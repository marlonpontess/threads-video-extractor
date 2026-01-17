import re
import requests
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI()

class ExtractRequest(BaseModel):
    url: str

@app.get("/health")
def health():
    return {"ok": True}

def normalize_threads_url(url: str) -> str:
    # remove querystring
    url = url.split("?")[0].strip()

    # garante domínio threads.com
    if "threads.net" in url:
        url = url.replace("threads.net", "threads.com")

    return url

def pick_best_mp4(urls: list[str]) -> str:
    # Preferir urls com "mp4" e sem "bytestart"/range, etc.
    # Em geral, qualquer uma funciona; escolhemos a primeira "limpa".
    for u in urls:
        if "bytestart" not in u and "byteend" not in u:
            return u
    return urls[0]

@app.post("/extract")
def extract(req: ExtractRequest):
    page_url = normalize_threads_url(req.url)

    headers = {
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
    }

    r = requests.get(page_url, headers=headers, timeout=20, allow_redirects=True)
    if r.status_code >= 400:
        raise HTTPException(status_code=502, detail=f"Failed to fetch page: {r.status_code}")

    html = r.text

    # Extrai qualquer URL de mp4 embutida (normalmente aparece no JSON data-sjs)
    mp4_urls = re.findall(r"https?:\/\/[^\"'\\\s]+\.mp4[^\"'\\\s]*", html)

    if not mp4_urls:
        # Ajuda no debug: indica se pelo menos vimos o script JSON
        has_json_script = 'type="application/json"' in html or "data-sjs" in html
        raise HTTPException(
            status_code=404,
            detail={
                "error": "No mp4 found in response HTML",
                "hint": "Threads may be returning different HTML to your server (bot/region/headers).",
                "saw_json_script": has_json_script,
            },
        )

    best = pick_best_mp4(mp4_urls)

    return {"mp4": best, "source": page_url, "count": len(mp4_urls)}
