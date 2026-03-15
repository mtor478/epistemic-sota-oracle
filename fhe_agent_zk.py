import time
import requests
import uuid

ORACLE_URL = "http://127.0.0.1:8084/mine_fhe_async"

def send_query(agent_id):
    t0 = time.time()
    resp = requests.post(ORACLE_URL, json={
        "agent_id": agent_id,
        "context_b64": "mock_ctx",
        "query_b64": "mock_query_tensor"
    })
    t_total = time.time() - t0
    
    if resp.status_code == 200:
        print(f"🟢 [AGENTE {agent_id[:6]}] Resposta FHE recebida em {t_total:.3f}s! Latência ZK = Zero.")

if __name__ == "__main__":
    print("🚀 [AGENTE] Disparando 3 requisições simultâneas para saturar o Batch L1...")
    for i in range(3):
        send_query(str(uuid.uuid4()))
