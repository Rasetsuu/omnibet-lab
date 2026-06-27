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
  const panel = document.getElementById('walk-forward-summary');
  if (!panel) return;
  const s = payload.summary || {};
  panel.innerHTML = `
    <h3>v321-v330 Walk-forward evaluator</h3>
    <p class="warn">No-leak local evaluator. Training remains blocked until safety and coverage gates pass.</p>
    <table>
      <tr><th>Metric</th><th>Value</th></tr>
      <tr><td>Windows</td><td>${esc(s.windows)}</td></tr>
      <tr><td>Total rows</td><td>${esc(s.total_rows)}</td></tr>
      <tr><td>Eligible rows</td><td>${esc(s.eligible_rows)}</td></tr>
      <tr><td>Blocked rows</td><td>${esc(s.blocked_rows)}</td></tr>
      <tr><td>Ready for training</td><td>${esc(s.ready_for_training)}</td></tr>
      <tr><td>Status</td><td>${esc(s.status)}</td></tr>
    </table>
  `;
}

function renderWindows(payload) {
  const panel = document.getElementById('walk-forward-windows');
  if (!panel) return;
  const rows = payload.window_rows || [];
  panel.innerHTML = `
    <h3>Evaluation windows</h3>
    <table>
      <tr><th>Window</th><th>Family</th><th>Prediction time</th><th>Rows</th><th>Status</th><th>Blockers</th></tr>
      ${rows.map(row => `
        <tr>
          <td>${esc(row.window_id)}</td>
          <td>${esc(row.market_family)}</td>
          <td>${esc(row.prediction_time)}</td>
          <td>${esc(row.rows)}</td>
          <td>${esc(row.coverage_status)}</td>
          <td>${list(row.blockers)}</td>
        </tr>
      `).join('')}
    </table>
  `;
}

function renderSafety(payload) {
  const panel = document.getElementById('walk-forward-safety');
  if (!panel) return;
  const rows = payload.safety_rows || [];
  panel.innerHTML = `
    <h3>Safety checks</h3>
    <table>
      <tr><th>Check</th><th>Status</th><th>Failures</th></tr>
      ${rows.map(row => `
        <tr>
          <td>${esc(row.check)}</td>
          <td>${esc(row.status)}</td>
          <td>${esc(row.failures)}</td>
        </tr>
      `).join('')}
    </table>
  `;
}

function renderCoverage(payload) {
  const panel = document.getElementById('walk-forward-coverage');
  if (!panel) return;
  const r = payload.coverage_readiness || {};
  panel.innerHTML = `
    <h3>Coverage readiness</h3>
    <table>
      <tr><th>Field</th><th>Actual</th><th>Minimum</th></tr>
      <tr><td>Eval rows</td><td>${esc(r.actual_eval_rows)}</td><td>${esc(r.minimum_eval_rows)}</td></tr>
      <tr><td>Settlement coverage</td><td>${esc(r.actual_settlement_coverage_ratio)}</td><td>${esc(r.minimum_settlement_coverage_ratio)}</td></tr>
      <tr><td>Closing odds coverage</td><td>${esc(r.actual_closing_odds_coverage_ratio)}</td><td>${esc(r.minimum_closing_odds_coverage_ratio)}</td></tr>
      <tr><td>Min market-family rows</td><td>${esc(r.actual_min_market_family_rows)}</td><td>${esc(r.minimum_market_family_rows)}</td></tr>
    </table>
    <h4>Blockers</h4>
    ${list(r.blockers)}
  `;
}

function renderNext(payload) {
  const panel = document.getElementById('walk-forward-next');
  if (!panel) return;
  panel.innerHTML = `
    <h3>Next</h3>
    <p>${esc(payload.next_phase)}</p>
  `;
}

export function renderWalkForwardEvaluatorStatus(payload) {
  renderSummary(payload);
  renderWindows(payload);
  renderSafety(payload);
  renderCoverage(payload);
  renderNext(payload);
  return payload;
}

export async function loadAndRenderWalkForwardEvaluatorStatus(path = 'tauri-app/src/walk-forward-evaluator.sample.json') {
  const payload = await loadJson(path);
  return renderWalkForwardEvaluatorStatus(payload);
}
