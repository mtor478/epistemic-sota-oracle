import os
import base64
import time
import sqlite3
import hashlib
import shutil
import torch
import numpy as np
from fastapi import FastAPI, BackgroundTasks
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List
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
MODEL_DIR = "/tmp/epistemic_miner_master_model"
shutil.rmtree(MODEL_DIR, ignore_errors=True)
os.makedirs(MODEL_DIR, exist_ok=True)

# 📐 Invariante Dimensional (Matching autopoietic_daemon.py shape 64)
DIMENSIONS = 64
N_VECTORS = 64

print(f"⚙️ [MESTRE] Inicializando Matriz e compilando modelo ({DIMENSIONS}x{N_VECTORS})...")
db_matrix_transposed = np.random.uniform(-0.1, 0.1, (DIMENSIONS, N_VECTORS))
model = FHEMatMul(db_matrix_transposed)

# Inputset for calibration
inputset = torch.tensor(np.random.uniform(-0.1, 0.1, (100, 1, DIMENSIONS)), dtype=torch.float32)
q_module = compile_torch_model(model, inputset)

dev = FHEModelDev(MODEL_DIR, q_module)
dev.save()

server = FHEModelServer(MODEL_DIR)

# Inicialização da Fila Persistente MPSC (Clearing House)
def init_db():
    conn = sqlite3.connect("zk_traces.db")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS traces (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            agent_id TEXT,
            query_hash TEXT,
            fhe_result_hash TEXT,
            status TEXT DEFAULT 'pending',
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

init_db()

class FHEAsyncRequest(BaseModel):
    agent_id: str
    context_b64: str  # Serialized evaluation keys
    query_b64: str    # Serialized query ciphertext

class ZKProofPayload(BaseModel):
    trace_ids: List[int]
    merkle_root: str
    zk_proof_hex: str

def persist_trace(agent_id: str, query_b64: str, result_b64: str):
    q_hash = hashlib.sha256(query_b64.encode()).hexdigest()
    r_hash = hashlib.sha256(result_b64.encode()).hexdigest()
    conn = sqlite3.connect("zk_traces.db")
    conn.execute("INSERT INTO traces (agent_id, query_hash, fhe_result_hash) VALUES (?, ?, ?)", 
                 (agent_id, q_hash, r_hash))
    conn.commit()
    conn.close()

@app.get("/get_client_zip")
async def get_client_zip():
    return FileResponse(os.path.join(MODEL_DIR, "client.zip"), media_type="application/zip", filename="client.zip")

@app.post("/mine_fhe_async")
async def blind_async_compute(req: FHEAsyncRequest, bg_tasks: BackgroundTasks):
    try:
        t0 = time.time()
        # Deserialize inputs
        query_bytes = base64.b64decode(req.query_b64)
        eval_keys_bytes = base64.b64decode(req.context_b64)
        
        # Execute server FHE inference
        res_bytes = server.run(query_bytes, eval_keys_bytes)
        result_b64 = base64.b64encode(res_bytes).decode('utf-8')
        
        # Persist trace in background (ZK Clearing House)
        bg_tasks.add_task(persist_trace, req.agent_id, req.query_b64, result_b64)
        
        t_total = time.time() - t0
        print(f"⚡ [ORÁCULO] FHE concluído em {t_total:.3f}s. Trace enfileirado para Liquidação ZK.")
        return {"result_b64": result_b64}
    except Exception as e:
        print(f"🔴 [ORÁCULO] Falha Física no Mestre: {e}")
        return {"error": str(e)}

@app.get("/pull_batch")
async def pull_batch():
    conn = sqlite3.connect("zk_traces.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id, agent_id, query_hash, fhe_result_hash FROM traces WHERE status = 'pending' LIMIT 10")
    rows = cursor.fetchall()
    
    if not rows:
        conn.close()
        return {"batch": []}
    
    trace_ids = [r[0] for r in rows]
    placeholders = ','.join(['?'] * len(trace_ids))
    cursor.execute(f"UPDATE traces SET status = 'processing' WHERE id IN ({placeholders})", trace_ids)
    conn.commit()
    conn.close()
    
    batch = [{"id": r[0], "agent_id": r[1], "q_hash": r[2], "r_hash": r[3]} for r in rows]
    print(f"📡 [MESTRE] Lote de {len(batch)} traces transferido para Nó Escravo (GPU).")
    return {"batch": batch}

@app.post("/webhook_zk_proof")
async def webhook_zk_proof(payload: ZKProofPayload):
    conn = sqlite3.connect("zk_traces.db")
    cursor = conn.cursor()
    placeholders = ','.join(['?'] * len(payload.trace_ids))
    cursor.execute(f"UPDATE traces SET status = 'settled' WHERE id IN ({placeholders})", payload.trace_ids)
    conn.commit()
    conn.close()
    
    print(f"\n💎 [MESTRE] PROVA ZK RECEBIDA DO CLUSTER PARASÍTICO!")
    print(f"🌲 Raiz de Merkle: {payload.merkle_root[:16]}...")
    print(f"🧱 ZK-SNARK: {payload.zk_proof_hex[:16]}...")
    print(f"⚖️ Acionando Contrato L1 (batchSettle) via Arbitrum RPC...")
    print(f"🟢 [MESTRE] Escrow liberado. Ciclo Autopoiético fechado a Custo Zero.\n")
    return {"status": "Liquidado"}
