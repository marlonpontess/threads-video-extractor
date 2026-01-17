import re
import html
import requests
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI()

class ExtractRequest(BaseModel):
    url: str

@app.get("/health")
def health():
    return {"ok": True}

@app.post("/extract")
def extract(req: ExtractRequest):
    print("=== /extract called ===")
    print("URL:", req.url)

    headers = {
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
    }

    try:
        r = requests.get(req.url, headers=headers, timeout=20, allow_redirects=True)
        print("Fetch status:", r.status_code)
        print("Final URL:", r.url)
        print("HTML size:", len(r.text))
    except Exception as e:
        print("REQUEST ERROR:", repr(e))
        raise HTTPException(status_code=502, detail=f"Request failed: {repr(e)}")

    if r.status_code != 200:
        print("Non-200 body snippet:", r.text[:300])
        raise HTTPException(status_code=502, detail=f"Failed to fetch page: {r.status_code}")

    # tenta achar mp4 (primeiro no formato escapado, depois normal)
    m = re.search(r'https:\\/\\/[^"\\s]+\\.mp4[^"\\s]*', r.text)
    if m:
        video_url = m.group(0).replace("\\/", "/")
        video_url = html.unescape(video_url)
        print("FOUND (escaped) mp4:", video_url)
        return {"video_url": video_url}

    m2 = re.search(r'https://[^"\s]+\.mp4[^"\s]*', r.text)
    if m2:
        video_url = html.unescape(m2.group(0))
        print("FOUND mp4:", video_url)
        return {"video_url": video_url}

    # Se não achou, devolve erro com pista
    print("NO MP4 FOUND. HTML snippet:", r.text[:500])
    raise HTTPException(status_code=404, detail="No mp4 found in page HTML")
