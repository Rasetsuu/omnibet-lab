function esc(value) {
  return String(value ?? '').replace(/[&<>"]/g, ch => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[ch]));
}

async function loadJson(path) {
  const response = await fetch(path);
  if (!response.ok) throw new Error(`failed to load ${path}: ${response.status}`);
  return response.json();
}

async function loadGeneratedAdapterStatus() {
  try {
    const adapterReport = await loadJson('reports/historical_file_adapter_v451_v460_report.json');
    const normalizedPreview = await loadJson('reports/historical_file_adapter_v451_v460_normalized_preview.json');
    return {
      schema: 'omnibet.historical_file_adapter_desktop_loaded.v461_v470',
      paper_only: true,
      adapter_report: adapterReport,
      normalized_preview: normalizedPreview,
      generated_fallback_used: false,
      ready_for_materialization: adapterReport.ready_for_materialization,
      ready_for_training: false,
      trust_status: adapterReport.trust_status || 'sample_only',
      credential_values_present: false,
      recommendation_output_present: false
    };
  } catch (err) {
    const sample = await loadJson('tauri-app/src/historical-file-adapter.sample.json');
    sample.generated_fallback_used = true;
    sample.generated_fallback_error = String(err);
    return sample;
  }
}

function table(rows, headers, cells) {
  const safeRows = Array.isArray(rows) ? rows : [];
  return `<table><tr>${headers.map(h => `<th>${esc(h)}</th>`).join('')}</tr>${safeRows.map(row => `<tr>${cells.map(fn => `<td>${esc(fn(row))}</td>`).join('')}</tr>`).join('')}</table>`;
}

function renderSummary(payload) {
  const panel = document.getElementById('historical-file-adapter-summary');
  if (!panel) return;
  const report = payload.adapter_report || {};
  panel.innerHTML = `
    <h3>Historical file adapter</h3>
    <p class="warn">Local CSV adapter preview. This validates user-provided historical files but does not train a model.</p>
    <table>
      <tr><th>Field</th><th>Value</th></tr>
      <tr><td>Status</td><td>${esc(report.status)}</td></tr>
      <tr><td>Fallback sample used</td><td>${esc(payload.generated_fallback_used || false)}</td></tr>
      <tr><td>Fixtures</td><td>${esc(report.fixture_rows)}</td></tr>
      <tr><td>Odds</td><td>${esc(report.odds_rows)}</td></tr>
      <tr><td>Settlements</td><td>${esc(report.settlement_rows)}</td></tr>
      <tr><td>Identities</td><td>${esc(report.identity_rows)}</td></tr>
      <tr><td>Ready for materialization</td><td>${esc(report.ready_for_materialization)}</td></tr>
      <tr><td>Ready for training</td><td>${esc(report.ready_for_training)}</td></tr>
    </table>
  `;
}

function renderInputs(payload) {
  const panel = document.getElementById('historical-file-adapter-inputs');
  if (!panel) return;
  panel.innerHTML = `
    <h3>Input files</h3>
    <p class="muted">Current beta path uses local CSV adapter samples. Upload/choose-file UX can plug into this same report shape next.</p>
    <table>
      <tr><th>Kind</th><th>Expected path</th></tr>
      <tr><td>Fixtures</td><td>data/historical/v451_v460/fixtures.adapter.sample.csv</td></tr>
      <tr><td>Odds</td><td>data/historical/v451_v460/odds.adapter.sample.csv</td></tr>
      <tr><td>Settlements</td><td>data/historical/v451_v460/settlements.adapter.sample.csv</td></tr>
      <tr><td>Identity map</td><td>data/historical/v451_v460/identity_map.adapter.sample.csv</td></tr>
    </table>
  `;
}

function renderFixtures(payload) {
  const panel = document.getElementById('historical-file-adapter-fixtures');
  if (!panel) return;
  const preview = payload.normalized_preview || {};
  panel.innerHTML = `<h3>Fixture preview</h3>${table(preview.fixtures || [], ['Fixture', 'Competition', 'Kickoff', 'Home', 'Away', 'Status'], [r => r.fixture_id, r => r.competition, r => r.kickoff_utc, r => r.home_team_raw, r => r.away_team_raw, r => r.result_status])}`;
}

function renderOdds(payload) {
  const panel = document.getElementById('historical-file-adapter-odds');
  if (!panel) return;
  const preview = payload.normalized_preview || {};
  panel.innerHTML = `<h3>Odds preview</h3>${table(preview.odds || [], ['Fixture', 'Market', 'Selection', 'Bookmaker', 'Captured', 'Odds'], [r => r.fixture_id, r => r.market_family, r => r.selection_id, r => r.bookmaker, r => r.captured_at_utc, r => r.decimal_odds])}`;
}

function renderSettlements(payload) {
  const panel = document.getElementById('historical-file-adapter-settlements');
  if (!panel) return;
  const preview = payload.normalized_preview || {};
  panel.innerHTML = `<h3>Settlement preview</h3>${table(preview.settlements || [], ['Fixture', 'Market', 'Selection', 'Result', 'Label available'], [r => r.fixture_id, r => r.market_family, r => r.selection_id, r => r.settlement_result, r => r.label_available_after_utc])}`;
}

function renderIdentities(payload) {
  const panel = document.getElementById('historical-file-adapter-identities');
  if (!panel) return;
  const preview = payload.normalized_preview || {};
  panel.innerHTML = `<h3>Identity preview</h3>${table(preview.identities || [], ['Type', 'Raw', 'Canonical', 'Confidence', 'Review'], [r => r.entity_type, r => r.raw_name, r => r.canonical_name || r.canonical_id, r => r.confidence, r => r.review_status])}`;
}

function renderErrors(payload) {
  const panel = document.getElementById('historical-file-adapter-errors');
  if (!panel) return;
  const report = payload.adapter_report || {};
  const errors = report.validation_errors || [];
  const warnings = report.validation_warnings || [];
  panel.innerHTML = `
    <h3>Validation</h3>
    <p>Errors: ${esc(errors.length)}</p>
    <p>Warnings: ${esc(warnings.length)}</p>
    ${table(errors.map(error => ({ error })), ['Error'], [r => r.error])}
    ${table(warnings.map(warning => ({ warning })), ['Warning'], [r => r.warning])}
  `;
}

function renderTrust(payload) {
  const panel = document.getElementById('historical-file-adapter-trust');
  if (!panel) return;
  const report = payload.adapter_report || {};
  panel.innerHTML = `
    <h3>Trust / locks</h3>
    <table>
      <tr><th>Field</th><th>Value</th></tr>
      <tr><td>Trust status</td><td>${esc(report.trust_status || payload.trust_status)}</td></tr>
      <tr><td>Ready for materialization</td><td>${esc(report.ready_for_materialization)}</td></tr>
      <tr><td>Ready for training</td><td>${esc(report.ready_for_training)}</td></tr>
      <tr><td>Credential values present</td><td>${esc(report.credential_values_present)}</td></tr>
      <tr><td>Recommendation output present</td><td>${esc(report.recommendation_output_present)}</td></tr>
    </table>
  `;
}

export function renderHistoricalFileAdapterStatus(payload) {
  renderSummary(payload);
  renderInputs(payload);
  renderFixtures(payload);
  renderOdds(payload);
  renderSettlements(payload);
  renderIdentities(payload);
  renderErrors(payload);
  renderTrust(payload);
  return payload;
}

export async function loadAndRenderHistoricalFileAdapterStatus() {
  const payload = await loadGeneratedAdapterStatus();
  renderHistoricalFileAdapterStatus(payload);
  return payload;
}
