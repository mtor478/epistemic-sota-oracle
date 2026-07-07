import time
import torch
import os
import requests
import numpy as np
import base64
import shutil
from market_sde import NeuralSDE
from defi_router import DeFiExecutor
from concrete.ml.deployment import FHEModelClient

# 📐 Invariantes SOTA L4
ORACLE_URL = "http://127.0.0.1:8086/mine_fhe_async"
CLIENT_ZIP_URL = "http://127.0.0.1:8086/get_client_zip"
DIMENSIONS = 64
ENV_PATH = os.path.expanduser("~/epistemic_ecosystem.env")
NYQUIST_SHANNON_INTERVAL = 14400  # 4 Horas estritas (Macro Volatility)
ORACLE_TIMEOUT = 45.0             # Limiar de Fenda de Comunicação
TMP_DIR = "/tmp/autopoietic_daemon_model"

print("⚙️ [DAEMON] Booting M2M Perpetual Markov Engine...")
sde = NeuralSDE(fhe_dim=DIMENSIONS)
defi = DeFiExecutor(ENV_PATH)
current_weights = torch.tensor([1.0, 0.0, 0.0]) 

def request_fhe_entropy():
    """Extração cega de conhecimento via L2 Roteador Mestre."""
    try:
        shutil.rmtree(TMP_DIR, ignore_errors=True)
        os.makedirs(TMP_DIR, exist_ok=True)
        
        print("⚙️ [DAEMON] Buscando client.zip do Mestre...")
        r = requests.get(CLIENT_ZIP_URL, timeout=5.0)
        with open(os.path.join(TMP_DIR, "client.zip"), "wb") as f:
            f.write(r.content)
            
        client = FHEModelClient(TMP_DIR)
        client.generate_private_and_evaluation_keys()
        
        query_tensor = np.random.uniform(-0.1, 0.1, (1, 1, DIMENSIONS))
        ser_x = client.quantize_encrypt_serialize(query_tensor)
        ser_eval_keys = client.get_serialized_evaluation_keys()
        
        payload = {
            "agent_id": "perpetual_agent_alpha",
            "context_b64": base64.b64encode(ser_eval_keys).decode(),
            "query_b64": base64.b64encode(ser_x).decode()
        }
        
        print("🚀 [DAEMON] Disparando Payload FHE para o Mestre...")
        resp = requests.post(ORACLE_URL, json=payload, timeout=ORACLE_TIMEOUT)
        if resp.status_code == 200:
            res_data = resp.json()
            res_bytes = base64.b64decode(res_data["result_b64"])
            y = client.deserialize_decrypt_dequantize(res_bytes)[0][0]
            return torch.tensor(y, dtype=torch.float32)
    except Exception as e:
        print(f"🟡 [ORACLE_VACUUM] Falha no Cluster Parasítico: {e}")
    return None

# Check if running in single-step test mode (via env var)
single_step_test = os.environ.get("TEST_DAEMON_SINGLE_STEP") == "1"

while True:
    print("\n" + "="*50)
    print(f"🌌 [DAEMON] Acordando na Janela SDE Janela de Tempo...")
    
    fhe_signals = request_fhe_entropy()
    
    with torch.no_grad():
        if fhe_signals is not None:
            print("⚡ [DAEMON] Tensor Epistêmico (FHE) acoplado com sucesso.")
            target_weights = sde(fhe_signals)
        else:
            print("🧪 [DAEMON] FHE Drift. Executando Passo Estocástico Puro (Euler-Maruyama)...")
            vacuum_tensor = torch.zeros(DIMENSIONS)
            target_weights = sde(vacuum_tensor)
            
    print(f"🎯 [DAEMON] Alocação Markoviana: USDC {target_weights[0]:.2f} | WETH {target_weights[1]:.2f} | WBTC {target_weights[2]:.2f}")
    
    try:
        tx_hash = defi.execute_rebalance(current_weights, target_weights)
        if tx_hash:
            print(f"💎 SOTA: Assinatura L1 Consolidada (Prova de Alpha). TX: {tx_hash}")
            current_weights = target_weights
    except Exception as e:
        print(f"🔴 [DAEMON] Falha Crítica de Roteamento Web3 capturada e isolada: {e}")

    if single_step_test:
        print("🧪 [DAEMON] Teste de passo único concluído. Encerrando daemon.")
        break
        
    print(f"⏳ [DAEMON] Estado Preservado na RAM. Hibernando por {NYQUIST_SHANNON_INTERVAL}s...")
    time.sleep(NYQUIST_SHANNON_INTERVAL)
