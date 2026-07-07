import os
import base64
import time
import sqlite3
import numpy as np
import shutil
import torch
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from eth_account import Account
from eth_account.messages import encode_typed_data
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
MODEL_DIR = "/tmp/epistemic_miner_channel_model"
shutil.rmtree(MODEL_DIR, ignore_errors=True)
os.makedirs(MODEL_DIR, exist_ok=True)

# 📐 Invariante Dimensional (L=1 Híbrido preservado)
DIMENSIONS = 384
N_VECTORS = 128

print(f"⚙️ [ORÁCULO CANAL] Inicializando database e compilando ({DIMENSIONS}x{N_VECTORS})...")
db_matrix_transposed = np.random.uniform(-0.1, 0.1, (DIMENSIONS, N_VECTORS))
model = FHEMatMul(db_matrix_transposed)

# Inputset for calibration (shape: [num_samples, 1, 384])
inputset = torch.tensor(np.random.uniform(-0.1, 0.1, (100, 1, DIMENSIONS)), dtype=torch.float32)
q_module = compile_torch_model(model, inputset)

dev = FHEModelDev(MODEL_DIR, q_module)
dev.save()

server = FHEModelServer(MODEL_DIR)

class FHEChannelRequest(BaseModel):
    agent_address: str
    amount: int
    nonce: int
    signature_hex: str
    context_b64: str  # Kept as context_b64 for API backward compatibility, holds serialized eval keys
    query_b64: str    # Serialized query ciphertext

def verify_eip712(agent_addr, amount, nonce, signature):
    msg = {
        "types": {
            "EIP712Domain": [
                {"name": "name", "type": "string"},
                {"name": "version", "type": "string"},
                {"name": "chainId", "type": "uint256"},
                {"name": "verifyingContract", "type": "address"}
            ],
            "Payment": [
                {"name": "agent", "type": "address"},
                {"name": "amount", "type": "uint256"},
                {"name": "nonce", "type": "uint256"}
            ]
        },
        "primaryType": "Payment",
        "domain": {
            "name": "EpistemicOracle",
            "version": "1",
            "chainId": 421614,
            "verifyingContract": "0x0000000000000000000000000000000000000000"
        },
        "message": {
            "agent": agent_addr,
            "amount": amount,
            "nonce": nonce
        }
    }
    encoded_data = encode_typed_data(full_message=msg)
    recovered_address = Account.recover_message(encoded_data, signature=signature)
    return recovered_address.lower() == agent_addr.lower()

@app.get("/get_client_zip")
async def get_client_zip():
    return FileResponse(os.path.join(MODEL_DIR, "client.zip"), media_type="application/zip", filename="client.zip")

@app.post("/mine_fhe_channel")
async def blind_channel_compute(req: FHEChannelRequest):
    t0 = time.time()
    
    if not verify_eip712(req.agent_address, req.amount, req.nonce, req.signature_hex):
        print("🔴 [ORÁCULO] Falha ECDSA: Assinatura Corrompida ou Falsificada.")
        raise HTTPException(status_code=401, detail="Invalid EIP-712 Signature")

    conn = sqlite3.connect("state_channels.db")
    cursor = conn.cursor()
    cursor.execute("SELECT current_nonce FROM nonces WHERE agent_address = ?", (req.agent_address,))
    row = cursor.fetchone()
    
    current_nonce = row[0] if row else 0
    if req.nonce <= current_nonce:
        conn.close()
        print(f"🔴 [ORÁCULO] Replay Attack Interceptado. Nonce {req.nonce} <= {current_nonce}")
        raise HTTPException(status_code=402, detail="Nonce Exhausted (Replay Attack)")
    
    cursor.execute("INSERT OR REPLACE INTO nonces (agent_address, current_nonce) VALUES (?, ?)", 
                   (req.agent_address, req.nonce))
    conn.commit()
    conn.close()

    print(f"⚡ [ORÁCULO] Canal L4 Verificado em {(time.time() - t0)*1000:.2f}ms. Iniciando Álgebra FHE...")

    # FHE computation
    query_bytes = base64.b64decode(req.query_b64)
    eval_keys_bytes = base64.b64decode(req.context_b64)
    
    res_bytes = server.run(query_bytes, eval_keys_bytes)
    
    print(f"🟢 [ORÁCULO] Cômputo autorizado via State Channel. MEV = 0.")
    return {"result_b64": base64.b64encode(res_bytes).decode('utf-8')}
