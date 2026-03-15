import base64
import time
import sqlite3
import numpy as np
import tenseal as ts
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from eth_account import Account
# 🧮 MUTAÇÃO SOTA: encode_typed_data substitui a API depreciada
from eth_account.messages import encode_typed_data

app = FastAPI()

class FHEChannelRequest(BaseModel):
    agent_address: str
    amount: int
    nonce: int
    signature_hex: str
    context_b64: str
    query_b64: str

# 📐 Invariante Dimensional (L=1 Híbrido preservado)
DIMENSIONS = 384
N_VECTORS = 128
db_matrix_transposed = np.random.uniform(-0.1, 0.1, (DIMENSIONS, N_VECTORS)).tolist()

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
    # 🧮 MUTAÇÃO SOTA: Injeção da variável full_message
    encoded_data = encode_typed_data(full_message=msg)
    recovered_address = Account.recover_message(encoded_data, signature=signature)
    return recovered_address.lower() == agent_addr.lower()

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

    ctx = ts.context_from(base64.b64decode(req.context_b64))
    enc_query = ts.ckks_vector_from(ctx, base64.b64decode(req.query_b64))
    enc_logits = enc_query.matmul(db_matrix_transposed)
    
    print(f"🟢 [ORÁCULO] Cômputo autorizado via State Channel. MEV = 0.")
    return {"result_b64": base64.b64encode(enc_logits.serialize()).decode('utf-8')}
