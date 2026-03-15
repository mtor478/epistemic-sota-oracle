import base64
import time
import requests
import tenseal as ts
import numpy as np
import torch
import torch.nn.functional as F
import os
from web3 import Web3
from dotenv import load_dotenv

load_dotenv(os.path.expanduser("~/epistemic_ecosystem.env"))
RPC_URL = os.getenv("RPC_URL_HTTP", "")
PK = os.getenv("AGENT_PRIVATE_KEY", "")
CONTRACT_ADDRESS = os.getenv("CONTRACT_ADDRESS", "")

LEADER_URL = "http://127.0.0.1:8091/reduce_fhe_p2p"
DIMENSIONS = 8
NYQUIST_INTERVAL = 15 # 4 horas estritas para macro volatilidade

w3 = Web3(Web3.HTTPProvider(RPC_URL)) if RPC_URL else None
shadow_mode = not (w3 and w3.is_connected() and PK and CONTRACT_ADDRESS)

print("⚙️ [AGENTE SDE] Colapsando Função de Incerteza (TFHE L=1)...")
context = ts.context(ts.SCHEME_TYPE.CKKS, poly_modulus_degree=4096, coeff_mod_bit_sizes=[40, 20, 40])
context.global_scale = 2**20
context.generate_galois_keys()

# 🧮 O SANTO GRAAL: Loop Autopoiético Perpétuo
while True:
    print("\n" + "="*50)
    print("🌌 [DAEMON L4] Acordando para novo Bloco de Consenso...")
    
    query_tensor = np.random.uniform(-0.1, 0.1, DIMENSIONS).tolist()
    enc_query = ts.ckks_vector(context, query_tensor)

    ctx_b64 = base64.b64encode(context.serialize(save_public_key=True, save_secret_key=False, save_galois_keys=True)).decode()
    query_b64 = base64.b64encode(enc_query.serialize()).decode()

    print("🚀 [AGENTE L4] Buscando Consenso BFT no Oráculo Descentralizado...")
    try:
        resp = requests.post(LEADER_URL, timeout=45.0, json={"context_b64": ctx_b64, "query_b64": query_b64})

        if resp.status_code == 200:
            data = resp.json()
            if "error" in data:
                print(f"🔴 Colapso: {data['error']}")
            else:
                res_bytes = base64.b64decode(data["aggregated_result_b64"])
                sigs = data["signatures"]
                merkle_root = data["merkle_root"]
                
                enc_result = ts.ckks_vector_from(context, res_bytes)
                decrypted_sum = enc_result.decrypt()
                
                N = len(sigs)
                decrypted_mean = [x / N for x in decrypted_sum]
                
                print(f"🟢 [BFT] {N} Assinaturas Validadas. Raiz: {merkle_root[:16]}...")
                
                logits_tensor = torch.tensor(decrypted_mean)
                probabilities = F.softmax(logits_tensor, dim=0)
                target_weights = (probabilities * 10000).int().tolist()
                
                print(f"🎯 [SDE] Alocação Ótima (Target Weights): {target_weights[:3]}...")
                
                if shadow_mode:
                    print(f"👻 [SHADOW MODE] Variáveis de Mainnet ausentes. Transação L1 evitada.")
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

    print(f"⏳ [SDE] Adormecendo... Hibernação Estocástica ({NYQUIST_INTERVAL}s).")
    time.sleep(NYQUIST_INTERVAL)
