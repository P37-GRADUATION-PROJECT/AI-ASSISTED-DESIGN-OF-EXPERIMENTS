from fastapi import FastAPI

from app.config import get_settings

app = FastAPI(title="P37 DoE Assistant", version="0.1.0")


@app.get("/health")
def health() -> dict[str, object]:
    settings = get_settings()
    return {"status": "ok", "llm_enabled": settings.llm_enabled}
