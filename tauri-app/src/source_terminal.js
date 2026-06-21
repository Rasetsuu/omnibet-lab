import { loadSourceTerminalReport } from './api.js';

function esc(value) {
  return String(value ?? '').replace(/[&<>"']/g, ch => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[ch]));
}

function rowsFromCounts(counts = {}) {
  return Object.entries(counts).map(([kind, count]) => `<tr><td>${esc(kind)}</td><td>${esc(count)}</td></tr>`).join('');
}

function list(items = []) {
  if (!items.length) return '<span class="muted">None</span>';
  return `<ul>${items.map(item => `<li>${esc(item)}</li>`).join('')}</ul>`;
}

function renderSourceTerminal(payload) {
  const report = payload?.source_terminal_json || payload;
  const summary = document.getElementById('source-terminal-summary');
  const readiness = document.getElementById('source-terminal-readiness');
  const actions = document.getElementById('source-terminal-actions');
  const blockers = document.getElementById('source-terminal-blockers');
  if (!summary || !readiness || !actions || !blockers) return payload;

  const counts = report?.normalized_row_counts || {};
  summary.innerHTML = `
    <h3>Source terminal summary</h3>
    <p class="muted">${esc(payload?.note || 'Loaded source terminal report.')}</p>
    <table>
      <tr><th>Metric</th><th>Value</th></tr>
      <tr><td>Path</td><td>${esc(payload?.path || 'bundled sample')}</td></tr>
      <tr><td>Adapters OK</td><td>${esc(report?.adapter_ok_count)} / ${esc(report?.adapter_count)}</td></tr>
      <tr><td>Normalized rows</td><td>${esc(report?.normalized_total_rows)}</td></tr>
      <tr><td>Paper only</td><td>${esc(report?.paper_only)}</td></tr>
      <tr><td>Quarantine only</td><td>${esc(report?.quarantine_only)}</td></tr>
    </table>
    <h4>Row counts</h4>
    <table><tr><th>Type</th><th>Rows</th></tr>${rowsFromCounts(counts)}</table>
  `;

  const r = report?.readiness || {};
  readiness.innerHTML = `
    <h3>Readiness badges</h3>
    <table>
      <tr><th>Badge</th><th>Status</th></tr>
      <tr><td>Adapter health</td><td>${esc(r.adapter_health_ok)}</td></tr>
      <tr><td>Normalization preview</td><td>${esc(r.normalization_preview_ok)}</td></tr>
      <tr><td>Source panel</td><td>${esc(r.ready_for_source_panel)}</td></tr>
      <tr><td>Downstream use</td><td>${esc(r.ready_for_downstream_use ?? false)}</td></tr>
      <tr><td>Reason</td><td>${esc(r.reason)}</td></tr>
    </table>
  `;

  actions.innerHTML = `
    <h3>Desktop actions</h3>
    <div class="grid">
      <div><h4>Allowed</h4>${list(report?.allowed_ui_actions || ['inspect_adapters', 'inspect_rows', 'export_report'])}</div>
      <div><h4>Locked</h4>${list(report?.locked_ui_actions || ['provider_call', 'bronze_write', 'evaluation_run', 'model_fit', 'external_execution'])}</div>
    </div>
  `;

  blockers.innerHTML = `
    <h3>Blockers</h3>
    ${list(report?.blocker_summary || [])}
  `;
  return payload;
}

export async function loadAndRenderSourceTerminal(pathHint = null) {
  const payload = await loadSourceTerminalReport(pathHint);
  return renderSourceTerminal(payload);
}
