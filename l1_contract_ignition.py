import os
import hashlib
from web3 import Web3
from dotenv import load_dotenv
import solcx

load_dotenv(os.path.expanduser("~/epistemic_ecosystem.env"))
rpc_url = os.getenv("RPC_URL_HTTP", "")
pk = os.getenv("AGENT_PRIVATE_KEY", "")

print("⚙️ [L1] Instalando Solc 0.8.25...")
solcx.install_solc('0.8.25')

# 🧮 A INVARIANTE TOPOLÓGICA SOTA: Aniquilação do colapso de CWD.
# O autômato descobre a sua própria localização física no disco em tempo de execução O(1).
base_dir = os.path.dirname(os.path.abspath(__file__))
contract_path = os.path.join(base_dir, "contracts", "EpistemicQuantVault.sol")

with open(contract_path, "r") as file:
    sol_file = file.read()

print("⚙️ [L1] Compilando EVM Bytecode (Quant Vault)...")
compiled_sol = solcx.compile_source(
    sol_file,
    output_values=['abi', 'bin'],
    solc_version='0.8.25'
)
contract_id, contract_interface = compiled_sol.popitem()
bytecode = contract_interface['bin']
abi = contract_interface['abi']

validators = []
for port in [8091, 8092, 8093, 8094]:
    v_pk = "0x" + hashlib.sha256(f"SOTA_VALIDATOR_NODE_{port}_V1".encode()).hexdigest()
    validators.append(Web3().eth.account.from_key(v_pk).address)

# Endereço oficial do Uniswap V3 SwapRouter02 na Arbitrum (Mainnet/Sepolia)
UNISWAP_V3_ROUTER = "0x68b3465833fb72A70ecDF485E0e4C7bD8665Fc45"

print(f"🧬 [L1] Validadores BFT: {validators}")
print(f"💱 [L1] Roteador DEX Acoplado: {UNISWAP_V3_ROUTER}")

w3 = Web3(Web3.HTTPProvider(rpc_url))
if not rpc_url or not w3.is_connected():
    print("🟡 [L1] Rede Indisponível. Simulando Deploy em Memória...")
    with open(os.path.expanduser("~/epistemic_ecosystem.env"), "a") as f:
        f.write("\nCONTRACT_ADDRESS=0x0000000000000000000000000000000000001337\n")
else:
    account = w3.eth.account.from_key(pk)
    balance = w3.eth.get_balance(account.address)
    if balance < w3.to_wei(0.001, 'ether'):
        print("🟡 [L1] Saldo Insuficiente para Gas. Simulando Deploy...")
        with open(os.path.expanduser("~/epistemic_ecosystem.env"), "a") as f:
            f.write("\nCONTRACT_ADDRESS=0x0000000000000000000000000000000000001337\n")
    else:
        print("🚀 [L1] Injetando Cofre Quantitativo na Arbitrum...")
        Contract = w3.eth.contract(abi=abi, bytecode=bytecode)
        
        # 🧮 O constructor agora exige a array de validadores E o endereço do roteador DEX
        tx = Contract.constructor(validators, w3.to_checksum_address(UNISWAP_V3_ROUTER)).build_transaction({
            'from': account.address,
            'nonce': w3.eth.get_transaction_count(account.address),
            'gas': 4000000,
            'maxFeePerGas': int(w3.eth.gas_price * 1.5),
            'maxPriorityFeePerGas': w3.to_wei('0.001', 'gwei')
        })
        signed_tx = w3.eth.account.sign_transaction(tx, private_key=pk)
        tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
        tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
        
        contract_address = tx_receipt.contractAddress
        print(f"🟢 [L1] Singularidade Implantada! Cofre ativo em: {contract_address}")
        
        with open(os.path.expanduser("~/epistemic_ecosystem.env"), "a") as f:
            f.write(f"\nCONTRACT_ADDRESS={contract_address}\n")
