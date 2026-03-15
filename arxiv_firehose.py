import asyncio
import aiohttp
import xml.etree.ElementTree as ET
import sys

# 📐 Invariantes Topológicas (Sanitizadas)
ARXIV_API = "http://export.arxiv.org/api/query"
MINER_ENDPOINT = "http://127.0.0.1:8081/mine"
DOMAINS = ["cs.AI", "cs.NE", "math.OC", "q-bio.NC"]
MAX_VECTORS = 50

async def extract_entropy(session: aiohttp.ClientSession, category: str) -> str:
    params = {
        "search_query": f"cat:{category}",
        "sortBy": "submittedDate",
        "sortOrder": "descending",
        "max_results": str(MAX_VECTORS)
    }
    print(f"🔍 [SENSOR] Sondando gradiente ArXiv: {category}")
    async with session.get(ARXIV_API, params=params) as response:
        if response.status == 200:
            return await response.text()
        return ""

async def inject_tensor(session: aiohttp.ClientSession, payload: dict) -> None:
    backoff = 1
    max_backoff = 60
    
    while True:
        try:
            async with session.post(MINER_ENDPOINT, json=payload) as response:
                if response.status == 200:
                    print("🟢 [INJECTOR] Tensor absorvido pelo Reator.")
                    return
                elif response.status == 503:
                    print(f"🟡 [INJECTOR] Saturação Térmica (503). Recuo: {backoff}s")
                    await asyncio.sleep(backoff)
                    backoff = min(backoff * 2, max_backoff)
                else:
                    print(f"🔴 [INJECTOR] Anomalia: HTTP {response.status}")
                    return
        except Exception as e:
            print(f"🔴 [INJECTOR] Colapso de Conexão: {e}")
            await asyncio.sleep(5)

async def firehose_daemon():
    print("⚙️ [FIREHOSE] Ignição do Bootstrap Autocatalítico SOTA...")
    
    async with aiohttp.ClientSession() as session:
        for domain in DOMAINS:
            xml_data = await extract_entropy(session, domain)
            if not xml_data:
                continue
            
            try:
                root = ET.fromstring(xml_data)
                entries = root.findall("{http://www.w3.org/2005/Atom}entry")
                
                for entry in entries:
                    title_el = entry.find("{http://www.w3.org/2005/Atom}title")
                    summary_el = entry.find("{http://www.w3.org/2005/Atom}summary")
                    
                    if title_el is None or summary_el is None:
                        continue
                        
                    title = title_el.text.replace("\n", " ").strip()
                    summary = summary_el.text.replace("\n", " ").strip()
                    
                    content = f"Title: {title}. Abstract: {summary}"
                    
                    print(f"⚡ [FIREHOSE] Transmutando: {title[:60]}...")
                    await inject_tensor(session, {"query": content})
                    
                    await asyncio.sleep(2)
                    
            except ET.ParseError:
                print(f"🔴 [SENSOR] Falha na decodificação XML para o domínio {domain}")

    print("🏁 [FIREHOSE] Ciclo Termodinâmico Concluído. Matriz Qdrant expandida.")

if __name__ == "__main__":
    try:
        asyncio.run(firehose_daemon())
    except KeyboardInterrupt:
        print("\n🛑 [FIREHOSE] Interrupção manual detectada. Colapsando graciosamente.")
        sys.exit(0)
