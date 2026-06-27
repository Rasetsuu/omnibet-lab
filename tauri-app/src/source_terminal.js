import { loadSourceTerminalReport, runLocalWorkflow } from './api.js';

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

function ensurePanel(id, fallbackText = 'Load source terminal first.') {
  let panel = document.getElementById(id);
  if (panel) return panel;
  const page = document.getElementById('source-terminal');
  if (!page) return null;
  panel = document.createElement('div');
  panel.id = id;
  panel.className = 'card';
  panel.innerHTML = `<div class="muted">${esc(fallbackText)}</div>`;
  page.appendChild(panel);
  return panel;
}

function asArray(value) {
  return Array.isArray(value) ? value : [];
}

function uniqueValues(rows, key) {
  return [...new Set(rows.map(row => row?.[key]).filter(value => value !== undefined && value !== null && value !== ''))].sort();
}

function filterOptions(values) {
  return ['all', ...values].map(value => `<option value="${esc(value)}">${esc(value)}</option>`).join('');
}

function sampleRows(report) {
  const explicitRows = asArray(report?.normalized_preview_rows);
  if (explicitRows.length) return explicitRows;
  return Object.entries(report?.normalized_row_counts || {}).map(([rowType, count], idx) => ({
    row_id: `count:${rowType}`,
    provider: 'unknown_provider',
    row_type: rowType,
    readiness: Number(count) > 0 ? 'count_only' : 'empty',
    blocker_reason: Number(count) > 0 ? 'details_not_in_report' : 'no_rows',
    next_action: Number(count) > 0 ? 'regenerate_with_v260_details' : 'inspect_source_inputs',
    sample: { row_type: rowType, count, note: 'Legacy report only contains counts.' },
    _legacy_index: idx
  }));
}

function adapterRows(report) {
  const explicitAdapters = asArray(report?.adapter_health);
  if (explicitAdapters.length) return explicitAdapters;
  return [
    {
      provider: 'all_adapters',
      provider_role: 'source_terminal_summary',
      status: (report?.adapter_ok_count ?? 0) === (report?.adapter_count ?? 0) ? 'ok' : 'blocked',
      credential_status: 'not_displayed',
      normalized_rows: report?.normalized_total_rows ?? 0,
      readiness: report?.readiness?.ready_for_source_panel ? 'source_panel_ready' : 'blocked',
      blocker_reason: asArray(report?.blocker_summary).join(', ') || 'none',
      next_action: 'inspect_generated_report'
    }
  ];
}

function rowMatches(row, filters) {
  return ['provider', 'row_type', 'readiness', 'blocker_reason'].every(key => filters[key] === 'all' || String(row?.[key] ?? '') === filters[key]);
}

function rowSummaryTable(rows) {
  if (!rows.length) return '<p class="muted">No rows match the current filters.</p>';
  return `
    <table>
      <tr><th>Row</th><th>Provider</th><th>Type</th><th>Readiness</th><th>Blocker</th><th>Next action</th><th>Details</th></tr>
      ${rows.map((row, index) => `
        <tr>
          <td>${esc(row.row_id || index + 1)}</td>
          <td>${esc(row.provider)}</td>
          <td>${esc(row.row_type)}</td>
          <td>${esc(row.readiness)}</td>
          <td>${esc(row.blocker_reason || 'none')}</td>
          <td>${esc(row.next_action || 'inspect')}</td>
          <td><button data-source-row-index="${index}">Inspect</button></td>
        </tr>
      `).join('')}
    </table>
  `;
}

function adapterTable(rows) {
  if (!rows.length) return '<p class="muted">No adapter health rows in this report.</p>';
  return `
    <table>
      <tr><th>Provider</th><th>Role</th><th>Status</th><th>Credential</th><th>Rows</th><th>Readiness</th><th>Next action</th></tr>
      ${rows.map(row => `
        <tr>
          <td>${esc(row.provider)}</td>
          <td>${esc(row.provider_role)}</td>
          <td>${esc(row.status)}</td>
          <td>${esc(row.credential_status)}</td>
          <td>${esc(row.normalized_rows)}</td>
          <td>${esc(row.readiness)}</td>
          <td>${esc(row.next_action)}</td>
        </tr>
      `).join('')}
    </table>
  `;
}

function detailBlock(row) {
  if (!row) return '<p class="muted">Select a row to inspect its sample payload and next action.</p>';
  return `
    <h4>Selected row detail</h4>
    <table>
      <tr><th>Field</th><th>Value</th></tr>
      <tr><td>Row id</td><td>${esc(row.row_id)}</td></tr>
      <tr><td>Provider</td><td>${esc(row.provider)}</td></tr>
      <tr><td>Type</td><td>${esc(row.row_type)}</td></tr>
      <tr><td>Readiness</td><td>${esc(row.readiness)}</td></tr>
      <tr><td>Blocker</td><td>${esc(row.blocker_reason || 'none')}</td></tr>
      <tr><td>Next action</td><td>${esc(row.next_action || 'inspect')}</td></tr>
    </table>
    <pre>${esc(JSON.stringify(row.sample || {}, null, 2))}</pre>
  `;
}

