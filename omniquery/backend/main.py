from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from models import QueryRequest, QueryResponse, HealthResponse
from council import run_council

app = FastAPI(
    title="OmniQuery Backend",
    version="phase2-v1.0",
    docs_url=None,
    redoc_url=None,
)

# localhost-only — no cross-origin needed for Phase 2
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1", "http://localhost"],
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        version="phase2-v1.0",
        council="Force-of-Three",
        seats=["Father/GPT", "Son/Claude", "Spirit/Grok"],
    )


@app.post("/query", response_model=QueryResponse)
async def query(request: QueryRequest) -> QueryResponse:
    if not request.query.strip():
        raise HTTPException(status_code=400, detail="query must not be empty")
    result = await run_council(request.query)
    return QueryResponse(**result)
