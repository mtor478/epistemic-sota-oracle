import base64
import time
import tenseal as ts
import numpy as np
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

class FHEL1Request(BaseModel):
    context_b64: str
    query_b64: str

# 🧮 MUTAÇÃO SOTA (ANTI-DEADLOCK): 
# Compressão dimensional para viabilizar computação FHE em CPU padrão.
DIMENSIONS = 64  # Reduzido de 384
N_VECTORS = 256  # Reduzido de 4096

print(f"⚙️ [ORÁCULO] Inicializando Matriz Comprimida ({DIMENSIONS}x{N_VECTORS})...")
db_matrix_transposed = np.random.uniform(-0.1, 0.1, (DIMENSIONS, N_VECTORS)).tolist()

@app.post("/mine_fhe_l1")
async def blind_l1_compute(req: FHEL1Request):
    try:
        t0 = time.time()
        ctx_bytes = base64.b64decode(req.context_b64)
        query_bytes = base64.b64decode(req.query_b64)
        
        ctx = ts.context_from(ctx_bytes)
        enc_query = ts.ckks_vector_from(ctx, query_bytes)
        
        print("⚡ [ORÁCULO] Executando MatMul Comprimido...")
        # A operação agora consumirá milissegundos em vez de horas.
        enc_logits = enc_query.matmul(db_matrix_transposed)
        
        result_bytes = enc_logits.serialize()
        t_fhe = time.time() - t0
        print(f"🟢 [ORÁCULO] Cômputo FHE concluído em {t_fhe:.3f}s. Zero Deadlock.")
        
        return {"result_b64": base64.b64encode(result_bytes).decode('utf-8')}
    except Exception as e:
        print(f"🔴 [ORÁCULO] Falha Física: {e}")
        return {"error": str(e)}
