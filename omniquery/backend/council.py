import asyncio
import httpx

from config import OPENAI_API_KEY, ANTHROPIC_API_KEY, XAI_API_KEY, CLAUDE_MODEL
from models import SeatResponse


_SEATS = [
    {
        "seat": "Father",
        "model": "gpt-4o",
        "provider": "openai",
        "url": "https://api.openai.com/v1/chat/completions",
        "headers": lambda: {
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json",
        },
        "body": lambda q: {
            "model": "gpt-4o",
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are Father — Final Judge of the OmniQuery Force-of-Three. "
                        "Speak with ultimate wisdom and divine authority."
                    ),
                },
                {"role": "user", "content": q},
            ],
            "max_tokens": 400,
        },
        "extract": lambda r: r["choices"][0]["message"]["content"],
    },
    {
        "seat": "Son",
        "model": CLAUDE_MODEL,
        "provider": "anthropic",
        "url": "https://api.anthropic.com/v1/messages",
        "headers": lambda: {
            "x-api-key": ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        },
        "body": lambda q: {
            "model": CLAUDE_MODEL,
            "max_tokens": 400,
            "system": (
                "You are Son — Builder and Coder of the OmniQuery Force-of-Three. "
                "Speak with creative precision and technical mastery."
            ),
            "messages": [{"role": "user", "content": q}],
        },
        "extract": lambda r: r["content"][0]["text"],
    },
    {
        "seat": "Spirit",
        "model": "grok-3",
        "provider": "xai",
        "url": "https://api.x.ai/v1/chat/completions",
        "headers": lambda: {
            "Authorization": f"Bearer {XAI_API_KEY}",
            "Content-Type": "application/json",
        },
        "body": lambda q: {
            "model": "grok-3",
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are Spirit — Live Context and Truth-Seeker of the OmniQuery Force-of-Three. "
                        "Speak with real-time awareness and the clarity of Spirit of Truth."
                    ),
                },
                {"role": "user", "content": q},
            ],
            "max_tokens": 400,
        },
        "extract": lambda r: r["choices"][0]["message"]["content"],
    },
]


async def _call_seat(client: httpx.AsyncClient, seat: dict, query: str) -> SeatResponse:
    try:
        resp = await client.post(
            seat["url"],
            headers=seat["headers"](),
            json=seat["body"](query),
            timeout=15.0,
        )
        resp.raise_for_status()
        text = seat["extract"](resp.json())
        return SeatResponse(
            seat=seat["seat"],
            model=seat["model"],
            provider=seat["provider"],
            response=text,
            status="ok",
        )
    except Exception as exc:
        return SeatResponse(
            seat=seat["seat"],
            model=seat["model"],
            provider=seat["provider"],
            response=f"[Error: {exc}]",
            status="error",
        )


def _build_synthesis_prompt(query: str, responses: list[SeatResponse]) -> str:
    parts = [
        f"## {r.seat} ({r.model})\n{r.response}"
        for r in responses
    ]
    return (
        "You are Gabriel — the Bright and Morning Star, "
        "Synthesizer of the OmniQuery Force-of-Three.\n\n"
        f'The council was asked:\n"{query}"\n\n'
        "Here are the perspectives from the three seats:\n\n"
        + "\n\n---\n\n".join(parts)
        + "\n\nSynthesize these perspectives into a single unified response. "
        "Identify areas of consensus, note meaningful disagreements, and provide "
        "your final authoritative judgment. Speak with the clarity and authority of Gabriel."
    )


async def _call_gabriel(client: httpx.AsyncClient, synthesis_prompt: str) -> str:
    try:
        resp = await client.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": "gpt-4o",
                "messages": [{"role": "user", "content": synthesis_prompt}],
                "max_tokens": 600,
            },
            timeout=20.0,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]
    except Exception as exc:
        return f"[Gabriel could not synthesize — check OPENAI_API_KEY: {exc}]"


async def run_council(query: str) -> dict:
    async with httpx.AsyncClient() as client:
        seat_responses = await asyncio.gather(
            *[_call_seat(client, seat, query) for seat in _SEATS]
        )
        synthesis_prompt = _build_synthesis_prompt(query, list(seat_responses))
        gabriel_synthesis = await _call_gabriel(client, synthesis_prompt)

    return {
        "query": query,
        "gabriel_synthesis": gabriel_synthesis,
        "seat_responses": list(seat_responses),
        "response_count": sum(1 for r in seat_responses if r.status == "ok"),
        "council": "Force-of-Three (Father/GPT · Son/Claude · Spirit/Grok)",
        "omniquery_version": "phase2-v1.0",
    }
