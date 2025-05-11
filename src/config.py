import os
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

PROXY_URL = os.getenv("PROXY_URL")  # Exemplo: http://user:pass@host:port

# Parâmetros de scraping
SCRAPE_TIMEOUT = int(os.getenv("SCRAPE_TIMEOUT", 30))  # segundos
MAX_RETRIES = int(os.getenv("MAX_RETRIES", 3))
CONCURRENCY = int(os.getenv("CONCURRENCY", 10))

# Parâmetros de agendamento
SCHEDULE_INTERVAL_HOURS = int(os.getenv("SCHEDULE_INTERVAL_HOURS", 12))
SCHEDULE_JITTER_MINUTES = int(os.getenv("SCHEDULE_JITTER_MINUTES", 30)) 