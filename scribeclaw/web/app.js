// ScribeClaw Command Centre — vanilla ES module, zero build step.
// Talks to the same FastAPI that serves this page:
//   GET  /health                       runtime probe
//   GET  /api/transcripts              list stems + meta
//   GET  /api/transcripts/<stem>       detail
//   GET  /api/evidence?limit=...       recent evidence records
//   GET  /api/file?path=...            proxy a file under DATA_ROOT
//   POST /tasks                        invoke a handler
const $  = (sel, root = document) => root.querySelector(sel);
const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));

const state = {
  selectedStem: null,
  allHandlers: [],
  detail: null,
};

async function j(url, opts = {}) {
  const r = await fetch(url, opts);
  if (!r.ok) throw new Error(`${r.status} ${url}`);
  return r.json();
}

function setPill(probe, ok, labelBase) {
  const el = document.querySelector(`[data-probe="${probe}"]`);
  if (!el) return;
  el.classList.remove("ok", "bad", "warn");
  el.classList.add(ok === true ? "ok" : ok === false ? "bad" : "warn");
  el.textContent = labelBase + " " + (ok === true ? "✓" : ok === false ? "✗" : "—");
}

async function refreshHealth() {
  try {
    const h = await j("/health");
    const statusEl = document.querySelector('[data-probe="status"]');
    statusEl.classList.remove("bad", "warn");
    statusEl.classList.add("ok");
    statusEl.textContent = `v${h.version} · ${h.status}`;
    setPill("ffmpeg_on_path", h.ffmpeg_on_path, "ffmpeg");
    setPill("faster_whisper_installed", h.faster_whisper_installed, "whisper");
    setPill("httpx_installed", h.httpx_installed, "httpx");
    setPill("google_libs_installed", h.google_libs_installed, "youtube libs");
    setPill("assemblyai_key_set", h.assemblyai_key_set, "AAI key");
    setPill("youtube_token_present", h.youtube_token_present, "YT token");
    state.allHandlers = (h.allowed_handlers || []).slice().sort();
    populateHandlers();
  } catch (e) {
    const statusEl = document.querySelector('[data-probe="status"]');
    statusEl.classList.remove("ok", "warn");
    statusEl.classList.add("bad");
    statusEl.textContent = "unreachable";
  }
}

function populateHandlers() {
  const sel = $("#handler-select");
  if (sel.options.length === state.allHandlers.length && sel.dataset.ready) return;
  sel.innerHTML = "";
  for (const h of state.allHandlers) {
    const o = document.createElement("option");
    o.value = h; o.textContent = h;
    sel.appendChild(o);
  }
  sel.dataset.ready = "1";
  sel.addEventListener("change", () => {
    const skel = suggestedPayload(sel.value);
    $("#handler-payload").value = JSON.stringify(skel, null, 2);
  });
  // seed
  if (state.allHandlers.length) {
    sel.value = state.allHandlers[0];
    sel.dispatchEvent(new Event("change"));
  }
}

function suggestedPayload(handler) {
  const stem = state.selectedStem || "<stem>";
  const base = {
    smoke_test: {},
    media_edit: { input: "<video>.mp4", loudnorm: true },
    audio_extract: { input: "<video>.edited.mp4" },
    transcribe_ro: { input: "<video>.edited.wav", model: "large-v3" },
    transcribe_assemblyai: { input: "<video>.edited.wav" },
    import_assemblyai_transcript: { transcript_id: "<id>", stem: stem },
    bulk_import_assemblyai_romanian: { max_transcripts: 50 },
    postprocess_transcript: { stem },
    resegment_phrase_cues: { stem },
    thumbnail_generate: { input: "<video>.edited.mp4", stem, timestamp: "00:00:05" },
    youtube_metadata: { stem, channel_footer: "" },
    youtube_upload: { stem, privacy_status: "private" },
  };
  return base[handler] ?? {};
}

async function refreshTranscripts() {
  const list = $("#transcript-list");
  list.innerHTML = "<li style='color:var(--fg-dim)'>loading…</li>";
  try {
    const data = await j("/api/transcripts");
    list.innerHTML = "";
    if (!data.transcripts.length) {
      list.innerHTML = "<li style='color:var(--fg-dim)'>no transcripts yet</li>";
      return;
    }
    for (const row of data.transcripts) {
      const li = document.createElement("li");
      li.textContent = row.stem;
      li.title = `${row.segments} segments · ${row.has_bundle ? "bundled" : "no bundle"}`;
      if (row.stem === state.selectedStem) li.classList.add("active");
      li.addEventListener("click", () => selectStem(row.stem));
      list.appendChild(li);
    }
  } catch (e) {
    list.innerHTML = `<li style='color:var(--bad)'>${e.message}</li>`;
  }
}

async function selectStem(stem) {
  state.selectedStem = stem;
  $$(".sidebar li").forEach(li => li.classList.toggle("active", li.textContent === stem));
  const detail = $("#detail");
  detail.innerHTML = `<div class="empty">loading ${stem}…</div>`;
  try {
    const d = await j("/api/transcripts/" + encodeURIComponent(stem));
    state.detail = d;
    renderDetail(d);
  } catch (e) {
    detail.innerHTML = `<div class="empty" style='color:var(--bad)'>${e.message}</div>`;
  }
}

