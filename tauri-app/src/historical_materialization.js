function esc(value) {
  return String(value ?? '').replace(/[&<>"]/g, ch => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[ch]));
}

async function loadJson(path) {
  const response = await fetch(path);
  if (!response.ok) throw new Error(`failed to load ${path}: ${response.status}`);
  return response.json();
}

async function loadJsonWithFallback(primaryPath, fallbackPath) {
  try {
    return await loadJson(primaryPath);
  } catch (err) {
    const payload = await loadJson(fallbackPath);
    payload.generated_fallback_used = true;
    payload.generated_fallback_error = String(err);
    return payload;
  }
}

function table(rows, headers, cells) {
  const safeRows = Array.isArray(rows) ? rows : [];
  return `<table><tr>${headers.map(h => `<th>${esc(h)}</th>`).join('')}</tr>${safeRows.map(row => `<tr>${cells.map(fn => `<td>${esc(fn(row))}</td>`).join('')}</tr>`).join('')}</table>`;
}

function renderSummary(payload) {
  const panel = document.getElementById('historical-materialization-summary');
  if (!panel) return;
  const report = payload.materialization_report || {};
  panel.innerHTML = `
    <h3>Historical materialization</h3>
    <p class="warn">Generated local historical materialization preview. Still sample_only; no training or recommendations.</p>
    <table>
      <tr><th>Field</th><th>Value</th></tr>
      <tr><td>Status</td><td>${esc(payload.status)}</td></tr>
      <tr><td>Run id</td><td>${esc(payload.run_id)}</td></tr>
      <tr><td>Artifact dir</td><td>${esc(payload.artifact_dir)}</td></tr>
      <tr><td>Fallback used</td><td>${esc(payload.generated_fallback_used || false)}</td></tr>
      <tr><td>Source import</td><td>${esc(report.source_import_status)}</td></tr>
      <tr><td>Ready for walk-forward</td><td>${esc(payload.ready_for_walk_forward)}</td></tr>
      <tr><td>Ready for training</td><td>${esc(payload.ready_for_training)}</td></tr>
    </table>
  `;
}

function renderArtifacts(payload) {
  const panel = document.getElementById('historical-materialization-artifacts');
  if (!panel) return;
  const artifacts = payload.generated_artifacts || {};
  const rows = Object.entries(artifacts).map(([name, path]) => ({ name, path }));
  panel.innerHTML = `<h3>Generated artifacts</h3>${table(rows, ['Artifact', 'Path'], [r => r.name, r => r.path])}`;
}

function renderBronze(payload) {
  const panel = document.getElementById('historical-materialization-bronze');
  if (!panel) return;
  const manifest = payload.materialization_manifest || {};
  panel.innerHTML = `<h3>Bronze tables</h3>${table(manifest.bronze_tables || [], ['Table', 'Rows', 'Status', 'Preview'], [r => r.table_id, r => r.row_count, r => r.status, r => r.preview_path])}`;
}

function renderSilver(payload) {
  const panel = document.getElementById('historical-materialization-silver');
  if (!panel) return;
  const manifest = payload.materialization_manifest || {};
  panel.innerHTML = `<h3>Silver tables</h3>${table(manifest.silver_tables || [], ['Table', 'Rows', 'Status', 'Preview'], [r => r.table_id, r => r.row_count, r => r.status, r => r.preview_path])}`;
}

function renderGold(payload) {
  const panel = document.getElementById('historical-materialization-gold');
  if (!panel) return;
  const manifest = payload.materialization_manifest || {};
  const report = payload.materialization_report || {};
  panel.innerHTML = `
    <h3>Gold candidates</h3>
    <p class="muted">Gold candidate rows require odds joined to settlement labels and remain preview-only.</p>
    <p>Gold candidate rows: ${esc(report.gold_candidate_rows)}</p>
    ${table(manifest.gold_tables || [], ['Table', 'Rows', 'Status', 'Preview'], [r => r.table_id, r => r.row_count, r => r.status, r => r.preview_path])}
  `;
}

function renderManifest(payload) {
  const panel = document.getElementById('historical-materialization-manifest');
  if (!panel) return;
  const manifest = payload.materialization_manifest || {};
  panel.innerHTML = `
    <h3>Materialization manifest</h3>
    <table>
      <tr><th>Field</th><th>Value</th></tr>
      <tr><td>Schema</td><td>${esc(manifest.schema)}</td></tr>
      <tr><td>Status</td><td>${esc(manifest.status)}</td></tr>
      <tr><td>Preferred codec</td><td>${esc(manifest.preferred_large_scale_codec)}</td></tr>
      <tr><td>Future codec</td><td>${esc(manifest.future_large_scale_codec)}</td></tr>
      <tr><td>Content hashes present</td><td>${esc(manifest.content_hashes_present)}</td></tr>
      <tr><td>Ready for training</td><td>${esc(manifest.ready_for_training)}</td></tr>
    </table>
  `;
}

function renderTrust(payload) {
  const panel = document.getElementById('historical-materialization-trust');
  if (!panel) return;
  panel.innerHTML = `
    <h3>Trust / locks</h3>
    <table>
      <tr><th>Field</th><th>Value</th></tr>
      <tr><td>Trust status</td><td>${esc(payload.trust_status)}</td></tr>
      <tr><td>Ready for walk-forward</td><td>${esc(payload.ready_for_walk_forward)}</td></tr>
      <tr><td>Ready for training</td><td>${esc(payload.ready_for_training)}</td></tr>
      <tr><td>Credential values present</td><td>${esc(payload.credential_values_present)}</td></tr>
      <tr><td>Recommendation output present</td><td>${esc(payload.recommendation_output_present)}</td></tr>
    </table>
  `;
}

export function renderHistoricalMaterializationStatus(payload) {
  renderSummary(payload);
  renderArtifacts(payload);
  renderBronze(payload);
  renderSilver(payload);
  renderGold(payload);
  renderManifest(payload);
  renderTrust(payload);
  return payload;
}

export async function loadAndRenderHistoricalMaterializationStatus(path = 'reports/generated_historical_materialization_v421_v430_report.json') {
  const payload = await loadJsonWithFallback(path, 'tauri-app/src/historical-materialization.sample.json');
  renderHistoricalMaterializationStatus(payload);
  return payload;
}
