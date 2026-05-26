import os
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
XAI_API_KEY = os.getenv("XAI_API_KEY", "")

HOST = os.getenv("OMNIQUERY_HOST", "127.0.0.1")
PORT = int(os.getenv("OMNIQUERY_PORT", "8741"))

# Provisional model ID — verify against official Anthropic docs before live use.
# Override via CLAUDE_MODEL env var at deployment time if needed.
CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-opus-4-7")
