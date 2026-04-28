"""
ContextIQ server entry point.

  Production:  python server.py
  Dev mode:    DEV_MODE="true" python server.py   (hot reload enabled)
"""

import os
import uvicorn
from dotenv import load_dotenv

load_dotenv()

if __name__ == "__main__":
    dev = os.getenv("DEV_MODE", "false").lower() == "true"

    print(f"Starting ContextIQ — {'dev mode (hot reload on)' if dev else 'production mode'}")
    print("Open http://127.0.0.1:8000\n")

    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", "8000"))

    uvicorn.run(
        "api.main:app",
        host=host,
        port=port,
        reload=dev,
        log_level="info",
    )
