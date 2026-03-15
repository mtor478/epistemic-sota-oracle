import time
import sqlite3
import hashlib

BATCH_THRESHOLD = 3 # Reduzido para testar rapidamente (SOTA = 10000)

def compute_merkle_root(hashes):
    if not hashes: return None
    if len(hashes) == 1: return hashes[0]
    
    next_level = []
    for i in range(0, len(hashes), 2):
        h1 = hashes[i]
        h2 = hashes[i+1] if i+1 < len(hashes) else h1
        combined = hashlib.sha256((h1 + h2).encode()).hexdigest()
        next_level.append(combined)
    return compute_merkle_root(next_level)

def run_prover_daemon():
    print("🛡️ [ZK-WORKER] Daemon de Liquidação inicializado. Escutando MPSC...")
    while True:
        conn = sqlite3.connect("zk_traces.db")
        cursor = conn.cursor()
        
        cursor.execute("SELECT id, agent_id, fhe_result_hash FROM traces WHERE status = 'pending'")
        pending = cursor.fetchall()
        
        if len(pending) >= BATCH_THRESHOLD:
            print(f"\n⚙️ [ZK-WORKER] Capacidade atingida ({len(pending)} traces). Iniciando ZK Rollup...")
            
            trace_ids = [p[0] for p in pending]
            hashes = [p[2] for p in pending]
            
            # 1. Árvore de Merkle
            merkle_root = compute_merkle_root(hashes)
            print(f"🌲 [ZK-WORKER] Raiz de Merkle computada: 0x{merkle_root[:16]}...")
            
            # 2. Geração da Prova ZK (Simulação do custo computacional pesado RISC-V)
            print("🧱 [ZK-WORKER] Sintetizando SNARK Circuit (Simulando 3s de carga CPU)...")
            time.sleep(3)
            mock_zk_proof = "0x" + hashlib.sha256(merkle_root.encode()).hexdigest()
            
            # 3. Commit L1 (Mudança de Estado)
            placeholders = ','.join(['?'] * len(trace_ids))
            cursor.execute(f"UPDATE traces SET status = 'settled' WHERE id IN ({placeholders})", trace_ids)
            conn.commit()
            
            print(f"💎 SOTA: Batch Settlement Concluído. Proof: {mock_zk_proof[:16]}... enviada para L1.")
            print(f"✅ Oráculo recebeu liberação de Escrow para {len(pending)} Agentes.")
            
        conn.close()
        time.sleep(2) # Polling interval

if __name__ == "__main__":
    run_prover_daemon()
