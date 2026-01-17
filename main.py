import re
import html
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, HttpUrl
import httpx

app = FastAPI(title="Threads MP4 Extractor")

class ExtractRequest(BaseModel):
    url: HttpUrl

# Regex para capturar URLs .mp4 (escapadas ou não)
MP4_RE = re.compile(
    r"https:\\/\\/[^\"\\s]+?\\.mp4[^\"\\s]*|https://[^\"\\s]+?\\.mp4[^\"\\s]*"
)

def normalize(u: str) -> str:
    u = u.replace("\\/", "/")
    u = html.unescape(u)
    return u

@app.get("/health")
def health():
    return {"ok": True}

@app.post("/extract")
async def extract(req: ExtractRequest):
    url = str(req.url)

    if "threads.com/" not in url:
        raise HTTPException(status_code=400, detail="URL precisa ser do Threads")

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
            "AppleWebKit/605.1.15 (KHTML, like Gecko) V
