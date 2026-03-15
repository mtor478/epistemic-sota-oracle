import base64
import time
import requests
import tenseal as ts
import numpy as np
import torch
import torch.nn.functional as F

ORACLE_URL = "http://127.0.0.1:8083/mine_fhe_l1"

# 🧮 O Agente deve espelhar a Invariante de Compressão do Oráculo
DIMENSIONS = 64

print("⚙️ [AGENTE] Forjando Chaves CKKS Otimizadas...")
context = ts.context(
    ts.SCHEME_TYPE.CKKS,
    poly_modulus_degree=8192,
    coeff_mod_bit_sizes=[60, 40, 60] 
)
context.global_scale = 2**40
context.generate_galois_keys()

query_tensor = np.random.uniform(-0.1, 0.1, DIMENSIONS).tolist()
enc_query = ts.ckks_vector(context, query_tensor)

ctx_b64 = base64.b64encode(context.serialize(save_public_key=True, save_secret_key=False, save_galois_keys=True)).decode()
query_b64 = base64.b64encode(enc_query.serialize()).decode()

print("🚀 [AGENTE] Disparando Tensor Comprimido (Anti-Deadlock)...")
t_req = time.time()
resp = requests.post(ORACLE_URL, json={"context_b64": ctx_b64, "query_b64": query_b64})

if resp.status_code == 200:
    res_data = resp.json()
    res_bytes = base64.b64decode(res_data["result_b64"])
    
    enc_logits = ts.ckks_vector_from(context, res_bytes)
    decrypted_logits = enc_logits.decrypt()
    
    logits_tensor = torch.tensor(decrypted_logits)
    probabilities = F.softmax(logits_tensor, dim=0)
    
    best_index = torch.argmax(probabilities).item()
    best_prob = probabilities[best_index].item()
    
    print(f"🟢 [AGENTE] Colapso de Onda Concluído em {(time.time() - t_req):.2f}s.")
    print(f"💎 SOTA: Deadlock Aniquilado. Softmax Ativado.")
    print(f"🎯 Índice {best_index} | Probabilidade = {best_prob:.6f}")
else:
    print(f"🔴 [AGENTE] Erro de Rede: {resp.text}")
