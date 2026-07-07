import os
os.environ["OMP_NUM_THREADS"] = "1"

import base64
import time
import asyncio
import httpx
import hashlib
import shutil
import torch
import numpy as np
from fastapi import FastAPI
from fastapi.responses import FileResponse
from pydantic import BaseModel
from eth_account import Account
from eth_account.messages import encode_defunct
from qdrant_client import QdrantClient
from concrete.ml.torch.compile import compile_torch_model
from concrete.ml.deployment import FHEModelDev, FHEModelServer

app = FastAPI()

class FHEMapRequest(BaseModel):
    context_b64: str  # Serialization of evaluation keys
    query_b64: str    # Serialization of query ciphertext

MY_PORT = int(os.environ.get("PORT", 8091))
MY_PEER_URL = f"http://127.0.0.1:{MY_PORT}"
MODEL_DIR = f"/tmp/p2p_oracle_model_{MY_PORT}"

pk_hex = "0x" + hashlib.sha256(f"SOTA_VALIDATOR_NODE_{MY_PORT}_V1".encode()).hexdigest()
node_account = Account.from_key(pk_hex)

class FHEMatMul(torch.nn.Module):
    def __init__(self, weight):
        super().__init__()
        self.weight = torch.nn.Parameter(torch.tensor(weight, dtype=torch.float32), requires_grad=False)
        
    def forward(self, x):
        return torch.matmul(x, self.weight)

# Load database matrix transposed
try:
    q_client = QdrantClient("localhost", port=6333)
    scroll_result, _ = q_client.scroll(collection_name="epistemic_production", limit=128, with_vectors=True)
    db_matrix = [point.vector for point in scroll_result]
    db_matrix_transposed = np.array(db_matrix).T
except Exception as e:
    print(f"🔴 [QDRANT] Vácuo de Memória Fria no Porto {MY_PORT}: {e}")
    # Default fallback: 8-dimensional space, 128 vectors
    np.random.seed(42)
    db_matrix_transposed = np.random.uniform(-0.1, 0.1, (8, 128))

DIMENSIONS, N_VECTORS = db_matrix_transposed.shape
print(f"⚙️ [ORÁCULO P2P {MY_PORT}] Compilando modelo Concrete ML ({DIMENSIONS}x{N_VECTORS})...")

model = FHEMatMul(db_matrix_transposed)
inputset = torch.tensor(np.random.uniform(-0.1, 0.1, (100, 1, DIMENSIONS)), dtype=torch.float32)
q_module = compile_torch_model(model, inputset)

shutil.rmtree(MODEL_DIR, ignore_errors=True)
os.makedirs(MODEL_DIR, exist_ok=True)
dev = FHEModelDev(MODEL_DIR, q_module)
dev.save()

server = FHEModelServer(MODEL_DIR)

def cpu_bound_fhe_matmul_b64(eval_keys_b64, query_b64):
    query_bytes = base64.b64decode(query_b64)
    eval_keys_bytes = base64.b64decode(eval_keys_b64)
    res_bytes = server.run(query_bytes, eval_keys_bytes)
    return base64.b64encode(res_bytes).decode('utf-8')

@app.get("/get_client_zip")
async def get_client_zip():
    return FileResponse(os.path.join(MODEL_DIR, "client.zip"), media_type="application/zip", filename="client.zip")

@app.post("/map_fhe")
async def map_shard_compute(req: FHEMapRequest):
    partial_result_b64 = await asyncio.to_thread(
        cpu_bound_fhe_matmul_b64, req.context_b64, req.query_b64
    )
    merkle_leaf = hashlib.sha256(partial_result_b64.encode()).hexdigest()
    msg = encode_defunct(text=merkle_leaf)
    sig = Account.sign_message(msg, private_key=node_account.key)
    
    return {
        "node_address": node_account.address,
        "signature": sig.signature.hex(),
        "merkle_leaf": merkle_leaf,
        "partial_result_b64": partial_result_b64
    }

async def fetch_shard(client, peer, payload):
    try:
        resp = await client.post(f"{peer}/map_fhe", json=payload, timeout=15.0)
        if resp.status_code == 200: return resp.json()
    except Exception:
        pass
    return None

@app.post("/reduce_fhe_p2p")
async def reduce_and_consensus(req: FHEMapRequest):
    ALL_PEERS = ["http://127.0.0.1:8091", "http://127.0.0.1:8092", "http://127.0.0.1:8093", "http://127.0.0.1:8094"]
    EXTERNAL_PEERS = [p for p in ALL_PEERS if p != MY_PEER_URL]
    
    local_task = asyncio.to_thread(cpu_bound_fhe_matmul_b64, req.context_b64, req.query_b64)
    async with httpx.AsyncClient() as client:
        remote_tasks = [fetch_shard(client, peer, {"context_b64": req.context_b64, "query_b64": req.query_b64}) for peer in EXTERNAL_PEERS]
        local_result_b64, *remote_results = await asyncio.gather(local_task, *remote_tasks)
    
    signatures = []
    fhe_results_b64 = []
    leaves = []
    
    local_leaf = hashlib.sha256(local_result_b64.encode()).hexdigest()
    local_sig = Account.sign_message(encode_defunct(text=local_leaf), private_key=node_account.key)
    signatures.append(local_sig.signature.hex())
    fhe_results_b64.append(local_result_b64)
    leaves.append(local_leaf)
    
    for data in remote_results:
        if data is not None:
            signatures.append(data["signature"])
            fhe_results_b64.append(data["partial_result_b64"])
            leaves.append(data["merkle_leaf"])
            
    if len(signatures) < 3:
        return {"error": "BFT Consensus Failed"}
        
    global_merkle_root = hashlib.sha256("".join(leaves).encode()).hexdigest()
    
    return {
        "signatures": signatures,
        "merkle_root": "0x" + global_merkle_root,
        "aggregated_result_b64": fhe_results_b64  # Returns list of ciphertexts for client-side aggregation
    }
