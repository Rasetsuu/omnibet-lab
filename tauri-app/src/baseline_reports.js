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
  const panel = document.getElementById('baseline-reports-summary');
  if (!panel) return;
  const s = payload.summary || {};
  panel.innerHTML = `
    <h3>v331-v340 Baseline training reports</h3>
    <p class="warn">Reports are blocked until walk-forward evaluator gates pass. No recommendations or profitability claims.</p>
    <table>
      <tr><th>Metric</th><th>Value</th></tr>
      <tr><td>Baseline rows</td><td>${esc(s.baseline_rows)}</td></tr>
      <tr><td>Ready for training</td><td>${esc(s.ready_for_training)}</td></tr>
      <tr><td>Report status</td><td>${esc(s.report_status)}</td></tr>
      <tr><td>Trust status</td><td>${esc(s.trust_status)}</td></tr>
      <tr><td>Blocked reason</td><td>${esc(s.blocked_reason)}</td></tr>
    </table>
  `;
}

function renderRows(payload) {
  const panel = document.getElementById('baseline-reports-rows');
  if (!panel) return;
  const rows = payload.baseline_rows || [];
  panel.innerHTML = `
    <h3>Baseline rows</h3>
    <table>
      <tr><th>Baseline</th><th>Family</th><th>Type</th><th>Status</th><th>Rows</th><th>Eligible</th><th>Blocked reason</th></tr>
      ${rows.map(row => `
        <tr>
          <td>${esc(row.baseline_id)}</td>
          <td>${esc(row.market_family)}</td>
          <td>${esc(row.baseline_type)}</td>
          <td>${esc(row.status)}</td>
          <td>${esc(row.sample_rows)}</td>
          <td>${esc(row.eligible_rows)}</td>
          <td>${esc(row.blocked_reason)}</td>
        </tr>
      `).join('')}
    </table>
  `;
}

function renderArtifact(payload) {
  const panel = document.getElementById('baseline-reports-artifact');
  if (!panel) return;
  const a = payload.artifact_manifest || {};
  const n = payload.no_vig_preview || {};
  panel.innerHTML = `
    <h3>Artifact / no-vig preview</h3>
    <table>
      <tr><th>Field</th><th>Value</th></tr>
      <tr><td>Artifact</td><td>${esc(a.artifact_id)}</td></tr>
      <tr><td>Status</td><td>${esc(a.status)}</td></tr>
      <tr><td>Training rows</td><td>${esc(a.training_rows)}</td></tr>
      <tr><td>Source report</td><td>${esc(a.source_report)}</td></tr>
      <tr><td>No-vig probabilities</td><td>${esc((n.no_vig_probabilities || []).join(', '))}</td></tr>
      <tr><td>Preview only</td><td>${esc(n.preview_only)}</td></tr>
    </table>
  `;
}

function renderTrust(payload) {
  const panel = document.getElementById('baseline-reports-trust');
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
  const panel = document.getElementById('baseline-reports-next');
  if (!panel) return;
  panel.innerHTML = `<h3>Next</h3><p>${esc(payload.next_phase)}</p>`;
}

export function renderBaselineReportsStatus(payload) {
  renderSummary(payload);
  renderRows(payload);
  renderArtifact(payload);
  renderTrust(payload);
  renderNext(payload);
  return payload;
}

export async function loadAndRenderBaselineReportsStatus(path = 'tauri-app/src/baseline-reports.sample.json') {
  const payload = await loadJson(path);
  return renderBaselineReportsStatus(payload);
}
