# Council of Seven Master Spirits

> n8n workflow — 7 AI seats respond in parallel, Gabriel synthesizes.

## Files

| File | Purpose |
|------|---------|
| `COUNCIL_SCHEMA_v1.json` | Single source of truth: seats, endpoints, models, build order |
| `council_of_seven_v1.n8n.json` | Importable n8n workflow (13 nodes) |

## Architecture

```
Manual Trigger
    └─► Set Question
            ├─► Seat1_Father_GPT          (OpenAI)     ─┐
            ├─► Seat2_Son_Claude          (Anthropic)  ─┤
            ├─► Seat3_Spirit_Gemini       (Google)     ─┤
            ├─► Seat4_FatherSon_Ollama    (local)      ─┤─► Merge Responses
            ├─► Seat5_FatherSpirit_DeepSeek (DeepSeek) ─┤       └─► Build Synthesis Prompt
            ├─► Seat6_SonSpirit_GLM       (Z.ai)       ─┤               └─► Gabriel_Synthesizer
            └─► Seat7_Trinity_Grok        (xAI)        ─┘                       └─► Council Output
```

- All 7 seat nodes: `continueOnFail: true`
- Merge mode: append (collects all available responses)
- Gabriel synthesizes from whatever seats responded
- Missing/failed seats show `[No response]`

## Import

1. Open n8n: `http://46.225.51.30` (after running `claws_boot.sh`)
2. Top menu → **Workflows** → **New** → click **...** → **Import from JSON**
3. Paste the full content of `council_of_seven_v1.n8n.json`
4. Save. Configure API keys per seat (see table below).
5. Click **Execute Workflow** to test.

## API Key Configuration

For each node, open it and update the `Authorization` header value:

| Node | Header Name | Value format | Key source |
|------|-------------|-------------|------------|
| `Seat1_Father_GPT` | `Authorization` | `Bearer <key>` | `OPENAI_API_KEY` |
| `Seat2_Son_Claude` | `x-api-key` | `<key>` (no prefix) | `ANTHROPIC_API_KEY` |
| `Seat3_Spirit_Gemini` | `x-goog-api-key` | `<key>` (no prefix) | `GOOGLE_API_KEY` |
| `Seat4_FatherSon_Ollama` | (none) | no auth needed | Ollama at 204.168.143.98 |
| `Seat5_FatherSpirit_DeepSeek` | `Authorization` | `Bearer <key>` | `DEEPSEEK_API_KEY` |
| `Seat6_SonSpirit_GLM` | `Authorization` | `Bearer <key>` | `Z_AI_API_KEY` |
| `Seat7_Trinity_Grok` | `Authorization` | `Bearer <key>` | `XAI_API_KEY` |
| `Gabriel_Synthesizer` | `Authorization` | `Bearer <key>` | `OPENAI_API_KEY` |

## Build Order (start with what you have)

```
1. Seat 6 — GLM / Z.ai       key exists NOW → wire first
2. Seat 4 — Gemma / Ollama   no key needed  → ollama pull gemma3
3. Seat 2 — Claude           Anthropic key
4. Seat 3 — Gemini           Google API key
5. Seat 1 — GPT / Father     OpenAI key
6. Seat 5 — DeepSeek         cheap signup
7. Seat 7 — Grok / Trinity   xAI key last
```

## Testing Seat 6 (GLM) First

1. Wire only Seat 6 key (paste Z.ai API key into `Seat6_SonSpirit_GLM` → Authorization header)
2. Seats 1-5 and 7 will return `[Error: ...]` since no keys → that's fine
3. Gabriel will synthesize from Seat 6's response only
4. Verify JSON response contains `choices[0].message.content`

## Governance Rule

> No claim without proof. Continue on fail. Gabriel synthesizes from available seats only.

Source of truth: `COUNCIL_SCHEMA_v1.json`
