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

function table(panelId, title, headers, rows, renderRow) {
  const panel = document.getElementById(panelId);
  if (!panel) return;
  panel.innerHTML = `
    <h3>${esc(title)}</h3>
    <table>
      <tr>${headers.map(h => `<th>${esc(h)}</th>`).join('')}</tr>
      ${rows.map(renderRow).join('')}
    </table>
  `;
}

function renderSummary(payload) {
  const panel = document.getElementById('dataset-materialization-summary');
  if (!panel) return;
  const s = payload.summary || {};
  panel.innerHTML = `
    <h3>v301-v310 Local dataset materialization preview</h3>
    <p class="warn">PAPER_ONLY local preview. No live calls, no credentials, no real training claim.</p>
    <table>
      <tr><th>Metric</th><th>Value</th></tr>
      <tr><td>Manifests</td><td>${esc(s.manifest_rows)}</td></tr>
      <tr><td>Fixture rows</td><td>${esc(s.fixture_rows)}</td></tr>
      <tr><td>Odds rows</td><td>${esc(s.odds_rows)}</td></tr>
      <tr><td>Settlement rows</td><td>${esc(s.settlement_rows)}</td></tr>
      <tr><td>CLV rows</td><td>${esc(s.clv_rows)}</td></tr>
      <tr><td>Candidates</td><td>${esc(s.candidate_rows)}</td></tr>
      <tr><td>Ready for training</td><td>${esc(s.ready_for_training)}</td></tr>
      <tr><td>Market terminal reload ready</td><td>${esc(s.market_terminal_reload_ready)}</td></tr>
    </table>
  `;
}

function renderManifests(payload) {
  table('dataset-materialization-manifests', 'Local source manifests', ['Source', 'Provider', 'Role', 'Codec', 'Rows', 'Readiness'], payload.manifest_rows || [], row => `
    <tr><td>${esc(row.source_id)}</td><td>${esc(row.provider)}</td><td>${esc(row.source_role)}</td><td>${esc(row.expected_codec)}</td><td>${esc(row.row_count)}</td><td>${esc(row.readiness)}</td></tr>
  `);
}

function renderFixtures(payload) {
  table('dataset-materialization-fixtures', 'Fixture/result import preview', ['Fixture', 'Competition', 'Status', 'State'], payload.fixture_rows || [], row => `
    <tr><td>${esc(row.label)}<br/><span class="muted">${esc(row.canonical_fixture_id)}</span></td><td>${esc(row.competition_id)}</td><td>${esc(row.result_status)}</td><td>${esc(row.candidate_state)}</td></tr>
  `);
}

function renderOdds(payload) {
  table('dataset-materialization-odds', 'Odds import preview', ['Fixture', 'Market', 'Selection', 'Price', 'State'], payload.odds_rows || [], row => `
    <tr><td>${esc(row.canonical_fixture_id)}</td><td>${esc(row.market_key)}</td><td>${esc(row.selection_key)}</td><td>${esc(row.price_decimal)}</td><td>${esc(row.candidate_state)}</td></tr>
  `);
}

function renderSettlements(payload) {
  table('dataset-materialization-settlements', 'Settlement label preview', ['Fixture', 'Market', 'Selection', 'Final', 'State'], payload.settlement_rows || [], row => `
    <tr><td>${esc(row.canonical_fixture_id)}</td><td>${esc(row.market_key)}</td><td>${esc(row.selection_key)}</td><td>${esc(row.final_result)}</td><td>${esc(row.candidate_state)}</td></tr>
  `);
}

function renderClv(payload) {
  table('dataset-materialization-clv', 'Closing-odds / CLV preview', ['Fixture', 'Market', 'Selection', 'Paper price', 'Closing price', 'CLV', 'State'], payload.clv_rows || [], row => `
    <tr><td>${esc(row.canonical_fixture_id)}</td><td>${esc(row.market_key)}</td><td>${esc(row.selection_key)}</td><td>${esc(row.paper_price_decimal)}</td><td>${esc(row.closing_price_decimal)}</td><td>${esc(row.paper_clv)}</td><td>${esc(row.candidate_state)}</td></tr>
  `);
}

function renderCandidates(payload) {
  table('dataset-materialization-candidates', 'Bronze / Silver / Gold candidate preview', ['Candidate', 'Type', 'Layer', 'Codec', 'Rows', 'State', 'Blockers'], payload.candidate_rows || [], row => `
    <tr><td>${esc(row.candidate_id)}</td><td>${esc(row.candidate_type)}</td><td>${esc(row.target_layer)}</td><td>${esc(row.codec_target)}</td><td>${esc(row.row_count)}</td><td>${esc(row.promotion_state)}</td><td>${list(row.blockers)}</td></tr>
  `);
}

function renderReadiness(payload) {
  const panel = document.getElementById('dataset-materialization-readiness');
  if (!panel) return;
  const r = payload.coverage_readiness || {};
  panel.innerHTML = `
    <h3>Coverage readiness</h3>
    <p class="warn">Training remains blocked until thresholds pass.</p>
    <table>
      <tr><th>Field</th><th>Value</th></tr>
      <tr><td>Ready for training</td><td>${esc(r.ready_for_training)}</td></tr>
      <tr><td>Ready rows</td><td>${esc(r.ready_rows)} / ${esc(r.minimum_ready_rows)}</td></tr>
      <tr><td>Odds coverage</td><td>${esc(r.odds_coverage_ratio)}</td></tr>
      <tr><td>Settlement coverage</td><td>${esc(r.settlement_coverage_ratio)}</td></tr>
      <tr><td>Closing odds coverage</td><td>${esc(r.closing_odds_coverage_ratio)}</td></tr>
    </table>
    <h4>Blockers</h4>
    ${list(r.blockers)}
  `;
}

export function renderDatasetMaterialization(payload) {
  renderSummary(payload);
  renderManifests(payload);
  renderFixtures(payload);
  renderOdds(payload);
  renderSettlements(payload);
  renderClv(payload);
  renderCandidates(payload);
  renderReadiness(payload);
  return payload;
}

export async function loadAndRenderDatasetMaterialization(path = 'tauri-app/src/dataset-materialization.sample.json') {
  const payload = await loadJson(path);
  return renderDatasetMaterialization(payload);
}

export async function generateAndRenderDatasetMaterialization() {
  // Browser/Tauri preview fallback: actual local generator is python_lab/local_dataset_materialization_preview.py.
  return loadAndRenderDatasetMaterialization('tauri-app/src/dataset-materialization.sample.json');
}
