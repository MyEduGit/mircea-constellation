from typing import Literal, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator

ErrorCode = Literal[
    "provider_unavailable",
    "timeout",
    "invalid_response",
    "synthesis_unavailable",
]


class QueryRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: str = Field(..., max_length=4000)

    @field_validator("query")
    @classmethod
    def _validate_query(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("query must not be empty or whitespace-only")
        return value


class SeatResponse(BaseModel):
    seat: str
    model: str
    provider: str
    response: str
    status: Literal["ok", "error"]
    error: Optional[ErrorCode] = None


class QueryResponse(BaseModel):
    query: str
    gabriel_synthesis: Optional[str]
    synthesis_status: Literal["ok", "error"]
    synthesis_error: Optional[ErrorCode] = None
    seat_responses: list[SeatResponse]
    response_count: int
    council: str = "Force-of-Three (Father/GPT · Son/Claude · Spirit/Grok)"
    omniquery_version: str = "phase2-v1.0"


class HealthResponse(BaseModel):
    status: str
    version: str
    council: str
    seats: list[str]
