function esc(value) {
  return String(value ?? '').replace(/[&<>"]/g, ch => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[ch]));
}

async function loadJson(path) {
  const response = await fetch(path);
  if (!response.ok) throw new Error(`failed to load ${path}: ${response.status}`);
  return response.json();
}

function list(items = []) {
  if (!items.length) return '<span class="muted">None</span>';
  return `<ul>${items.map(item => `<li>${esc(item)}</li>`).join('')}</ul>`;
}

function renderSummary(payload) {
  const panel = document.getElementById('calibration-clv-summary');
  if (!panel) return;
  const s = payload.summary || {};
  panel.innerHTML = `
    <h3>v341-v350 Calibration / CLV reports</h3>
    <p class="warn">Blocked until walk-forward and baseline report gates pass. No recommendations or profitability claims.</p>
    <table>
      <tr><th>Metric</th><th>Value</th></tr>
      <tr><td>Report status</td><td>${esc(s.report_status)}</td></tr>
      <tr><td>Walk-forward status</td><td>${esc(s.walk_forward_status)}</td></tr>
      <tr><td>Baseline status</td><td>${esc(s.baseline_status)}</td></tr>
      <tr><td>Calibration bins</td><td>${esc(s.calibration_bins)}</td></tr>
      <tr><td>No-vig delta rows</td><td>${esc(s.no_vig_delta_rows)}</td></tr>
      <tr><td>Paper CLV rows</td><td>${esc(s.paper_clv_rows)}</td></tr>
      <tr><td>Trust</td><td>${esc(s.trust_status)}</td></tr>
      <tr><td>Blocked reason</td><td>${esc(s.blocked_reason)}</td></tr>
    </table>
  `;
}

function renderCalibrationBins(payload) {
  const panel = document.getElementById('calibration-clv-bins');
  if (!panel) return;
  const rows = payload.calibration_bins || [];
  panel.innerHTML = `
    <h3>Reliability bins</h3>
    <table>
      <tr><th>Family</th><th>Bin</th><th>Predictions</th><th>Avg model</th><th>Empirical</th><th>Gap</th><th>Status</th></tr>
      ${rows.map(row => `
        <tr>
          <td>${esc(row.market_family)}</td>
          <td>${esc(row.bin_id)}</td>
          <td>${esc(row.predictions)}</td>
          <td>${esc(row.avg_model_probability)}</td>
          <td>${esc(row.empirical_hit_rate)}</td>
          <td>${esc(row.calibration_gap)}</td>
          <td>${esc(row.status)} / ${esc(row.blocked_reason)}</td>
        </tr>
      `).join('')}
    </table>
  `;
}

function renderMetrics(payload) {
  const panel = document.getElementById('calibration-clv-metrics');
  if (!panel) return;
  const rows = payload.metric_summary || [];
  panel.innerHTML = `
    <h3>Brier / log-loss metrics</h3>
    <table>
      <tr><th>Family</th><th>Rows</th><th>Eligible</th><th>Log loss</th><th>Brier</th><th>ECE</th><th>Status</th></tr>
      ${rows.map(row => `
        <tr>
          <td>${esc(row.market_family)}</td>
          <td>${esc(row.sample_rows)}</td>
          <td>${esc(row.eligible_rows)}</td>
          <td>${esc(row.log_loss)}</td>
          <td>${esc(row.brier_score)}</td>
          <td>${esc(row.calibration_ece)}</td>
          <td>${esc(row.status)} / ${esc(row.blocked_reason)}</td>
        </tr>
      `).join('')}
    </table>
  `;
}

function renderNoVig(payload) {
  const panel = document.getElementById('calibration-clv-no-vig');
  if (!panel) return;
  const rows = payload.no_vig_delta_rows || [];
  panel.innerHTML = `
    <h3>No-vig deltas</h3>
    <table>
      <tr><th>Family</th><th>Selection</th><th>Model %</th><th>No-vig %</th><th>Delta</th><th>Status</th></tr>
      ${rows.map(row => `
        <tr>
          <td>${esc(row.market_family)}</td>
          <td>${esc(row.selection_key)}</td>
          <td>${esc(row.model_probability)}</td>
          <td>${esc(row.no_vig_probability)}</td>
          <td>${esc(row.delta_vs_no_vig)}</td>
          <td>${esc(row.status)} / ${esc(row.blocked_reason)}</td>
        </tr>
      `).join('')}
    </table>
  `;
}

function renderPaperClv(payload) {
  const panel = document.getElementById('calibration-clv-paper-clv');
  if (!panel) return;
  const rows = payload.paper_clv_summary || [];
  panel.innerHTML = `
    <h3>Paper CLV</h3>
    <table>
      <tr><th>Family</th><th>Watch rows</th><th>Closing rows</th><th>Avg CLV</th><th>Positive ratio</th><th>Status</th></tr>
      ${rows.map(row => `
        <tr>
          <td>${esc(row.market_family)}</td>
          <td>${esc(row.paper_watch_rows)}</td>
          <td>${esc(row.closing_odds_rows)}</td>
          <td>${esc(row.average_clv_decimal)}</td>
          <td>${esc(row.positive_clv_ratio)}</td>
          <td>${esc(row.status)} / ${esc(row.blocked_reason)}</td>
        </tr>
      `).join('')}
    </table>
  `;
}

function renderTrust(payload) {
  const panel = document.getElementById('calibration-clv-trust');
  if (!panel) return;
  const gate = payload.trust_gate || {};
  panel.innerHTML = `
    <h3>Trust gate</h3>
    <table>
      <tr><th>Field</th><th>Value</th></tr>
      <tr><td>Status</td><td>${esc(gate.status)}</td></tr>
      <tr><td>Terminal prediction allowed</td><td>${esc(gate.terminal_prediction_allowed)}</td></tr>
      <tr><td>Bilet builder allowed</td><td>${esc(gate.bilet_builder_allowed)}</td></tr>
    </table>
    <h4>Requires</h4>
    ${list(gate.requires)}
  `;
}

function renderNext(payload) {
  const panel = document.getElementById('calibration-clv-next');
  if (!panel) return;
  panel.innerHTML = `<h3>Next</h3><p>${esc(payload.next_phase)}</p>`;
}

export function renderCalibrationClvStatus(payload) {
  renderSummary(payload);
  renderCalibrationBins(payload);
  renderMetrics(payload);
  renderNoVig(payload);
  renderPaperClv(payload);
  renderTrust(payload);
  renderNext(payload);
  return payload;
}

export async function loadAndRenderCalibrationClvStatus(path = 'tauri-app/src/calibration-clv.sample.json') {
  const payload = await loadJson(path);
  return renderCalibrationClvStatus(payload);
}
