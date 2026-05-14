#!/usr/bin/env python3
"""
cognee_config.py — Multi-Provider Cognee Configuration
Mircea's Constellation / UrantiOS governed

Supports: Ollama, Anthropic (Claude), OpenAI (ChatGPT), xAI (Grok),
Perplexity, Google (Gemini), Groq, Together AI

Usage:
    import cognee_config
    cognee_config.init()                          # auto-detect Ollama
    cognee_config.init(provider="anthropic")      # use Claude
    cognee_config.init(provider="openai")         # use ChatGPT
    cognee_config.init(provider="xai")            # use Grok
    cognee_config.init(provider="perplexity")     # use Perplexity
    cognee_config.init(provider="gemini")          # use Gemini
"""
import os
import cognee

OLLAMA_LOCAL = "http://localhost:11434"
OLLAMA_REMOTE = "http://204.168.143.98:11434"

PROVIDERS = {
    "ollama": {
        "provider": "ollama",
        "model": "ollama/qwen2.5:32b",
        "endpoint": None,
        "key_env": None,
        "key_default": "ollama",
    },
    "anthropic": {
        "provider": "anthropic",
        "model": "anthropic/claude-sonnet-4-6",
        "endpoint": "",
        "key_env": "ANTHROPIC_API_KEY",
        "key_default": None,
    },
    "openai": {
        "provider": "openai",
        "model": "gpt-4o",
        "endpoint": "",
        "key_env": "OPENAI_API_KEY",
        "key_default": None,
    },
    "xai": {
        "provider": "xai",
        "model": "xai/grok-2",
        "endpoint": "https://api.x.ai/v1",
        "key_env": "XAI_API_KEY",
        "key_default": None,
    },
    "perplexity": {
        "provider": "perplexity",
        "model": "perplexity/sonar-pro",
        "endpoint": "https://api.perplexity.ai",
        "key_env": "PERPLEXITY_API_KEY",
        "key_default": None,
    },
    "gemini": {
        "provider": "gemini",
        "model": "gemini/gemini-2.5-pro",
        "endpoint": "",
        "key_env": "GEMINI_API_KEY",
        "key_default": None,
    },
    "groq": {
        "provider": "groq",
        "model": "groq/llama-3.3-70b-versatile",
        "endpoint": "https://api.groq.com/openai/v1",
        "key_env": "GROQ_API_KEY",
        "key_default": None,
    },
    "together": {
        "provider": "together_ai",
        "model": "together_ai/meta-llama/Llama-3.3-70B-Instruct-Turbo",
        "endpoint": "https://api.together.xyz/v1",
        "key_env": "TOGETHER_API_KEY",
        "key_default": None,
    },
}

EMBEDDING_PROVIDER = "fastembed"
EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"
EMBEDDING_DIMENSIONS = 384

DATASET_URANTIA = "urantia_book"
DATASET_PHD = "phd_triune_monism"
DATASET_NEMOCLAW = "nemoclaw_memory"
DATASET_CORPUS = "mircea_corpus"


def _check_ollama(endpoint, timeout=2.0):
    import urllib.request
    try:
        req = urllib.request.Request(f"{endpoint}/api/tags", method="GET")
        with urllib.request.urlopen(req, timeout=timeout):
            return True
    except Exception:
        return False


def _resolve_key(prov_cfg):
    if prov_cfg["key_env"]:
        key = os.environ.get(prov_cfg["key_env"])
        if key:
            return key
    secrets_path = os.path.expanduser("~/.openclaw/secrets.env")
    if os.path.exists(secrets_path) and prov_cfg["key_env"]:
        with open(secrets_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    if k.strip() == prov_cfg["key_env"]:
                        return v.strip()
    return prov_cfg.get("key_default")


def init(provider="auto", model=None, verbose=True):
    """
    Initialize Cognee with any LLM provider.

    provider: "ollama", "anthropic", "openai", "xai", "perplexity",
              "gemini", "groq", "together", or "auto" (tries Ollama first)
    model:    override the default model for the provider
    """
    if provider == "auto":
        if _check_ollama(OLLAMA_LOCAL):
            provider = "ollama"
            endpoint_override = OLLAMA_LOCAL
        elif _check_ollama(OLLAMA_REMOTE):
            provider = "ollama"
            endpoint_override = OLLAMA_REMOTE
        else:
            for name in ["anthropic", "openai", "xai", "perplexity", "gemini"]:
                cfg = PROVIDERS[name]
                if cfg["key_env"] and os.environ.get(cfg["key_env"]):
                    provider = name
                    break
            else:
                provider = "ollama"
                endpoint_override = OLLAMA_LOCAL
    else:
        endpoint_override = None

    if provider not in PROVIDERS:
        raise ValueError(f"Unknown provider '{provider}'. Options: {list(PROVIDERS.keys())}")

    cfg = PROVIDERS[provider]
    final_model = model or os.environ.get("COGNEE_LLM_MODEL", cfg["model"])
    api_key = _resolve_key(cfg)

    if provider == "ollama":
        endpoint = endpoint_override or OLLAMA_LOCAL
        cognee.config.set_llm_endpoint(endpoint)
    elif cfg["endpoint"]:
        cognee.config.set_llm_endpoint(cfg["endpoint"])

    cognee.config.set_llm_provider(cfg["provider"])
    cognee.config.set_llm_model(final_model)
    if api_key:
        cognee.config.set_llm_api_key(api_key)

    cognee.config.set_embedding_provider(EMBEDDING_PROVIDER)
    cognee.config.set_embedding_model(EMBEDDING_MODEL)
    cognee.config.set_embedding_dimensions(EMBEDDING_DIMENSIONS)

    data_root = os.environ.get("COGNEE_DATA_ROOT", os.path.expanduser("~/.cognee/data"))
    cognee.config.data_root_directory(data_root)

    if verbose:
        masked_key = (api_key[:8] + "..." + api_key[-4:]) if api_key and len(api_key) > 12 else (api_key or "none")
        print(f"Cognee {cognee.__version__} ready")
        print(f"  Provider:  {provider}")
        print(f"  Model:     {final_model}")
        print(f"  API Key:   {masked_key}")
        print(f"  Embedding: {EMBEDDING_PROVIDER} / {EMBEDDING_MODEL}")
        print(f"  Data root: {data_root}")
        print()

    return {"provider": provider, "model": final_model, "version": cognee.__version__}


def switch(provider, model=None):
    """Switch provider on the fly without restarting."""
    return init(provider=provider, model=model, verbose=True)


def list_providers():
    """Show all available providers and whether their API key is set."""
    print("Available Cognee LLM providers:")
    print()
    for name, cfg in PROVIDERS.items():
        if cfg["key_env"]:
            key = os.environ.get(cfg["key_env"]) or ""
            has_key = bool(key)
            status = "KEY SET" if has_key else "needs " + cfg["key_env"]
        else:
            status = "no key needed"
        print(f"  {name:12s}  {cfg['model']:45s}  {status}")
    print()


if __name__ == "__main__":
    list_providers()
    print()
    info = init()
    print(f"Active: {info['provider']} / {info['model']}")