function renderFilteredSourceRows(report) {
  const filtersPanel = ensurePanel('source-terminal-filters');
  const rowPanel = ensurePanel('source-terminal-row-details');
  if (!filtersPanel || !rowPanel) return;

  const rows = sampleRows(report);
  const filters = {
    provider: document.getElementById('source-terminal-provider-filter')?.value || 'all',
    row_type: document.getElementById('source-terminal-row-type-filter')?.value || 'all',
    readiness: document.getElementById('source-terminal-readiness-filter')?.value || 'all',
    blocker_reason: document.getElementById('source-terminal-blocker-filter')?.value || 'all'
  };
  const filteredRows = rows.filter(row => rowMatches(row, filters));

  rowPanel.innerHTML = `
    <h3>Row sample details</h3>
    <p class="muted">Showing ${esc(filteredRows.length)} / ${esc(rows.length)} rows. Rows remain quarantined/read-only until later promotion gates.</p>
    ${rowSummaryTable(filteredRows)}
    <div id="source-terminal-selected-row" class="card">${detailBlock(filteredRows[0])}</div>
  `;

  rowPanel.querySelectorAll('[data-source-row-index]').forEach(button => {
    button.addEventListener('click', () => {
      const selected = filteredRows[Number(button.dataset.sourceRowIndex)];
      const detail = document.getElementById('source-terminal-selected-row');
      if (detail) detail.innerHTML = detailBlock(selected);
    });
  });
}

function renderSourceTerminal(payload) {
  const report = payload?.source_terminal_json || payload;
  const summary = document.getElementById('source-terminal-summary');
  const readiness = document.getElementById('source-terminal-readiness');
  const actions = document.getElementById('source-terminal-actions');
  const blockers = document.getElementById('source-terminal-blockers');
  const filtersPanel = ensurePanel('source-terminal-filters');
  if (!summary || !readiness || !actions || !blockers) return payload;

  const counts = report?.normalized_row_counts || {};
  const sourceRows = sampleRows(report);
  summary.innerHTML = `
    <h3>Source terminal summary</h3>
    <p class="muted">${esc(payload?.note || 'Loaded source terminal report.')}</p>
    <table>
      <tr><th>Metric</th><th>Value</th></tr>
      <tr><td>Path</td><td>${esc(payload?.path || 'bundled sample')}</td></tr>
      <tr><td>Adapters OK</td><td>${esc(report?.adapter_ok_count)} / ${esc(report?.adapter_count)}</td></tr>
      <tr><td>Normalized rows</td><td>${esc(report?.normalized_total_rows)}</td></tr>
      <tr><td>Inspectable samples</td><td>${esc(sourceRows.length)}</td></tr>
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
    <h4>Adapter health</h4>
    ${adapterTable(adapterRows(report))}
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

  if (filtersPanel) {
    filtersPanel.innerHTML = `
      <h3>Row filters</h3>
      <p class="muted">Filter normalized preview rows before inspecting samples. Filters are local UI-only.</p>
      <div class="grid">
        <label>Provider<br/><select id="source-terminal-provider-filter">${filterOptions(uniqueValues(sourceRows, 'provider'))}</select></label>
        <label>Row type<br/><select id="source-terminal-row-type-filter">${filterOptions(uniqueValues(sourceRows, 'row_type'))}</select></label>
        <label>Readiness<br/><select id="source-terminal-readiness-filter">${filterOptions(uniqueValues(sourceRows, 'readiness'))}</select></label>
        <label>Blocker<br/><select id="source-terminal-blocker-filter">${filterOptions(uniqueValues(sourceRows, 'blocker_reason'))}</select></label>
      </div>
    `;
    filtersPanel.querySelectorAll('select').forEach(select => {
      select.addEventListener('change', () => renderFilteredSourceRows(report));
    });
    renderFilteredSourceRows(report);
  }
  return payload;
}

export async function loadAndRenderSourceTerminal(pathHint = null) {
  const payload = await loadSourceTerminalReport(pathHint);
  return renderSourceTerminal(payload);
}

export async function generateAndRenderSourceTerminal() {
  const run = await runLocalWorkflow('generate_source_terminal_report');
  if (!run?.ok) return run;
  const loaded = await loadAndRenderSourceTerminal(null);
  return { ok: true, workflow: run, refreshed_report: loaded, note: 'Generated local source terminal report and refreshed the source view.' };
}
