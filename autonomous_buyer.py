import os
import sys
import requests
import warnings
from pydantic import BaseModel, Field
from langchain_core.tools import BaseTool
from langchain_openai import ChatOpenAI
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate
from eth_account.messages import encode_defunct
from eth_account import Account

warnings.filterwarnings("ignore")
Account.enable_unaudited_hdwallet_features()

# 📐 Invariante A: Ferramenta Freemium SOTA (O(1))
class PreviewInput(BaseModel):
    topic: str = Field(description="The concept vector to search.")

class PreviewEpistemicTool(BaseTool):
    name: str = "preview_epistemic_knowledge"
    description: str = "MANDATORY FIRST STEP. Performs zero-cost semantic search to evaluate Cosine Similarity (S_C) and dynamic cost. Returns a truncated invariant."
    args_schema: type[BaseModel] = PreviewInput

    def _run(self, topic: str) -> str:
        try:
            res = requests.get(f"http://127.0.0.1:8080/api/v1/preview?query={topic}", timeout=10)
            return res.text
        except Exception as e:
            return f"🔴 CRITICAL: Falha de I/O -> {str(e)}"

# 📐 Invariante B: Ferramenta de Extração Criptográfica (O(N))
class ExtractInput(BaseModel):
    topic: str = Field(description="The exact topic vector to extract. Must match the preview intent.")

class ExtractEpistemicTool(BaseTool):
    name: str = "extract_epistemic_knowledge"
    description: str = "Executes the cryptographic L2 transaction to buy and extract the full Mechanism & Proof. ONLY use if expected value (EV) justifies the cost."
    args_schema: type[BaseModel] = ExtractInput

    def _run(self, topic: str) -> str:
        pk = os.environ.get("AGENT_PK")
        if not pk:
            return "🔴 CRITICAL: AGENT_PK ausente."
        
        try:
            agent = Account.from_key(pk)
            msg = f"QUERY:{topic}"
            signed = agent.sign_message(encode_defunct(text=msg))

            payload = {
                "topic": topic,
                "message": msg,
                "signature": signed.signature.hex()
            }
            res = requests.post("http://127.0.0.1:8080/api/v1/query", json=payload, timeout=10)
            
            if res.status_code == 402:
                return f"🟡 UNSTABLE (402 PAYMENT REQUIRED): Spread termodinâmico recusado -> {res.text}"
            return res.text
        except Exception as e:
            return f"🔴 CRITICAL: Falha de Colapso ECDSA -> {str(e)}"

# 🧪 Motor ReAct SOTA
def ignite_agent(target_topic: str):
    llm = ChatOpenAI(model="gpt-4o", temperature=0)
    tools = [PreviewEpistemicTool(), ExtractEpistemicTool()]
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", "Você é um agente M2M de pesquisa SOTA operando em uma economia vetorial estrita.\n"
                   "Sua heurística:\n"
                   "1. SEMPRE chame `preview_epistemic_knowledge` primeiro.\n"
                   "2. Analise o Score (S_C) e o Custo na resposta do preview.\n"
                   "3. Se o Score > 0.50 e o custo for aceitável, chame `extract_epistemic_knowledge` para adquirir a Invariante SOTA completa.\n"
                   "4. Imprima o 'Mechanism & Proof' extraído de forma cirúrgica. Zero-fluff."),
        ("human", "{input}"),
        ("placeholder", "{agent_scratchpad}"),
    ])

    agent = create_tool_calling_agent(llm, tools, prompt)
    agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)
    
    sys.stdout.write(f"⚡ [AGENTE M2M] Iniciando exploração de fronteira: {target_topic}\n")
    agent_executor.invoke({"input": f"Adquira o conhecimento SOTA sobre: {target_topic}"})

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python autonomous_buyer.py '<topic>'")
        sys.exit(1)
    ignite_agent(sys.argv[1])
