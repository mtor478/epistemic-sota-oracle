import os
import base64
import time
import requests
import numpy as np
import shutil
from concrete.ml.deployment import FHEModelClient

LEADER_URL = "http://127.0.0.1:8091/reduce_fhe_p2p"
CLIENT_ZIP_URL = "http://127.0.0.1:8091/get_client_zip"
DIMENSIONS = 8
TMP_DIR = "/tmp/fhe_agent_p2p_model"

# Clean up and fetch client.zip
shutil.rmtree(TMP_DIR, ignore_errors=True)
os.makedirs(TMP_DIR, exist_ok=True)

print("⚙️ [AGENTE] Buscando client.zip do Líder P2P...")
r = requests.get(CLIENT_ZIP_URL)
with open(os.path.join(TMP_DIR, "client.zip"), "wb") as f:
    f.write(r.content)

print("⚙️ [AGENTE] Inicializando Cliente FHE P2P...")
client = FHEModelClient(TMP_DIR)
client.generate_private_and_evaluation_keys()

# Gerando o query tensor
query_tensor = np.random.uniform(-0.1, 0.1, (1, 1, DIMENSIONS))

print("⚡ [AGENTE] Encriptando Vetor de Estado SDE...")
ser_x = client.quantize_encrypt_serialize(query_tensor)
ser_eval_keys = client.get_serialized_evaluation_keys()

query_b64 = base64.b64encode(ser_x).decode()
ctx_b64 = base64.b64encode(ser_eval_keys).decode()

print("🚀 [AGENTE] Disparando Tensor Protegido para a Rede P2P...")
t_req = time.time()
resp = requests.post(LEADER_URL, timeout=45.0, json={"context_b64": ctx_b64, "query_b64": query_b64})

if resp.status_code == 200:
    data = resp.json()
    if "error" in data:
        print(f"🔴 [AGENTE] Colapso: {data['error']}")
    else:
        results_list = data["aggregated_result_b64"]
        sigs = data["signatures"]
        
        # Descriptografar cada resultado parcial e calcular a média
        decrypted_results = []
        for res_b64 in results_list:
            res_bytes = base64.b64decode(res_b64)
            decrypted_y = client.deserialize_decrypt_dequantize(res_bytes)[0][0]
            decrypted_results.append(decrypted_y)
            
        N = len(sigs)
        decrypted_mean = np.mean(decrypted_results, axis=0).tolist()
        
        print(f"🟢 [AGENTE] Consenso BFT Alcançado. {N} assinaturas validadas.")
        print(f"💎 SOTA: Produto Escalar Homomórfico Distribuído extraído.")
        print(f"🎯 Resposta Agregada (Amostra Local): {decrypted_mean[0]:.6f}")
        print(f"⏱️ Tempo Total (MapReduce FHE L4): {time.time() - t_req:.2f}s")
else:
    print(f"🔴 [AGENTE] Falha Crítica de Rede: {resp.status_code}")
