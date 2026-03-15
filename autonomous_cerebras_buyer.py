import os
import sys
import requests
import warnings
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from langchain_core.tools import BaseTool
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.prebuilt import create_react_agent
from eth_account.messages import encode_defunct
from eth_account import Account

warnings.filterwarnings("ignore")
Account.enable_unaudited_hdwallet_features()
load_dotenv()

class PreviewInput(BaseModel):
    topic: str = Field(description="The concept vector to search.")

class PreviewEpistemicTool(BaseTool):
    name: str = "preview_epistemic_knowledge"
    description: str = "MANDATORY FIRST STEP. Performs zero-cost semantic search to evaluate Cosine Similarity (S_C) and dynamic cost. Returns a truncated invariant."
    args_schema: type[BaseModel] = PreviewInput

    def _run(self, topic: str) -> str:
        try:
            res = requests.get(f"http://127.0.0.1:8080/api/v1/preview?query={topic}", timeout=10)
            if res.status_code == 402:
                # 📐 Invariante SOTA: Força a parada do LangGraph
                return "S_C < 0.50 DETECTADO. ORDEM ESTRITA: PARE O GRAFO IMEDIATAMENTE. RESPONDA APENAS: 'Autopoiese acionada no Backend. Transação abortada.'"
            return res.text
        except Exception as e:
            return f"🔴 CRITICAL: Falha de I/O -> {str(e)}"

class ExtractInput(BaseModel):
    topic: str = Field(description="The exact topic vector to extract. Must match the preview intent.")

class ExtractEpistemicTool(BaseTool):
    name: str = "extract_epistemic_knowledge"
    description: str = "Executes cryptographic L2 transaction to extract Mechanism & Proof. ONLY use if expected value justifies the cost."
    args_schema: type[BaseModel] = ExtractInput

    def _run(self, topic: str) -> str:
        pk = os.environ.get("AGENT_PK")
        if not pk:
            return "🔴 CRITICAL: AGENT_PK ausente no .env."
        
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

def ignite_agent(target_topic: str):
    if not os.environ.get("CEREBRAS_API_KEY"):
        sys.exit("🔴 CRITICAL: CEREBRAS_API_KEY ausente no ambiente.")

    llm = ChatOpenAI(
        model="llama3.1-8b",
        api_key=os.environ.get("CEREBRAS_API_KEY"),
        base_url="https://api.cerebras.ai/v1",
        temperature=0
    )
    tools = [PreviewEpistemicTool(), ExtractEpistemicTool()]
    
    system_prompt = """Você é um agente M2M de pesquisa SOTA estrito e impiedoso.
Sua heurística absoluta:
1. SEMPRE chame `preview_epistemic_knowledge` com o tópico.
2. Analise o Score (S_C).
3. REGRA DE OURO: Se S_C < 0.50, A INFORMAÇÃO É LIXO. VOCÊ ESTÁ ESTRITAMENTE PROIBIDO de chamar `extract_epistemic_knowledge`. Em vez disso, retorne imediatamente: 'ABORTADO: Assimetria Semântica (S_C < 0.5). Rejeitando extração.'
4. Apenas se S_C >= 0.50 e o custo for aceitável, chame `extract_epistemic_knowledge`.
Zero-fluff. Sem desculpas."""

    agent_executor = create_react_agent(llm, tools)
    
    sys.stdout.write(f"⚡ [AGENTE CEREBRAS SOTA] Iniciando exploração no Grafo: {target_topic}\n")
    
    inputs = {
        "messages": [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"Adquira o conhecimento SOTA sobre: {target_topic}")
        ]
    }
    
    for event in agent_executor.stream(inputs, stream_mode="values"):
        message = event["messages"][-1]
        if message.content:
            print(f"🧠 [Estado LLM]: {message.content}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python autonomous_cerebras_buyer.py '<topic>'")
        sys.exit(1)
    ignite_agent(sys.argv[1])
