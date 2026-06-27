function esc(value) {
  return String(value ?? '').replace(/[&<>"]/g, ch => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[ch]));
}

async function loadJson(path) {
  const response = await fetch(path);
  if (!response.ok) throw new Error(`failed to load ${path}: ${response.status}`);
  return response.json();
}

function table(rows, headers, cells) {
  return `<table><tr>${headers.map(h => `<th>${esc(h)}</th>`).join('')}</tr>${rows.map(row => `<tr>${cells.map(fn => `<td>${esc(fn(row))}</td>`).join('')}</tr>`).join('')}</table>`;
}

function renderSummary(payload) {
  const panel = document.getElementById('green-sample-summary');
  if (!panel) return;
  const s = payload.summary || {};
  panel.innerHTML = `
    <h3>v351-v360 Green evaluator sample</h3>
    <p class="warn">This is a tiny green sample only. It is not validated_paper and it does not unlock recommendations.</p>
    <table>
      <tr><th>Field</th><th>Value</th></tr>
      <tr><td>Status</td><td>${esc(s.status)}</td></tr>
      <tr><td>Ready for evaluation</td><td>${esc(s.ready_for_evaluation)}</td></tr>
      <tr><td>Ready for baseline report</td><td>${esc(s.ready_for_baseline_report)}</td></tr>
      <tr><td>Ready for calibration/CLV</td><td>${esc(s.ready_for_calibration_clv_report)}</td></tr>
      <tr><td>Trust</td><td>${esc(s.trust_status)}</td></tr>
      <tr><td>Validated paper</td><td>${esc(s.validated_paper)}</td></tr>
      <tr><td>Terminal prediction allowed</td><td>${esc(s.terminal_prediction_allowed)}</td></tr>
      <tr><td>Bilet builder allowed</td><td>${esc(s.bilet_builder_allowed)}</td></tr>
    </table>
  `;
}

function renderManifests(payload) {
  const panel = document.getElementById('green-sample-manifests');
  if (!panel) return;
  panel.innerHTML = `<h3>Source manifests</h3>${table(payload.source_manifests || [], ['Source', 'Rows', 'SHA256', 'Credentials'], [r => r.source_id, r => r.row_count, r => r.content_sha256, r => r.credential_values_present])}`;
}

function renderFixtures(payload) {
  const panel = document.getElementById('green-sample-fixtures');
  if (!panel) return;
  panel.innerHTML = `<h3>Fixtures</h3>${table(payload.fixtures || [], ['Fixture', 'Result', 'Settled at'], [r => r.canonical_fixture_id, r => r.final_result, r => r.settled_at])}`;
}

function renderPredictions(payload) {
  const panel = document.getElementById('green-sample-predictions');
  if (!panel) return;
  panel.innerHTML = `<h3>Prediction rows</h3>${table(payload.prediction_rows || [], ['Fixture', 'Family', 'Selection', 'Model %', 'No-vig %', 'Outcome'], [r => r.canonical_fixture_id, r => r.market_family, r => r.selection_key, r => r.model_probability, r => r.no_vig_probability, r => r.outcome])}`;
}

function renderMetrics(payload) {
  const panel = document.getElementById('green-sample-metrics');
  if (!panel) return;
  panel.innerHTML = `<h3>Sample metrics</h3>${table(payload.metric_summary || [], ['Family', 'Log loss', 'Brier', 'ECE', 'Status'], [r => r.market_family, r => r.log_loss, r => r.brier_score, r => r.calibration_ece, r => r.status])}`;
}

function renderClv(payload) {
  const panel = document.getElementById('green-sample-clv');
  if (!panel) return;
  panel.innerHTML = `<h3>Paper CLV</h3>${table(payload.paper_clv_summary || [], ['Family', 'Avg CLV', 'Positive ratio', 'Status'], [r => r.market_family, r => r.average_clv_decimal, r => r.positive_clv_ratio, r => r.status])}`;
}

function renderTrust(payload) {
  const panel = document.getElementById('green-sample-trust');
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

export function renderGreenSampleStatus(payload) {
  renderSummary(payload);
  renderManifests(payload);
  renderFixtures(payload);
  renderPredictions(payload);
  renderMetrics(payload);
  renderClv(payload);
  renderTrust(payload);
  return payload;
}

export async function loadAndRenderGreenSampleStatus(path = 'tauri-app/src/green-evaluator-sample.sample.json') {
  const payload = await loadJson(path);
  return renderGreenSampleStatus(payload);
}
