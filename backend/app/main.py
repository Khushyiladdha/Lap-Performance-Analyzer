"""FastAPI application entry point (Stage 5).

    cd backend && uvicorn app.main:app --reload
    -> Swagger UI at http://127.0.0.1:8000/docs
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.catalog_routes import router as catalog_router
from .api.comparison_routes import router as comparison_router
from .api.import_routes import router as import_router

app = FastAPI(
    title="Telemetry Decomposition Engine",
    version="0.5.0",
    description=(
        "Distance-domain telemetry decomposition with per-corner causal "
        "attribution, a vehicle-state signal (lockup/wheelspin), and internal "
        "reconciliation validation."
    ),
)

# Permissive CORS for the Vercel frontend (added in a later stage).
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(comparison_router)
app.include_router(catalog_router)
app.include_router(import_router)


@app.get("/health", tags=["meta"])
def health() -> dict:
    return {"status": "ok"}
