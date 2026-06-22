import { useState } from "react";

const MAX_QUERY_LEN = 4000;

// Sanitized error codes are the ONLY error information the backend returns.
// The UI surfaces the code verbatim plus a short, fixed gloss. No raw
// exception text is ever expected or rendered.
const ERROR_GLOSS = {
  provider_unavailable: "The model provider could not be reached.",
  timeout: "The provider did not respond in time.",
  invalid_response: "The provider returned an unusable response.",
  synthesis_unavailable: "Gabriel could not produce a synthesis.",
};

function glossFor(code) {
  return ERROR_GLOSS[code] || "Unknown sanitized error code.";
}

export default function App() {
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [uiError, setUiError] = useState(null);

  const trimmed = query.trim();
  const canSubmit = trimmed.length > 0 && trimmed.length <= MAX_QUERY_LEN && !loading;

  async function onSubmit(e) {
    e.preventDefault();
    if (!canSubmit) return;

    setLoading(true);
    setResult(null);
    setUiError(null);

    try {
      const res = await fetch("/api/query", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: trimmed }),
      });

      if (!res.ok) {
        setUiError(
          `Backend rejected the request (HTTP ${res.status}). ` +
            "Check that the query is valid and the Phase 2 backend is running on 127.0.0.1:8741."
        );
        return;
      }

      const data = await res.json();
      setResult(data);
    } catch {
      setUiError(
        "Could not reach the backend. Start the Phase 2 backend locally " +
          "(python main.py) so it listens on 127.0.0.1:8741, then retry."
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="app">
      <header className="masthead">
        <h1>OmniQuery</h1>
        <p className="council-line">
          Force-of-Three · Father/GPT · Son/Claude · Spirit/Grok — synthesized by Gabriel
        </p>
        <div className="warning-banner" role="note">
          Phase 3 — LOCAL UI ONLY. Not for deployment or production hosting.
          Talks only to the backend on 127.0.0.1. No secrets are stored or
          handled in the browser.
        </div>
      </header>

      <form className="query-form" onSubmit={onSubmit}>
        <label htmlFor="query">Your query</label>
        <textarea
          id="query"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="What is the nature of truth, beauty, and goodness?"
          rows={4}
          maxLength={MAX_QUERY_LEN}
        />
        <div className="form-row">
          <span className="counter">
            {trimmed.length}/{MAX_QUERY_LEN}
          </span>
          <button type="submit" disabled={!canSubmit}>
            {loading ? "Convening the Council…" : "Ask the Council"}
          </button>
        </div>
      </form>

      {uiError && (
        <div className="ui-error" role="alert">
          {uiError}
        </div>
      )}

      {result && <Results result={result} />}
    </div>
  );
}

function Results({ result }) {
  const seats = Array.isArray(result.seat_responses) ? result.seat_responses : [];
  const synthesisOk = result.synthesis_status === "ok" && result.gabriel_synthesis;

  return (
    <section className="results">
      <div className="synthesis">
        <h2>Gabriel — Synthesis</h2>
        {synthesisOk ? (
          <p className="synthesis-text">{result.gabriel_synthesis}</p>
        ) : (
          <ErrorNote code={result.synthesis_error || "synthesis_unavailable"} />
        )}
      </div>

      <h3 className="seats-heading">
        Force-of-Three — {result.response_count ?? seats.filter((s) => s.status === "ok").length}/
        {seats.length} seats responded
      </h3>

      <div className="seats">
        {seats.map((seat, i) => (
          <SeatCard key={`${seat.seat}-${i}`} seat={seat} />
        ))}
      </div>
    </section>
  );
}

function SeatCard({ seat }) {
  const ok = seat.status === "ok";
  return (
    <article className={`seat ${ok ? "seat-ok" : "seat-error"}`}>
      <header className="seat-head">
        <span className="seat-name">{seat.seat}</span>
        <span className="seat-meta">
          {seat.model} · {seat.provider}
        </span>
      </header>
      {ok ? (
        <p className="seat-text">{seat.response}</p>
      ) : (
        <ErrorNote code={seat.error || "provider_unavailable"} />
      )}
    </article>
  );
}

function ErrorNote({ code }) {
  return (
    <div className="error-note">
      <code className="error-code">{code}</code>
      <span className="error-gloss">{glossFor(code)}</span>
    </div>
  );
}
