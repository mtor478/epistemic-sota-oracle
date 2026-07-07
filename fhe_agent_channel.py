import os
import base64
import time
import requests
import numpy as np
import shutil
from eth_account import Account
from eth_account.messages import encode_typed_data
from concrete.ml.deployment import FHEModelClient

ORACLE_URL = "http://127.0.0.1:8085/mine_fhe_channel"
CLIENT_ZIP_URL = "http://127.0.0.1:8085/get_client_zip"
DIMENSIONS = 384
TMP_DIR = "/tmp/fhe_agent_channel_model"

# Clean up and fetch client.zip
shutil.rmtree(TMP_DIR, ignore_errors=True)
os.makedirs(TMP_DIR, exist_ok=True)

print("⚙️ [AGENTE] Buscando client.zip do Oráculo Canal...")
r = requests.get(CLIENT_ZIP_URL)
with open(os.path.join(TMP_DIR, "client.zip"), "wb") as f:
    f.write(r.content)

print("⚙️ [AGENTE] Inicializando Cliente FHE Canal...")
client = FHEModelClient(TMP_DIR)
client.generate_private_and_evaluation_keys()

print("⚙️ [AGENTE] Forjando Identidade ECDSA e Canal EIP-712...")
agent_acct = Account.create()
agent_address = agent_acct.address
private_key = agent_acct.key

amount_to_pay = 1000000
current_nonce = 1

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
        "agent": agent_address,
        "amount": amount_to_pay,
        "nonce": current_nonce
    }
}

encoded_data = encode_typed_data(full_message=msg)
signed_message = Account.sign_message(encoded_data, private_key)
signature_hex = signed_message.signature.hex()

print("⚡ [AGENTE] Assinatura Criptográfica Concluída. Sem exposição ao Mempool.")

query_tensor = np.random.uniform(-0.1, 0.1, (1, 1, DIMENSIONS))

print("⚙️ [AGENTE] Encriptando Tensor SDE...")
ser_x = client.quantize_encrypt_serialize(query_tensor)
ser_eval_keys = client.get_serialized_evaluation_keys()

payload = {
    "agent_address": agent_address,
    "amount": amount_to_pay,
    "nonce": current_nonce,
    "signature_hex": signature_hex,
    "context_b64": base64.b64encode(ser_eval_keys).decode(),
    "query_b64": base64.b64encode(ser_x).decode()
}

print("🚀 [AGENTE] Disparando Payload (Assinatura + Tensor) via rede L4...")
t_req = time.time()
resp = requests.post(ORACLE_URL, json=payload)

if resp.status_code == 200:
    print(f"🟢 [AGENTE] Liquidação Otimista validada e Resposta extraída em {(time.time() - t_req):.3f}s")
else:
    print(f"🔴 [AGENTE] Falha de Consenso: {resp.text}")

print("🧱 [TESTE DE REPLAY ATTACK] Disparando mesma assinatura novamente (Mesmo Nonce)...")
resp_replay = requests.post(ORACLE_URL, json=payload)
if resp_replay.status_code == 402:
    print("💎 SOTA: Replay Attack Bloqueado Matematicamente pelo Oráculo.")
