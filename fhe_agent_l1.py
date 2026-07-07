import os
import base64
import time
import requests
import numpy as np
import shutil
import torch
import torch.nn.functional as F
from concrete.ml.deployment import FHEModelClient

ORACLE_URL = "http://127.0.0.1:8083/mine_fhe_l1"
CLIENT_ZIP_URL = "http://127.0.0.1:8083/get_client_zip"
DIMENSIONS = 64
TMP_DIR = "/tmp/fhe_agent_l1_model"

# Clean up and fetch client.zip
shutil.rmtree(TMP_DIR, ignore_errors=True)
os.makedirs(TMP_DIR, exist_ok=True)

print("⚙️ [AGENTE] Buscando client.zip do Oráculo L1...")
r = requests.get(CLIENT_ZIP_URL)
with open(os.path.join(TMP_DIR, "client.zip"), "wb") as f:
    f.write(r.content)

print("⚙️ [AGENTE] Inicializando Cliente FHE L1...")
client = FHEModelClient(TMP_DIR)
client.generate_private_and_evaluation_keys()

query_tensor = np.random.uniform(-0.1, 0.1, (1, 1, DIMENSIONS))

print("⚡ [AGENTE] Encriptando Tensor Comprimido (Anti-Deadlock)...")
ser_x = client.quantize_encrypt_serialize(query_tensor)
ser_eval_keys = client.get_serialized_evaluation_keys()

# Base64 encoding
query_b64 = base64.b64encode(ser_x).decode()
ctx_b64 = base64.b64encode(ser_eval_keys).decode()

print("🚀 [AGENTE] Disparando Tensor Comprimido...")
t_req = time.time()
resp = requests.post(ORACLE_URL, json={"context_b64": ctx_b64, "query_b64": query_b64})

if resp.status_code == 200:
    res_data = resp.json()
    res_bytes = base64.b64decode(res_data["result_b64"])
    
    # Decrypt
    decrypted_logits = client.deserialize_decrypt_dequantize(res_bytes)[0][0]
    
    logits_tensor = torch.tensor(decrypted_logits)
    probabilities = F.softmax(logits_tensor, dim=0)
    
    best_index = torch.argmax(probabilities).item()
    best_prob = probabilities[best_index].item()
    
    print(f"🟢 [AGENTE] Colapso de Onda Concluído em {(time.time() - t_req):.2f}s.")
    print(f"💎 SOTA: Deadlock Aniquilado. Softmax Ativado.")
    print(f"🎯 Índice {best_index} | Probabilidade = {best_prob:.6f}")
else:
    print(f"🔴 [AGENTE] Erro de Rede: {resp.text}")
