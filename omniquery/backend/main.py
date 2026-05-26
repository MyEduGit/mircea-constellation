from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import HOST, PORT
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
    result = await run_council(request.query)
    return QueryResponse(**result)


if __name__ == "__main__":
    # Entry point binds to the validated localhost-only HOST from config.
    import uvicorn

    uvicorn.run(app, host=HOST, port=PORT)
