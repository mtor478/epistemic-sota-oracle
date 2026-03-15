import base64
import time
import requests
import tenseal as ts
import numpy as np

ORACLE_URL = "http://127.0.0.1:8082/mine_fhe_simd"
DIMENSIONS = 384

print("⚙️ [AGENTE] Forjando Chaves FHE CKKS + Galois Keys (SIMD)...")
# poly_modulus_degree 8192 garante exatamente 4096 slots polinomialmente independentes
context = ts.context(
    ts.SCHEME_TYPE.CKKS,
    poly_modulus_degree=8192,
    coeff_mod_bit_sizes=[60, 40, 40, 60]
)
context.global_scale = 2**40
context.generate_galois_keys() # Obrigatório para rotações SIMD L2

query_tensor = np.random.uniform(-0.1, 0.1, DIMENSIONS).tolist()

print("⚡ [AGENTE] Encriptando Vetor (Broadcasting Implícito)...")
enc_query = ts.ckks_vector(context, query_tensor)

ctx_b64 = base64.b64encode(context.serialize(save_public_key=True, save_secret_key=False, save_galois_keys=True)).decode()
query_b64 = base64.b64encode(enc_query.serialize()).decode()

print("🚀 [AGENTE] Disparando Payload para Oráculo SIMD...")
t_req = time.time()
resp = requests.post(ORACLE_URL, json={"context_b64": ctx_b64, "query_b64": query_b64})

if resp.status_code == 200:
    res_data = resp.json()
    res_bytes = base64.b64decode(res_data["result_b64"])
    
    # Colapso Dimensional
    enc_scores = ts.ckks_vector_from(context, res_bytes)
    decrypted_scores = enc_scores.decrypt()
    
    t_total = time.time() - t_req
    
    # Extração argmax (O Agente acha o melhor papel sem o Oráculo saber qual foi)
    best_index = np.argmax(decrypted_scores)
    best_score = decrypted_scores[best_index]
    
    print(f"🟢 [AGENTE] Colapso ZK Concluído.")
    print(f"💎 SOTA: {len(decrypted_scores)} scores decriptados simultaneamente.")
    print(f"🎯 Vetor Ótimo (Top 1): Índice {best_index} | Similaridade = {best_score:.6f}")
    print(f"⏱️ Tempo Total M2M: {t_total:.2f}s")
else:
    print(f"🔴 [AGENTE] Falha no Oráculo: {resp.text}")
