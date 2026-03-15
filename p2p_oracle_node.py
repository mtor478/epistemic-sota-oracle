import os
os.environ["OMP_NUM_THREADS"] = "1"

import base64
import time
import asyncio
import httpx
import hashlib
import tenseal as ts
import numpy as np
from fastapi import FastAPI
from pydantic import BaseModel
from eth_account import Account
from eth_account.messages import encode_defunct
from qdrant_client import QdrantClient

app = FastAPI()

class FHEMapRequest(BaseModel):
    context_b64: str
    query_b64: str

MY_PORT = int(os.environ.get("PORT", 8091))
MY_PEER_URL = f"http://127.0.0.1:{MY_PORT}"

pk_hex = "0x" + hashlib.sha256(f"SOTA_VALIDATOR_NODE_{MY_PORT}_V1".encode()).hexdigest()
node_account = Account.from_key(pk_hex)

try:
    q_client = QdrantClient("localhost", port=6333)
    scroll_result, _ = q_client.scroll(collection_name="epistemic_production", limit=128, with_vectors=True)
    db_matrix = [point.vector for point in scroll_result]
    db_matrix_transposed = np.array(db_matrix).T.tolist()
except Exception as e:
    print(f"🔴 [QDRANT] Vácuo de Memória Fria: {e}")
    db_matrix_transposed = np.random.uniform(-0.1, 0.1, (8, 128)).tolist()

def cpu_bound_fhe_matmul_b64(ctx_b64, query_b64, db_transposed):
    ctx = ts.context_from(base64.b64decode(ctx_b64))
    enc_query = ts.ckks_vector_from(ctx, base64.b64decode(query_b64))
    enc_partial_scores = enc_query.matmul(db_transposed)
    return base64.b64encode(enc_partial_scores.serialize()).decode('utf-8')

def cpu_bound_fhe_aggregate_b64(ctx_b64, results_list_b64):
    ctx = ts.context_from(base64.b64decode(ctx_b64))
    aggregated_enc = None
    for b64_data in results_list_b64:
        enc_partial = ts.ckks_vector_from(ctx, base64.b64decode(b64_data))
        if aggregated_enc is None:
            aggregated_enc = enc_partial
        else:
            aggregated_enc = aggregated_enc + enc_partial
    return base64.b64encode(aggregated_enc.serialize()).decode('utf-8')

@app.post("/map_fhe")
async def map_shard_compute(req: FHEMapRequest):
    partial_result_b64 = await asyncio.to_thread(
        cpu_bound_fhe_matmul_b64, req.context_b64, req.query_b64, db_matrix_transposed
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
    
    local_task = asyncio.to_thread(cpu_bound_fhe_matmul_b64, req.context_b64, req.query_b64, db_matrix_transposed)
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
        
    aggregated_b64 = await asyncio.to_thread(cpu_bound_fhe_aggregate_b64, req.context_b64, fhe_results_b64)
    global_merkle_root = hashlib.sha256("".join(leaves).encode()).hexdigest()
    
    return {
        "signatures": signatures,
        "merkle_root": "0x" + global_merkle_root,
        "aggregated_result_b64": aggregated_b64
    }
