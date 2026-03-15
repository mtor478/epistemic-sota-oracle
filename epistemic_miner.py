import time
import base64
import tenseal as ts
import numpy as np
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

class FHERequest(BaseModel):
    context_b64: str
    query_b64: str

@app.post("/mine_fhe")
async def blind_oracle_compute(req: FHERequest):
    try:
        print("⚡ [ORÁCULO] Requisição Cifrada Recebida. Iniciando cômputo às cegas...")
        # 1. Deserialização do contexto e do tensor
        ctx_bytes = base64.b64decode(req.context_b64)
        query_bytes = base64.b64decode(req.query_b64)
        
        ctx = ts.context_from(ctx_bytes)
        enc_query = ts.ckks_vector_from(ctx, query_bytes)
        
        # 2. Simulação SOTA: Extração do Vetor do ArXiv no Qdrant (mock para 384 dim)
        # O oráculo acessa seus dados em texto plano, mas opera sobre a query cifrada
        db_vector = np.random.uniform(-0.1, 0.1, 384).tolist()
        
        # 3. Produto Escalar Homomórfico (O(d))
        enc_dot_product = enc_query.dot(db_vector)
        
        # 4. Serialização da resposta cifrada
        result_bytes = enc_dot_product.serialize()
        return {"result_b64": base64.b64encode(result_bytes).decode('utf-8')}
    except Exception as e:
        print(f"🔴 [ORÁCULO] Colapso FHE: {e}")
        return {"error": str(e)}
