import os
import base64
import time
import requests
import numpy as np
import shutil
from concrete.ml.deployment import FHEModelClient

ORACLE_URL = "http://127.0.0.1:8082/mine_fhe_simd"
CLIENT_ZIP_URL = "http://127.0.0.1:8082/get_client_zip"
DIMENSIONS = 384
TMP_DIR = "/tmp/fhe_agent_simd_model"

# Clean up and fetch client.zip
shutil.rmtree(TMP_DIR, ignore_errors=True)
os.makedirs(TMP_DIR, exist_ok=True)

print("⚙️ [AGENTE] Buscando client.zip do Oráculo SIMD...")
r = requests.get(CLIENT_ZIP_URL)
with open(os.path.join(TMP_DIR, "client.zip"), "wb") as f:
    f.write(r.content)

print("⚙️ [AGENTE] Inicializando Cliente FHE SIMD...")
client = FHEModelClient(TMP_DIR)
client.generate_private_and_evaluation_keys()

query_tensor = np.random.uniform(-0.1, 0.1, (1, 1, DIMENSIONS))

print("⚡ [AGENTE] Encriptando Vetor...")
ser_x = client.quantize_encrypt_serialize(query_tensor)
ser_eval_keys = client.get_serialized_evaluation_keys()

# Base64 encoding
query_b64 = base64.b64encode(ser_x).decode()
ctx_b64 = base64.b64encode(ser_eval_keys).decode()

print("🚀 [AGENTE] Disparando Payload para Oráculo SIMD...")
t_req = time.time()
resp = requests.post(ORACLE_URL, json={"context_b64": ctx_b64, "query_b64": query_b64})

if resp.status_code == 200:
    res_data = resp.json()
    res_bytes = base64.b64decode(res_data["result_b64"])
    
    # Decrypt
    decrypted_scores = client.deserialize_decrypt_dequantize(res_bytes)[0][0]
    
    t_total = time.time() - t_req
    
    # Extração argmax
    best_index = np.argmax(decrypted_scores)
    best_score = decrypted_scores[best_index]
    
    print(f"🟢 [AGENTE] Colapso ZK Concluído.")
    print(f"💎 SOTA: {len(decrypted_scores)} scores decriptados simultaneamente.")
    print(f"🎯 Vetor Ótimo (Top 1): Índice {best_index} | Similaridade = {best_score:.6f}")
    print(f"⏱️ Tempo Total M2M: {t_total:.2f}s")
else:
    print(f"🔴 [AGENTE] Falha no Oráculo: {resp.text}")