function renderDetail(d) {
  const chips = [];
  if (d.has_bundle) chips.push(`<span class="chip ok">bundle</span>`);
  if (d.has_thumbnail) chips.push(`<span class="chip ok">thumbnail</span>`);
  if (d.has_cues) chips.push(`<span class="chip ok">phrase cues</span>`);
  if (d.has_upload) chips.push(`<span class="chip ok">uploaded</span>`);
  chips.push(`<span class="chip">${d.segments} segments</span>`);
  if (d.language) chips.push(`<span class="chip">lang: ${d.language}</span>`);
  if (d.duration_sec != null) chips.push(`<span class="chip">${Math.round(d.duration_sec)}s</span>`);

  const preview = (d.segments_preview || []).map(s =>
    `<b>[${fmtTs(s.start)}]</b> ${escape(s.text)}`
  ).join("<br>");

  const bundlePre = d.bundle
    ? `<pre>${escape(JSON.stringify({
        title: d.bundle.title_candidates?.[0],
        tags: (d.bundle.tags || []).slice(0, 10),
        chapters: d.bundle.chapters?.length,
      }, null, 2))}</pre>`
    : `<div style="color: var(--fg-dim)">no bundle yet — run youtube_metadata</div>`;

  const thumb = d.has_thumbnail
    ? `<img src="/api/file?path=youtube/${encodeURIComponent(d.stem)}/thumbnail.jpg&v=${Date.now()}" alt="thumbnail">`
    : `<div style="color: var(--fg-dim)">no thumbnail yet — run thumbnail_generate</div>`;

  const upload = d.upload
    ? `<pre>${escape(JSON.stringify({
        video_id: d.upload.video_id,
        url: d.upload.video_url,
        status: d.upload.privacy_status,
      }, null, 2))}</pre>`
    : `<div style="color: var(--fg-dim)">not uploaded</div>`;

  $("#detail").innerHTML = `
    <h2>${escape(d.stem)}</h2>
    <div class="sub">${escape(d.source_file || "")}</div>
    <div class="chips">${chips.join("")}</div>
    <div class="quick-row">
      ${qb("postprocess_transcript", { stem: d.stem })}
      ${qb("resegment_phrase_cues", { stem: d.stem })}
      ${qb("youtube_metadata", { stem: d.stem })}
      ${qb("thumbnail_generate", { input: d.video_hint || `${d.stem}.edited.mp4`, stem: d.stem, timestamp: "00:00:05" })}
      ${qb("youtube_upload", { stem: d.stem, privacy_status: "private" })}
    </div>
    <div class="detail-grid">
      <div class="card"><h3>First segments</h3>${preview || "<i>empty</i>"}</div>
      <div class="card"><h3>Thumbnail</h3>${thumb}</div>
      <div class="card"><h3>Bundle</h3>${bundlePre}</div>
      <div class="card"><h3>Upload result</h3>${upload}</div>
    </div>
  `;
  $$("#detail button[data-handler]").forEach(b => {
    b.addEventListener("click", () => {
      $("#handler-select").value = b.dataset.handler;
      $("#handler-select").dispatchEvent(new Event("change"));
      $("#handler-payload").value = b.dataset.payload;
      $("#handler-payload").scrollIntoView({ behavior: "smooth", block: "center" });
    });
  });
}

function qb(handler, payload) {
  const p = JSON.stringify(payload, null, 2);
  return `<button data-handler="${handler}" data-payload='${p.replace(/'/g, "&#39;")}'>▶ ${handler}</button>`;
}

function fmtTs(sec) {
  sec = Math.max(0, sec || 0);
  const h = Math.floor(sec / 3600);
  const m = Math.floor((sec % 3600) / 60);
  const s = Math.floor(sec % 60);
  return h > 0 ? `${h}:${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`
               : `${m}:${String(s).padStart(2, "0")}`;
}
function escape(s) {
  return String(s ?? "").replace(/[&<>"]/g, c =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
}

async function runHandler() {
  const handler = $("#handler-select").value;
  let payload;
  try { payload = JSON.parse($("#handler-payload").value); }
  catch (e) { $("#handler-result").textContent = "invalid JSON: " + e.message; return; }

  const out = $("#handler-result");
  out.textContent = "running…";
  try {
    const r = await fetch("/tasks", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ handler, payload }),
    });
    const data = await r.json();
    out.textContent = JSON.stringify(data, null, 2);
    // Refresh the sidebar — handler may have created or updated a stem.
    refreshTranscripts();
    refreshEvidence();
    if (state.selectedStem) selectStem(state.selectedStem);
  } catch (e) {
    out.textContent = "error: " + e.message;
  }
}

async function refreshEvidence() {
  try {
    const data = await j("/api/evidence?limit=30");
    const list = $("#evidence-list");
    list.innerHTML = "";
    for (const ev of data.evidence) {
      const li = document.createElement("li");
      const t = new Date(ev.ts_epoch * 1000).toISOString().slice(11, 19);
      li.textContent = `${t} · ${ev.handler}`;
      li.title = ev.result_sha256 || "";
      list.appendChild(li);
    }
  } catch (e) { /* silent */ }
}

$("#run-handler").addEventListener("click", runHandler);
$("#refresh-transcripts").addEventListener("click", refreshTranscripts);

refreshHealth();
refreshTranscripts();
refreshEvidence();
setInterval(refreshHealth, 10000);
setInterval(refreshEvidence, 15000);
