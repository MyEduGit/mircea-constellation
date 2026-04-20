# Voice Cloning — Consent Record

## Why this document exists

We clone Dr. Emanoil Geaboc's voice to narrate translated short-form clips
in English, Spanish, and Portuguese. **Voice is biometric data.** Cloning
it without explicit, written, scoped consent is unlawful in many of the
jurisdictions we publish into (EU GDPR Art. 9; California BIPA-style
statutes; Tennessee ELVIS Act; UK DPA 2018; Brazil LGPD), and is
unconditionally against the Terms of Service of every reputable voice
cloning platform (ElevenLabs, PlayHT, Resemble AI).

This file is the **operational record** of consent. Phase 2B's
`scribeclaw/shorts/clone_voice.py` refuses to run without it.

## What "consent" means here (minimum)

A signed document from Dr. Emanoil Geaboc that, at minimum:

1. **Names the cloning provider(s).** Default: ElevenLabs Professional Voice
   Clone. Fallback: self-hosted OpenVoice v2.
2. **Lists the target languages.** Currently: English, Spanish, Portuguese.
3. **Defines the use.** Producing short-form (≤60s) and long-form
   compilation videos for distribution under the channels Dr. Geaboc owns or
   has authorized.
4. **Forbids out-of-scope use** — no impersonation, no political endorsement,
   no statements he has not approved, no commercial endorsement of products,
   no use after consent withdrawal.
5. **Allows withdrawal** at any time. On withdrawal we must (a) stop
   generating, (b) delete the trained voice from all providers, (c) take
   down published clips that depend on the cloned voice within 30 days.
6. **Specifies sample data handling.** Source voice samples (Romanian
   sermons) are stored encrypted at rest and not shared with third parties
   except the cloning provider under their DPA.
7. **Is dated and signed.** Wet signature or a verifiable e-signature
   (DocuSign, Adobe Sign).

## How to record consent

1. Have Dr. Geaboc sign the consent document (template TBD — counsel-
   reviewed; not committed to git).
2. Store the signed PDF in encrypted storage (GPG-encrypted blob, not
   plaintext in git).
3. Update this file with:
   - SHA-256 fingerprint of the signed PDF
   - Date of signature
   - Path to the encrypted store (URL or vault key)
   - Listed languages, providers, expiry (if any)

Until those fields are filled in below, **`scribeclaw/shorts/clone_voice.py`
will refuse to call any cloning API**.

## Current state

```
Status:              PENDING — record not yet on file
Signature SHA-256:   <none>
Signature date:      <none>
Encrypted store:     <none>
Languages authorized: en-US, es-MX, pt-BR  (per project intent)
Providers authorized: <pending signature — default ElevenLabs PVC>
Expiry:              <none — perpetual until withdrawn in writing>
Withdrawal contact:  <Dr. Geaboc's preferred channel>
```

When the signed record arrives, replace the placeholders above. The Phase 2B
loader parses this header block (lines starting with the field names) at
runtime to gate cloning calls.

## Provenance markers in published clips

Per the AI Act / FTC disclosure best practice, **every** non-Romanian clip
that uses cloned audio must:

- Tag the upload metadata (description / hashtags) with `#AIvoice` or the
  platform-specific synthetic-media label (YouTube "altered or synthetic
  content", TikTok "AI-generated", Instagram "AI info").
- Carry a one-line on-screen disclosure on first publication: e.g.
  "Cloned voice — English narration of Dr. Emanoil Geaboc."
- Link in the description to the original Romanian sermon.

These belong in the manifest as a `disclosure` field added in Phase 2B.

## Audit log

Every render that uses cloned audio writes a row to
`scribeclaw/shorts/.audit/clone-renders.jsonl` (gitignored) with:
manifest path, locale, source sermon URL, render timestamp, output path,
provider, voice clone ID, consent fingerprint at time of render. This
gives us a fast answer if Dr. Geaboc ever asks "where did you use my voice?"

## Provider-specific gotchas

- **ElevenLabs PVC** — only the speaker themselves may submit consent
  (verification audio must come from the same voice). We can't sign on
  Dr. Geaboc's behalf. Their workflow accepts our scope language.
- **OpenVoice v2** — runs locally; no third-party DPA. Consent still
  required for the recording itself, but data exposure is limited to our
  own infrastructure. Lower fidelity than PVC.
- **Translated content liability** — we are responsible for what the cloned
  voice says, not just that we cloned it. Translation review by a fluent
  speaker before publication is required (Phase 2B's
  `scribeclaw/shorts/translate.py` flags any clip whose Claude translation
  has not been human-reviewed).
