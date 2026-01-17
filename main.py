import json
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
    url = url.split("?")[0].strip()
    if "threads.net" in url:
        url = url.replace("threads.net", "threads.com")
    return url

def iter_strings(obj):
    """Recursively yield every string inside dict/list JSON."""
    if isinstance(obj, dict):
        for v in obj.values():
            yield from iter_strings(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from iter_strings(v)
    elif isinstance(obj, str):
        yield obj

def extract_json_scripts(html: str) -> list[str]:
    # pega todos os <script type="application/json" ...>...</script>
    return re.findall(
        r'<script[^>]*type="application/json"[^>]*>(.*?)</script>',
        html,
        flags=re.DOTALL | re.IGNORECASE,
    )

def pick_best(urls: list[str]) -> str:
    # tenta escolher um "melhor"
    for u in urls:
        if "bytestart" not in u and "byteend" not in u and "range" not in u:
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

    scripts = extract_json_scripts(html)
    if not scripts:
        raise HTTPException(status_code=404, detail={"error": "No JSON script tags found"})

    mp4s = []

    for s in scripts:
        s = s.strip()
        # tenta carregar o JSON do script; se falhar, ignora esse script
        try:
            data = json.loads(s)
        except Exception:
            continue

        for st in iter_strings(data):
            # normaliza barras escapadas e unicode escapes
            # (json.loads já resolve \uXXXX, e aqui só trocamos \/ -> /)
            st2 = st.replace("\\/", "/")
            if ".mp4" in st2:
                # extrai URL completa dentro da string
                found = re.findall(r"https?://[^\"'\s]+\.mp4[^\"'\s]*", st2)
                if found:
                    mp4s.extend(found)

    # remove duplicados mantendo ordem
    seen = set()
    mp4s_unique = []
    for u in mp4s:
        if u not in seen:
            seen.add(u)
            mp4s_unique.append(u)

    if not mp4s_unique:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "No mp4 found inside JSON scripts",
                "hint": "Pode ser que esse post use outro formato (m3u8/mpd) ou o payload veio diferente.",
                "json_scripts_found": len(scripts),
            },
        )

    best = pick_best(mp4s_unique)
    return {"mp4": best, "source": page_url, "count": len(mp4s_unique)}
