from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, HttpUrl
from typing import List, Optional
from supabase import create_client
from config.settings import settings

app = FastAPI(title="Scraping API")

supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)

class URLIn(BaseModel):
    url: HttpUrl
    domain: str

class URLOut(BaseModel):
    url: HttpUrl
    domain: str
    status: str
    next_scrape_at: Optional[str]

class ScrapeResult(BaseModel):
    url: HttpUrl
    price: Optional[float]
    last_checked: Optional[str]
    status: str

@app.get("/urls", response_model=List[URLOut])
def list_urls():
    resp = supabase.table("monitored_urls").select("*").execute()
    return resp.data

@app.post("/urls", response_model=URLOut)
def add_url(url_in: URLIn):
    data = url_in.dict()
    data["status"] = "active"
    resp = supabase.table("monitored_urls").insert(data).execute()
    if not resp.data:
        raise HTTPException(status_code=400, detail="Erro ao adicionar URL")
    return resp.data[0]

@app.get("/results/{url}", response_model=ScrapeResult)
def get_result(url: str):
    resp = supabase.table("scrape_results").select("*").eq("url", url).order("last_checked", desc=True).limit(1).execute()
    if not resp.data:
        raise HTTPException(status_code=404, detail="Resultado não encontrado")
    return resp.data[0] 