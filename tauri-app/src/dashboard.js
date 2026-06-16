import { loadDashboardReport } from './api.js';

export function esc(value) {
  return String(value ?? '').replace(/[&<>'"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' }[c]));
}

export function table(rows, cols) {
  if (!rows || rows.length === 0) return '<div class="muted">No rows.</div>';
  const head = '<tr>' + cols.map(c => `<th>${esc(c.label)}</th>`).join('') + '</tr>';
  const body = rows.map(r => '<tr>' + cols.map(c => `<td>${esc(r[c.key])}</td>`).join('') + '</tr>').join('');
  return `<table>${head}${body}</table>`;
}

function setHtml(id, html) {
  const el = document.getElementById(id);
  if (el) el.innerHTML = html;
}

function unwrapDashboardPayload(payload) {
  if (payload && payload.dashboard_json) return payload.dashboard_json;
  return payload;
}

export function renderDashboard(data) {
  const sections = data.sections || {};
  const events = sections.events || [];
  const event = events[0] || {};

  const eventHtml = `
    <h3>Event list</h3>
    <p><b>${esc(event.home_team_name)} vs ${esc(event.away_team_name)}</b></p>
    <p>${esc(event.competition)} · ${esc(event.commence_time)}</p>
    <p>${(event.provider_links || []).map(x => `<span class="pill">${esc(x.provider_id)}</span>`).join('')}</p>
  `;
  setHtml('dashboard-events', eventHtml);
  setHtml('page-events', eventHtml + table(events, [
    { key: 'canonical_event_id', label: 'Canonical event' },
    { key: 'home_team_name', label: 'Home' },
    { key: 'away_team_name', label: 'Away' },
    { key: 'commence_time', label: 'Commence' }
  ]));

  const marketHtml = '<h3>Market snapshots</h3>' + table(sections.market_snapshots, [
    { key: 'bookmaker', label: 'Bookmaker' },
    { key: 'raw_market_name', label: 'Market' },
    { key: 'raw_selection_name', label: 'Selection' },
    { key: 'mapped_market_id', label: 'Mapped' },
    { key: 'decimal_odds', label: 'Odds' }
  ]);
  setHtml('dashboard-markets', marketHtml);
  setHtml('page-markets', marketHtml);

  const unknownHtml = '<h3>Unknown market queue</h3>' + table(sections.unknown_market_queue, [
    { key: 'raw_market_name', label: 'Market' },
    { key: 'raw_selection_name', label: 'Selection' },
    { key: 'bookmaker', label: 'Bookmaker' }
  ]);
  setHtml('dashboard-unknowns', unknownHtml);
  setHtml('page-unknowns', unknownHtml);

  const featureHtml = '<h3>Feature snapshot preview</h3>' + table((sections.feature_snapshot_preview || {}).counts, [
    { key: 'snapshot_stage', label: 'Stage' },
    { key: 'rows', label: 'Rows' },
    { key: 'model_eligible_rows', label: 'Model eligible' }
  ]);
  setHtml('dashboard-features', featureHtml);
  setHtml('page-features', featureHtml + table((sections.feature_snapshot_preview || {}).rows, [
    { key: 'snapshot_stage', label: 'Stage' },
    { key: 'mapped_market_id', label: 'Market' },
    { key: 'raw_selection_name', label: 'Selection' },
    { key: 'implied_probability', label: 'Implied' },
    { key: 'model_eligible', label: 'Eligible' }
  ]));

  const settlementHtml = '<h3>Settlement report</h3>' + table((sections.settlement_report || {}).counts, [
    { key: 'settlement_status', label: 'Status' },
    { key: 'settlement_result', label: 'Result' },
    { key: 'rows', label: 'Rows' }
  ]);
  setHtml('dashboard-settlement', settlementHtml);
  setHtml('page-settlement', settlementHtml + table((sections.settlement_report || {}).rows, [
    { key: 'mapped_market_id', label: 'Market' },
    { key: 'raw_selection_name', label: 'Selection' },
    { key: 'settlement_result', label: 'Result' },
    { key: 'reason', label: 'Reason' }
  ]));

  const accounting = sections.result_accounting_report || {};
  const accountingHtml = '<h3>Result accounting report</h3>' + table(accounting.counts, [
    { key: 'settlement_result', label: 'Result' },
    { key: 'rows', label: 'Rows' },
    { key: 'paper_units', label: 'Units' }
  ]) + `<p class="muted">${esc(accounting.note || '')}</p>`;
  setHtml('dashboard-accounting', accountingHtml);
  setHtml('page-accounting', accountingHtml + table(accounting.rows, [
    { key: 'mapped_market_id', label: 'Market' },
    { key: 'raw_selection_name', label: 'Selection' },
    { key: 'decimal_odds', label: 'Odds' },
    { key: 'settlement_result', label: 'Result' },
    { key: 'paper_unit_result', label: 'Units' }
  ]));
}

export async function loadAndRenderDashboard(pathHint = null) {
  const payload = await loadDashboardReport(pathHint);
  const data = unwrapDashboardPayload(payload);
  renderDashboard(data);
  return { ok: true, loaded: data.version, bridge_mode: payload?.mode || 'browser_fallback', sections: Object.keys(data.sections || {}) };
}
