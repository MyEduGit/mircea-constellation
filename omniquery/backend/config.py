import os
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
XAI_API_KEY = os.getenv("XAI_API_KEY", "")

_LOCALHOST_ALLOWED = {"127.0.0.1", "localhost", "::1"}


def _resolve_host() -> str:
    # Localhost-only by doctrine. A non-localhost OMNIQUERY_HOST is rejected
    # outright so the backend can never be bound to a public interface.
    requested = os.getenv("OMNIQUERY_HOST", "127.0.0.1").strip()
    if requested not in _LOCALHOST_ALLOWED:
        raise ValueError(
            f"OMNIQUERY_HOST={requested!r} rejected. "
            "OmniQuery backend binds to localhost (127.0.0.1) only."
        )
    return "127.0.0.1"


HOST = _resolve_host()
PORT = int(os.getenv("OMNIQUERY_PORT", "8741"))

# Provisional model ID — verify against official Anthropic docs before live use.
# Override via CLAUDE_MODEL env var at deployment time if needed.
CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-opus-4-7")
