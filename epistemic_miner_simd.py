import base64
import time
import tenseal as ts
import numpy as np
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

class FHESimdRequest(BaseModel):
    context_b64: str
    query_b64: str

# 📐 Invariante Dimensional
DIMENSIONS = 384
N_VECTORS = 4096 # Preenche exatamente 1 Ciphertext CKKS (M/2 slots para poly=8192)

print(f"⚙️ [ORÁCULO] Inicializando Matriz Transposta na RAM ({DIMENSIONS}x{N_VECTORS})...")
# P_DB: Matriz de conhecimento L2. Transposta para habilitar Produto Matriz-Vetor em O(1)
# Na produção real, isto é lido do Qdrant e clusterizado em chunks de 4096.
db_matrix_transposed = np.random.uniform(-0.1, 0.1, (DIMENSIONS, N_VECTORS)).tolist()

@app.post("/mine_fhe_simd")
async def blind_simd_compute(req: FHESimdRequest):
    try:
        t0 = time.time()
        # 1. Deserialização FHE O(1)
        ctx_bytes = base64.b64decode(req.context_b64)
        query_bytes = base64.b64decode(req.query_b64)
        
        ctx = ts.context_from(ctx_bytes)
        enc_query = ts.ckks_vector_from(ctx, query_bytes)
        
        print("⚡ [ORÁCULO] Ciphertext recebido. Executando Halevi-Shoup SIMD Batching...")
        
        # 2. 🧮 O SANTO GRAAL: Multiplicação Matricial Homomórfica
        # enc_query (1 x 384) @ db_matrix_transposed (384 x 4096) -> enc_scores (1 x 4096)
        # 384 rotações de Galois e polinômios avaliados simultaneamente. Sem loops Python.
        enc_scores = enc_query.matmul(db_matrix_transposed)
        
        # 3. Serialização da resposta cifrada O(1)
        result_bytes = enc_scores.serialize()
        t_fhe = time.time() - t0
        print(f"🟢 [ORÁCULO] Cômputo SIMD concluído em {t_fhe:.3f}s. {N_VECTORS} scores empacotados.")
        
        return {"result_b64": base64.b64encode(result_bytes).decode('utf-8')}
    except Exception as e:
        print(f"🔴 [ORÁCULO] Colapso FHE SIMD: {e}")
        return {"error": str(e)}
