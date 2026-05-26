from typing import Literal
from pydantic import BaseModel


class QueryRequest(BaseModel):
    query: str


class SeatResponse(BaseModel):
    seat: str
    model: str
    provider: str
    response: str
    status: Literal["ok", "error"]


class QueryResponse(BaseModel):
    query: str
    gabriel_synthesis: str
    seat_responses: list[SeatResponse]
    response_count: int
    council: str = "Force-of-Three (Father/GPT · Son/Claude · Spirit/Grok)"
    omniquery_version: str = "phase2-v1.0"


class HealthResponse(BaseModel):
    status: str
    version: str
    council: str
    seats: list[str]
