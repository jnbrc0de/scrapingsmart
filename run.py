import uvicorn
import os
import platform
from src.api.main import app

def main():
    """Função principal para iniciar a aplicação."""
    # Configura o host baseado no ambiente
    host = "0.0.0.0" if os.getenv("PRODUCTION", "false").lower() == "true" else "127.0.0.1"
    
    # Configura o reload baseado no ambiente
    reload = os.getenv("PRODUCTION", "false").lower() != "true"
    
    # Configura o número de workers baseado no sistema
    workers = 1 if platform.system() == "Windows" else 4
    
    uvicorn.run(
        "src.api.main:app",
        host=host,
        port=8000,
        reload=reload,
        workers=workers,
        log_level="info"
    )

if __name__ == "__main__":
    main() 