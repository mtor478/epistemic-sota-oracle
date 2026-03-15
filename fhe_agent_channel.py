import base64
import time
import requests
import tenseal as ts
import numpy as np
from eth_account import Account
# 🧮 MUTAÇÃO SOTA: encode_typed_data substitui a API depreciada
from eth_account.messages import encode_typed_data

ORACLE_URL = "http://127.0.0.1:8085/mine_fhe_channel"
DIMENSIONS = 384

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

# 🧮 MUTAÇÃO SOTA: Injeção da variável full_message
encoded_data = encode_typed_data(full_message=msg)
signed_message = Account.sign_message(encoded_data, private_key)
signature_hex = signed_message.signature.hex()

print("⚡ [AGENTE] Assinatura Criptográfica Concluída. Sem exposição ao Mempool.")

print("⚙️ [AGENTE] Encriptando Tensor SDE (L=1)...")
context = ts.context(ts.SCHEME_TYPE.CKKS, poly_modulus_degree=8192, coeff_mod_bit_sizes=[60, 40, 60])
context.global_scale = 2**40
context.generate_galois_keys()

query_tensor = np.random.uniform(-0.1, 0.1, DIMENSIONS).tolist()
enc_query = ts.ckks_vector(context, query_tensor)

payload = {
    "agent_address": agent_address,
    "amount": amount_to_pay,
    "nonce": current_nonce,
    "signature_hex": signature_hex,
    "context_b64": base64.b64encode(context.serialize(save_public_key=True, save_secret_key=False, save_galois_keys=True)).decode(),
    "query_b64": base64.b64encode(enc_query.serialize()).decode()
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
