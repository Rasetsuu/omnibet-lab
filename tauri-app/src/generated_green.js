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
  return `<table><tr>${headers.map(h => `<th>${esc(h)}</th>`).join('')}</tr>${rows.map(row => `<tr>${cells.map(fn => `<td>${esc(fn(row))}</td>`).join('')}</tr>`).join('')}</table>`;
}

function renderSummary(payload) {
  const panel = document.getElementById('generated-green-summary');
  if (!panel) return;
  const s = payload.summary || {};
  panel.innerHTML = `
    <h3>v371-v380 Generated green report</h3>
    <p class="warn">Generated local mini-pack path. Still sample_only; no validated_paper claim and no recommendations.</p>
    <table>
      <tr><th>Field</th><th>Value</th></tr>
      <tr><td>Status</td><td>${esc(payload.status)}</td></tr>
      <tr><td>Manifest verified</td><td>${esc(payload.source_manifest_verified)}</td></tr>
      <tr><td>Generated fallback used</td><td>${esc(payload.generated_fallback_used || false)}</td></tr>
      <tr><td>Fixtures loaded</td><td>${esc(s.fixtures_loaded)}</td></tr>
      <tr><td>Odds rows loaded</td><td>${esc(s.odds_rows_loaded)}</td></tr>
      <tr><td>Settlement rows loaded</td><td>${esc(s.settlement_rows_loaded)}</td></tr>
      <tr><td>Prediction rows generated</td><td>${esc(s.prediction_rows_generated)}</td></tr>
      <tr><td>Trust</td><td>${esc(s.trust_status)}</td></tr>
      <tr><td>Validated paper</td><td>${esc(s.validated_paper)}</td></tr>
    </table>
  `;
}

function renderSources(payload) {
  const panel = document.getElementById('generated-green-sources');
  if (!panel) return;
  const storage = payload.storage_manifest || {};
  panel.innerHTML = `
    <h3>Storage / source manifest</h3>
    <table>
      <tr><th>Field</th><th>Value</th></tr>
      <tr><td>Preferred codec</td><td>${esc(storage.preferred_output_codec)}</td></tr>
      <tr><td>Fallback codec</td><td>${esc(storage.fallback_output_codec)}</td></tr>
      <tr><td>Rows</td><td>${esc(storage.row_count)}</td></tr>
      <tr><td>SHA256</td><td>${esc(storage.content_sha256)}</td></tr>
      <tr><td>Credential values</td><td>${esc(storage.credential_values_present)}</td></tr>
    </table>
  `;
}

function renderWalkForward(payload) {
  const panel = document.getElementById('generated-green-walk-forward');
  if (!panel) return;
  const row = payload.walk_forward_report || {};
  panel.innerHTML = `<h3>Walk-forward</h3><table><tr><th>Field</th><th>Value</th></tr><tr><td>Status</td><td>${esc(row.status)}</td></tr><tr><td>Random split</td><td>${esc(row.random_split_used)}</td></tr><tr><td>Prediction checks</td><td>${esc(row.prediction_time_checks)}</td></tr><tr><td>Settlement checks</td><td>${esc(row.settlement_label_checks)}</td></tr></table>`;
}

function renderBaseline(payload) {
  const panel = document.getElementById('generated-green-baseline');
  if (!panel) return;
  const report = payload.baseline_report || {};
  panel.innerHTML = `<h3>Baseline metrics</h3><p>Status: ${esc(report.status)}</p>${table(report.metric_summary || [], ['Family', 'Log loss', 'Brier', 'Status'], [r => r.market_family, r => r.log_loss, r => r.brier_score, r => r.status])}`;
}

function renderCalibration(payload) {
  const panel = document.getElementById('generated-green-calibration');
  if (!panel) return;
  const report = payload.calibration_report || {};
  panel.innerHTML = `<h3>Calibration</h3><p>Status: ${esc(report.status)}</p>${table(report.bins || [], ['Family', 'Avg model', 'Empirical', 'Gap'], [r => r.market_family, r => r.avg_model_probability, r => r.empirical_hit_rate, r => r.calibration_gap])}`;
}

function renderStorage(payload) {
  const panel = document.getElementById('generated-green-storage');
  if (!panel) return;
  panel.innerHTML = `<h3>Paper CLV</h3>${table(payload.paper_clv_summary || [], ['Family', 'Avg CLV', 'Positive ratio'], [r => r.market_family, r => r.average_clv_decimal, r => r.positive_clv_ratio])}`;
}

function renderTrust(payload) {
  const panel = document.getElementById('generated-green-trust');
  if (!panel) return;
  const gate = payload.trust_gate || {};
  panel.innerHTML = `
    <h3>Trust gate</h3>
    <table>
      <tr><th>Field</th><th>Value</th></tr>
      <tr><td>Status</td><td>${esc(gate.status)}</td></tr>
      <tr><td>Validated paper</td><td>${esc(gate.validated_paper)}</td></tr>
      <tr><td>Terminal prediction allowed</td><td>${esc(gate.terminal_prediction_allowed)}</td></tr>
      <tr><td>Bilet builder allowed</td><td>${esc(gate.bilet_builder_allowed)}</td></tr>
    </table>
  `;
}

export function renderGeneratedGreenStatus(payload) {
  renderSummary(payload);
  renderSources(payload);
  renderWalkForward(payload);
  renderBaseline(payload);
  renderCalibration(payload);
  renderStorage(payload);
  renderTrust(payload);
  return payload;
}

export async function loadAndRenderGeneratedGreenStatus(path = 'tauri-app/src/generated-green-sample.generated.json') {
  const payload = await loadJsonWithFallback(path, 'tauri-app/src/generated-green-sample.sample.json');
  return renderGeneratedGreenStatus(payload);
}
