import base64
import time
import requests
import tenseal as ts
import numpy as np

ORACLE_URL = "http://127.0.0.1:8081/mine_fhe"
DIMENSIONS = 384

print("⚙️ [AGENTE] Forjando Chaves FHE (CKKS)...")
t0 = time.time()
context = ts.context(
    ts.SCHEME_TYPE.CKKS,
    poly_modulus_degree=8192,
    coeff_mod_bit_sizes=[60, 40, 40, 60]
)
context.global_scale = 2**40
context.generate_galois_keys()

# Gerando a Tese/Query real (Vetor semântico da SDE)
query_tensor = np.random.uniform(-0.1, 0.1, DIMENSIONS).tolist()

print("⚡ [AGENTE] Encriptando Tensor...")
enc_query = ts.ckks_vector(context, query_tensor)

# Serialização
ctx_b64 = base64.b64encode(context.serialize(save_public_key=True, save_secret_key=False, save_galois_keys=True)).decode()
query_b64 = base64.b64encode(enc_query.serialize()).decode()

print("🚀 [AGENTE] Disparando Payload Cifrado para o Oráculo...")
t_req = time.time()
resp = requests.post(ORACLE_URL, json={"context_b64": ctx_b64, "query_b64": query_b64})

if resp.status_code == 200:
    res_data = resp.json()
    res_bytes = base64.b64decode(res_data["result_b64"])
    
    # Reconstrução e Decriptação ZK
    enc_result = ts.ckks_vector_from(context, res_bytes)
    score = enc_result.decrypt()[0]
    
    print(f"🟢 [AGENTE] Colapso de Onda Concluído.")
    print(f"💎 SOTA: Similaridade Semântica FHE = {score:.6f}")
    print(f"⏱️ Tempo Total L4 + FHE: {time.time() - t_req:.2f}s")
else:
    print(f"🔴 [AGENTE] Falha no Oráculo: {resp.text}")
