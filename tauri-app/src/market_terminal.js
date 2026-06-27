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
  const panel = document.getElementById('market-terminal-summary');
  if (!panel) return;
  const s = payload.summary || {};
  panel.innerHTML = `
    <h3>v291-v300 Market Terminal MVP</h3>
    <p class="warn">PAPER_ONLY offline sample. Inspect/paper-watch only. No real-money recommendation output.</p>
    <table>
      <tr><th>Metric</th><th>Value</th></tr>
      <tr><td>Fixtures</td><td>${esc(s.fixtures)}</td></tr>
      <tr><td>Prediction rows</td><td>${esc(s.prediction_rows)}</td></tr>
      <tr><td>Paper watch rows</td><td>${esc(s.paper_watch_rows)}</td></tr>
      <tr><td>Paper ledger rows</td><td>${esc(s.paper_ledger_rows)}</td></tr>
      <tr><td>Bilet builder enabled</td><td>${esc(s.bilet_builder_enabled)}</td></tr>
      <tr><td>Ready for real predictions</td><td>${esc(s.ready_for_real_predictions)}</td></tr>
    </table>
  `;
}

function renderFixtures(payload) {
  const panel = document.getElementById('market-terminal-fixtures');
  if (!panel) return;
  const fixtures = payload.fixtures || [];
  panel.innerHTML = `
    <h3>Fixture / market selection</h3>
    <table>
      <tr><th>Fixture</th><th>Status</th><th>Freshness</th><th>Markets</th><th>Trust</th><th>Inspect</th></tr>
      ${fixtures.map((fixture, index) => `
        <tr>
          <td>${esc(fixture.label)}<br/><span class="muted">${esc(fixture.competition)}</span></td>
          <td>${esc(fixture.status)}</td>
          <td>${esc(fixture.source_freshness)}</td>
          <td>${list(fixture.available_markets)}</td>
          <td>${esc(fixture.trust_summary)}</td>
          <td><button data-market-terminal-fixture-index="${index}">Details</button></td>
        </tr>
      `).join('')}
    </table>
  `;
  panel.querySelectorAll('[data-market-terminal-fixture-index]').forEach(button => {
    button.addEventListener('click', () => renderSelectedFixture(fixtures[Number(button.dataset.marketTerminalFixtureIndex)], payload));
  });
}

function renderPredictions(payload, fixtureId = null) {
  const panel = document.getElementById('market-terminal-predictions');
  if (!panel) return;
  const rows = (payload.prediction_rows || []).filter(row => !fixtureId || row.canonical_fixture_id === fixtureId);
  panel.innerHTML = `
    <h3>Prediction table</h3>
    <p class="muted">Showing ${esc(rows.length)} row(s). Null model/fair odds mean the model is not validated yet.</p>
    <table>
      <tr><th>Fixture</th><th>Market</th><th>Selection</th><th>Model %</th><th>Fair odds</th><th>Book odds</th><th>No-vig %</th><th>Edge</th><th>Trust</th><th>Action</th></tr>
      ${rows.map(row => `
        <tr>
          <td>${esc(row.canonical_fixture_id)}</td>
          <td>${esc(row.market_key)}</td>
          <td>${esc(row.selection_key)}</td>
          <td>${esc(row.model_probability)}</td>
          <td>${esc(row.fair_odds_decimal)}</td>
          <td>${esc(row.bookmaker_odds_decimal)}</td>
          <td>${esc(row.no_vig_probability)}</td>
          <td>${esc(row.edge_vs_no_vig)}</td>
          <td>${esc(row.trust_status)}<br/>${list(row.blockers)}</td>
          <td>${esc(row.allowed_action)}</td>
        </tr>
      `).join('')}
    </table>
  `;
}

function renderWatchlist(payload) {
  const panel = document.getElementById('market-terminal-watchlist');
  if (!panel) return;
  const rows = payload.paper_watchlist || [];
  panel.innerHTML = `
    <h3>Paper watchlist</h3>
    <table>
      <tr><th>Watch id</th><th>Fixture</th><th>Market</th><th>Selection</th><th>Captured price</th><th>Status</th></tr>
      ${rows.map(row => `
        <tr>
          <td>${esc(row.paper_watch_id)}</td>
          <td>${esc(row.canonical_fixture_id)}</td>
          <td>${esc(row.market_key)}</td>
          <td>${esc(row.selection_key)}</td>
          <td>${esc(row.captured_price_decimal)} @ ${esc(row.captured_at)}</td>
          <td>${esc(row.status)} / ${esc(row.trust_status)}</td>
        </tr>
      `).join('')}
    </table>
  `;
}

