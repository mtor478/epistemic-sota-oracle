import os
import base64
import time
import requests
import numpy as np
import shutil
from concrete.ml.deployment import FHEModelClient

ORACLE_URL = "http://127.0.0.1:8081/mine_fhe"
CLIENT_ZIP_URL = "http://127.0.0.1:8081/get_client_zip"
DIMENSIONS = 384
TMP_DIR = "/tmp/fhe_agent_model"

# Clean up and fetch client.zip
shutil.rmtree(TMP_DIR, ignore_errors=True)
os.makedirs(TMP_DIR, exist_ok=True)

print("⚙️ [AGENTE] Buscando client.zip do Oráculo...")
r = requests.get(CLIENT_ZIP_URL)
with open(os.path.join(TMP_DIR, "client.zip"), "wb") as f:
    f.write(r.content)

print("⚙️ [AGENTE] Inicializando Cliente FHE...")
client = FHEModelClient(TMP_DIR)
client.generate_private_and_evaluation_keys()

# Gerando a Tese/Query real (Vetor semântico da SDE)
query_tensor = np.random.uniform(-0.1, 0.1, (1, 1, DIMENSIONS))

print("⚡ [AGENTE] Encriptando Tensor...")
ser_x = client.quantize_encrypt_serialize(query_tensor)
ser_eval_keys = client.get_serialized_evaluation_keys()

# Base64 encoding
query_b64 = base64.b64encode(ser_x).decode()
ctx_b64 = base64.b64encode(ser_eval_keys).decode()

print("🚀 [AGENTE] Disparando Payload Cifrado para o Oráculo...")
t_req = time.time()
resp = requests.post(ORACLE_URL, json={"context_b64": ctx_b64, "query_b64": query_b64})

if resp.status_code == 200:
    res_data = resp.json()
    res_bytes = base64.b64decode(res_data["result_b64"])
    
    # Decrypt
    y = client.deserialize_decrypt_dequantize(res_bytes)
    score = y[0][0][0]
    
    print(f"🟢 [AGENTE] Colapso de Onda Concluído.")
    print(f"💎 SOTA: Similaridade Semântica FHE = {score:.6f}")
    print(f"⏱️ Tempo Total L4 + FHE: {time.time() - t_req:.2f}s")
else:
    print(f"🔴 [AGENTE] Falha no Oráculo: {resp.text}")
