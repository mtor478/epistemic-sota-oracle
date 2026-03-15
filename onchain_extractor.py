import os
import time
import pandas as pd
import requests
from web3 import Web3
from dotenv import load_dotenv

load_dotenv(os.path.expanduser("~/epistemic_ecosystem.env"))

RPC_URL = os.getenv("RPC_URL_HTTP", "").strip()
CONTRACT_ADDRESS = os.getenv("CONTRACT_ADDRESS", "").strip()

if not RPC_URL or not CONTRACT_ADDRESS:
    raise ValueError("🔴 CRITICAL: RPC_URL ou CONTRACT_ADDRESS ausentes.")

w3 = Web3(Web3.HTTPProvider(RPC_URL))
abi = [{
    "anonymous": False,
    "inputs": [
        {"indexed": False, "internalType": "int256[]", "name": "targetWeights", "type": "int256[]"},
        {"indexed": False, "internalType": "uint256", "name": "timestamp", "type": "uint256"}
    ],
    "name": "PortfolioMutated",
    "type": "event"
}]

contract = w3.eth.contract(address=w3.to_checksum_address(CONTRACT_ADDRESS), abi=abi)
event_signature_hash = w3.to_hex(w3.keccak(text="PortfolioMutated(int256[],uint256)"))
contract_addr = w3.to_checksum_address(CONTRACT_ADDRESS)

print("⚡ [EXTRACTOR] Varrendo a Blockchain Arbitrum (Deep Scan SOTA)...")
try:
    latest_block = w3.eth.block_number
    # 🧮 DILATAÇÃO SOTA: Varredura expandida para 50.000 blocos (~3.6 horas de histórico L1)
    start_block = max(0, latest_block - 50000)
    
    CHUNK_SIZE = 10
    logs = []
    
    total_chunks = (latest_block - start_block) // CHUNK_SIZE
    print(f"⚡ [EXTRACTOR] Ingerindo {latest_block - start_block} blocos em {total_chunks} micro-lotes...")
    print(f"⏳ Tempo estimado de extração termodinâmica: ~8 minutos.")
    
    for i, chunk_start in enumerate(range(start_block, latest_block + 1, CHUNK_SIZE)):
        chunk_end = min(chunk_start + CHUNK_SIZE - 1, latest_block)
        
        filter_params = {
            "address": contract_addr,
            "fromBlock": hex(chunk_start),
            "toBlock": hex(chunk_end),
            "topics": [event_signature_hash]
        }
        
        try:
            chunk_logs_raw = w3.eth.get_logs(filter_params)
            for raw_log in chunk_logs_raw:
                decoded_log = contract.events.PortfolioMutated().process_log(raw_log)
                logs.append(decoded_log)
                
            if i % 100 == 0:
                print(f"   ... Progresso: {i}/{total_chunks} lotes. Eventos encontrados: {len(logs)}")
                
            # 🧮 RESFRIAMENTO OTIMIZADO: 0.1s garante ~10 req/s, bem dentro dos 330 CU/s da Alchemy
            time.sleep(0.1)
            
        except requests.exceptions.HTTPError as e:
            print(f"\n🔴 [DIAGNÓSTICO] Falha HTTP Crítica no chunk {chunk_start}-{chunk_end}.")
            exit(1)
        except Exception as e:
            time.sleep(2)
            chunk_logs_raw = w3.eth.get_logs(filter_params)
            for raw_log in chunk_logs_raw:
                decoded_log = contract.events.PortfolioMutated().process_log(raw_log)
                logs.append(decoded_log)
    
    if not logs:
        print("🟡 [EXTRACTOR] Vácuo absoluto. O Autômato SDE gerou alocações on-chain neste horizonte?")
        print("💡 DIRETRIZ: Assegure-se de que o autopoietic_daemon.py esteja rodando e injetando transações.")
        exit(0)
        
    records = []
    for log in logs:
        weights = log.args.targetWeights
        w_usdc = weights[0] / 10000.0 if len(weights) > 0 else 0
        w_weth = weights[1] / 10000.0 if len(weights) > 1 else 0
        w_wbtc = weights[2] / 10000.0 if len(weights) > 2 else 0
        
        records.append({
            "block_number": log.blockNumber,
            "timestamp": log.args.timestamp,
            "w_usdc": w_usdc,
            "w_weth": w_weth,
            "w_wbtc": w_wbtc,
            "tx_hash": log.transactionHash.hex()
        })
        
    df = pd.DataFrame(records)
    df.to_csv("audit_events.csv", index=False)
    print(f"🟢 [EXTRACTOR] {len(df)} mutações L1 capturadas e cravadas em audit_events.csv.")

except Exception as e:
    print(f"🔴 [EXTRACTOR] Colapso: {e}")