function renderLedger(payload) {
  const panel = document.getElementById('market-terminal-ledger');
  if (!panel) return;
  const rows = payload.paper_ledger_preview || [];
  panel.innerHTML = `
    <h3>Paper ledger preview</h3>
    <table>
      <tr><th>Ticket</th><th>Status</th><th>Selections</th><th>Paper stake</th><th>Real stake</th><th>Settlement</th></tr>
      ${rows.map(row => `
        <tr>
          <td>${esc(row.paper_ticket_id)}</td>
          <td>${esc(row.status)}</td>
          <td>${esc(row.selections_count)}</td>
          <td>${esc(row.paper_stake_units)}</td>
          <td>${esc(row.real_stake_allowed)}</td>
          <td>${esc(row.settlement_status)}</td>
        </tr>
      `).join('')}
    </table>
  `;
}

function renderBiletBuilder(payload) {
  const panel = document.getElementById('market-terminal-bilet-builder');
  if (!panel) return;
  const b = payload.bilet_builder_placeholder || {};
  panel.innerHTML = `
    <h3>Bilet Builder placeholder</h3>
    <p class="warn">Disabled until model trust reaches validated_paper. This MVP cannot place bets or recommend stakes.</p>
    <table>
      <tr><th>Field</th><th>Value</th></tr>
      <tr><td>Enabled</td><td>${esc(b.enabled)}</td></tr>
      <tr><td>Disabled reason</td><td>${esc(b.disabled_reason)}</td></tr>
      <tr><td>Minimum trust</td><td>${esc(b.minimum_required_trust_status)}</td></tr>
      <tr><td>Current best status</td><td>${esc(b.current_best_status)}</td></tr>
      <tr><td>Allowed action</td><td>${esc(b.allowed_action)}</td></tr>
    </table>
  `;
}

function renderSelectedFixture(fixture, payload) {
  const panel = document.getElementById('market-terminal-selected');
  if (!panel) return;
  if (!fixture) {
    panel.innerHTML = '<div class="muted">Select a fixture to inspect markets, blockers, and movement preview.</div>';
    return;
  }
  const rows = (payload.prediction_rows || []).filter(row => row.canonical_fixture_id === fixture.canonical_fixture_id);
  panel.innerHTML = `
    <h3>Selected fixture</h3>
    <table>
      <tr><th>Field</th><th>Value</th></tr>
      <tr><td>Fixture</td><td>${esc(fixture.canonical_fixture_id)}</td></tr>
      <tr><td>Label</td><td>${esc(fixture.label)}</td></tr>
      <tr><td>Competition</td><td>${esc(fixture.competition)}</td></tr>
      <tr><td>Status</td><td>${esc(fixture.status)}</td></tr>
      <tr><td>Kickoff</td><td>${esc(fixture.kickoff_time)}</td></tr>
      <tr><td>Freshness</td><td>${esc(fixture.source_freshness)}</td></tr>
      <tr><td>Trust</td><td>${esc(fixture.trust_summary)}</td></tr>
    </table>
    <h4>Movement preview</h4>
    ${rows.map(row => `<p>${esc(row.market_key)} / ${esc(row.selection_key)}: ${esc(row.movement_preview?.movement_status)} (${esc(row.movement_preview?.opening_price_decimal)} → ${esc(row.movement_preview?.current_price_decimal)} → ${esc(row.movement_preview?.closing_price_decimal)})</p>`).join('') || '<p class="muted">No market rows.</p>'}
  `;
  renderPredictions(payload, fixture.canonical_fixture_id);
}

export function renderMarketTerminalMvp(payload) {
  renderSummary(payload);
  renderFixtures(payload);
  renderPredictions(payload);
  renderSelectedFixture(null, payload);
  renderWatchlist(payload);
  renderLedger(payload);
  renderBiletBuilder(payload);
  return payload;
}

export async function loadAndRenderMarketTerminalMvp(path = 'tauri-app/src/market-terminal.sample.json') {
  const payload = await loadJson(path);
  return renderMarketTerminalMvp(payload);
}
