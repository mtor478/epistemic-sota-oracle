import os
import base64
import torch
import numpy as np
import shutil
from fastapi import FastAPI
from fastapi.responses import FileResponse
from pydantic import BaseModel
from concrete.ml.torch.compile import compile_torch_model
from concrete.ml.deployment import FHEModelDev, FHEModelServer

app = FastAPI()

class FHEMatMul(torch.nn.Module):
    def __init__(self, weight):
        super().__init__()
        self.weight = torch.nn.Parameter(torch.tensor(weight, dtype=torch.float32), requires_grad=False)
        
    def forward(self, x):
        return torch.matmul(x, self.weight)

# Setup model directory
MODEL_DIR = "/tmp/epistemic_miner_model"
shutil.rmtree(MODEL_DIR, ignore_errors=True)
os.makedirs(MODEL_DIR, exist_ok=True)

# 2. Simulação SOTA: Extração do Vetor do ArXiv no Qdrant (mock para 384 dim)
# O oráculo acessa seus dados em texto plano, mas opera sobre a query cifrada
print("⚙️ [ORÁCULO] Inicializando database e compilando modelo Concrete ML...")
db_vector = np.random.uniform(-0.1, 0.1, (384, 1))
model = FHEMatMul(db_vector)

# Inputset for calibration (shape: [num_samples, 1, 384])
inputset = torch.tensor(np.random.uniform(-0.1, 0.1, (100, 1, 384)), dtype=torch.float32)
q_module = compile_torch_model(model, inputset)

dev = FHEModelDev(MODEL_DIR, q_module)
dev.save()

server = FHEModelServer(MODEL_DIR)

class FHERequest(BaseModel):
    context_b64: str  # Kept as context_b64 for API backward compatibility, holds serialized eval keys
    query_b64: str    # Serialized query ciphertext

@app.get("/get_client_zip")
async def get_client_zip():
    return FileResponse(os.path.join(MODEL_DIR, "client.zip"), media_type="application/zip", filename="client.zip")

@app.post("/mine_fhe")
async def blind_oracle_compute(req: FHERequest):
    try:
        print("⚡ [ORÁCULO] Requisição Cifrada Recebida. Iniciando cômputo às cegas...")
        # 1. Deserialização do contexto e do tensor
        query_bytes = base64.b64decode(req.query_b64)
        eval_keys_bytes = base64.b64decode(req.context_b64)
        
        # 2. Executar inferência no servidor FHE
        res_bytes = server.run(query_bytes, eval_keys_bytes)
        
        return {"result_b64": base64.b64encode(res_bytes).decode('utf-8')}
    except Exception as e:
        print(f"🔴 [ORÁCULO] Colapso FHE: {e}")
        return {"error": str(e)}
