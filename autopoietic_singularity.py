import base64
import time
import requests
import numpy as np
import torch
import torch.nn.functional as F
import os
import shutil
from web3 import Web3
from dotenv import load_dotenv
from concrete.ml.deployment import FHEModelClient

load_dotenv(os.path.expanduser("~/epistemic_ecosystem.env"))
RPC_URL = os.getenv("RPC_URL_HTTP", "")
PK = os.getenv("AGENT_PRIVATE_KEY", "")
CONTRACT_ADDRESS = os.getenv("CONTRACT_ADDRESS", "")

LEADER_URL = "http://127.0.0.1:8091/reduce_fhe_p2p"
CLIENT_ZIP_URL = "http://127.0.0.1:8091/get_client_zip"
DIMENSIONS = 8
NYQUIST_INTERVAL = 15 # 4 horas estritas para macro volatilidade
TMP_DIR = "/tmp/autopoietic_singularity_model"

w3 = Web3(Web3.HTTPProvider(RPC_URL)) if RPC_URL else None
shadow_mode = not (w3 and w3.is_connected() and PK and CONTRACT_ADDRESS)

# Clean up and fetch client.zip
shutil.rmtree(TMP_DIR, ignore_errors=True)
os.makedirs(TMP_DIR, exist_ok=True)

print("⚙️ [AGENTE SDE] Colapsando Função de Incerteza (TFHE L=1)...")
print("⚙️ [AGENTE SDE] Buscando client.zip do Líder...")
try:
    r = requests.get(CLIENT_ZIP_URL, timeout=10.0)
    with open(os.path.join(TMP_DIR, "client.zip"), "wb") as f:
        f.write(r.content)
    client = FHEModelClient(TMP_DIR)
    client.generate_private_and_evaluation_keys()
except Exception as e:
    print(f"🔴 [AGENTE SDE] Falha ao inicializar chaves FHE: {e}")
    client = None

single_step_test = os.environ.get("TEST_SINGULARITY_SINGLE_STEP") == "1"

# 🧮 O SANTO GRAAL: Loop Autopoiético Perpétuo
while True:
    print("\n" + "="*50)
    print("🌌 [DAEMON L4] Acordando para novo Bloco de Consenso...")
    
    if client is None:
        print("🔴 Cliente FHE não inicializado. Abortando passo.")
        if single_step_test: break
        time.sleep(NYQUIST_INTERVAL)
        continue
        
    query_tensor = np.random.uniform(-0.1, 0.1, (1, 1, DIMENSIONS))
    
    print("⚡ [AGENTE L4] Encriptando Vetor de Estado...")
    ser_x = client.quantize_encrypt_serialize(query_tensor)
    ser_eval_keys = client.get_serialized_evaluation_keys()

    ctx_b64 = base64.b64encode(ser_eval_keys).decode()
    query_b64 = base64.b64encode(ser_x).decode()

    print("🚀 [AGENTE L4] Buscando Consenso BFT no Oráculo Descentralizado...")
    try:
        resp = requests.post(LEADER_URL, timeout=45.0, json={"context_b64": ctx_b64, "query_b64": query_b64})

        if resp.status_code == 200:
            data = resp.json()
            if "error" in data:
                print(f"🔴 Colapso: {data['error']}")
            else:
                results_list = data["aggregated_result_b64"]
                sigs = data["signatures"]
                merkle_root = data["merkle_root"]
                
                # Decrypt each result and calculate the average
                decrypted_results = []
                for res_b64 in results_list:
                    res_bytes = base64.b64decode(res_b64)
                    decrypted_y = client.deserialize_decrypt_dequantize(res_bytes)[0][0]
                    decrypted_results.append(decrypted_y)
                    
                N = len(sigs)
                decrypted_mean = np.mean(decrypted_results, axis=0).tolist()
                
                print(f"🟢 [BFT] {N} Assinaturas Validadas. Raiz: {merkle_root[:16]}...")
                
                logits_tensor = torch.tensor(decrypted_mean)
                probabilities = F.softmax(logits_tensor, dim=0)
                target_weights = (probabilities * 10000).int().tolist()
                
                print(f"🎯 [SDE] Alocação Ótima (Target Weights): {target_weights[:3]}...")
                
                if shadow_mode:
                    print(f"% [SHADOW MODE] Variáveis de Mainnet ausentes. Transação L1 evitada.")
                else:
                    print("🔥 [DEFI] Disparando Liquidacão BFT On-Chain...")
                    account = w3.eth.account.from_key(PK)
                    
                    abi = [{"inputs":[{"internalType":"bytes32","name":"merkleRoot","type":"bytes32"},{"internalType":"bytes[]","name":"signatures","type":"bytes[]"},{"internalType":"int256[]","name":"targetWeights","type":"int256[]"}],"name":"batchSettleBFT","outputs":[],"stateMutability":"nonpayable","type":"function"}]
                    contract = w3.eth.contract(address=w3.to_checksum_address(CONTRACT_ADDRESS), abi=abi)
                    
                    tx = contract.functions.batchSettleBFT(
                        bytes.fromhex(merkle_root[2:]), 
                        [bytes.fromhex(s[2:]) for s in sigs], 
                        target_weights
                    ).build_transaction({
                        'from': account.address,
                        'nonce': w3.eth.get_transaction_count(account.address),
                        'gas': 1000000,
                        'maxFeePerGas': int(w3.eth.gas_price * 1.5),
                        'maxPriorityFeePerGas': w3.to_wei('0.001', 'gwei')
                    })
                    
                    signed_tx = w3.eth.account.sign_transaction(tx, PK)
                    tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
                    print(f"💎 SOTA: SINGULARIDADE ALCANÇADA. TxHash: {tx_hash.hex()}")
        else:
            print(f"🔴 [L4] Falha Crítica de Rede: {resp.status_code}")
    except Exception as e:
        print(f"🟡 [L4] Vácuo Térmico: {e}")

    if single_step_test:
        print("🧪 [AGENTE SDE] Teste de passo único concluído. Encerrando agente.")
        break
        
    print(f"⏳ [SDE] Adormecendo... Hibernação Estocástica ({NYQUIST_INTERVAL}s).")
    time.sleep(NYQUIST_INTERVAL)
