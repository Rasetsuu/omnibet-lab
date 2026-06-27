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
  const panel = document.getElementById('live-source-summary');
  if (!panel) return;
  const s = payload.summary || {};
  panel.innerHTML = `
    <h3>v262-v265 Source-to-context bridge</h3>
    <p class="warn">PAPER_ONLY offline sample. This is source/context readiness, not a betting recommendation.</p>
    <table>
      <tr><th>Metric</th><th>Value</th></tr>
      <tr><td>Live now</td><td>${esc(s.live_now)}</td></tr>
      <tr><td>Upcoming</td><td>${esc(s.upcoming)}</td></tr>
      <tr><td>Odds rows</td><td>${esc(s.odds_rows)}</td></tr>
      <tr><td>Context bundles</td><td>${esc(s.context_bundles)}</td></tr>
      <tr><td>Blocked/partial</td><td>${esc(s.blocked_or_partial)}</td></tr>
      <tr><td>Ready for real predictions</td><td>${esc(s.ready_for_real_predictions)}</td></tr>
    </table>
  `;
}

function renderMatches(payload) {
  const panel = document.getElementById('live-source-matches');
  if (!panel) return;
  const matches = payload.matches || [];
  panel.innerHTML = `
    <h3>Live / upcoming matches</h3>
    <table>
      <tr><th>Match</th><th>Status</th><th>Score</th><th>Odds</th><th>Lineups</th><th>Readiness</th><th>Inspect</th></tr>
      ${matches.map((match, index) => `
        <tr>
          <td>${esc(match.label)}<br/><span class="muted">${esc(match.competition)}</span></td>
          <td>${esc(match.status)} / ${esc(match.phase)} ${match.minute === null ? '' : esc(`${match.minute}'`)}</td>
          <td>${esc(match.score || '-')}</td>
          <td>${esc(match.odds_available)}</td>
          <td>${esc(match.lineup_available)}</td>
          <td>${esc(match.prediction_readiness)}</td>
          <td><button data-live-source-match-index="${index}">Details</button></td>
        </tr>
      `).join('')}
    </table>
  `;
  panel.querySelectorAll('[data-live-source-match-index]').forEach(button => {
    button.addEventListener('click', () => renderSelected(matches[Number(button.dataset.liveSourceMatchIndex)]));
  });
}

function renderOdds(payload) {
  const panel = document.getElementById('live-source-odds');
  if (!panel) return;
  const rows = payload.odds_preview || [];
  panel.innerHTML = `
    <h3>Odds preview</h3>
    <table>
      <tr><th>Fixture</th><th>Market</th><th>Selection</th><th>Price</th><th>In-play</th><th>Freshness</th></tr>
      ${rows.map(row => `
        <tr>
          <td>${esc(row.canonical_fixture_id)}</td>
          <td>${esc(row.market_key)}</td>
          <td>${esc(row.selection_key)}</td>
          <td>${esc(row.price_decimal)}</td>
          <td>${esc(row.is_in_play)}</td>
          <td>${esc(row.freshness_status)}</td>
        </tr>
      `).join('')}
    </table>
  `;
}

function renderContext(payload) {
  const panel = document.getElementById('live-source-context');
  if (!panel) return;
  const rows = payload.context_preview || [];
  panel.innerHTML = `
    <h3>Prediction context preview</h3>
    <table>
      <tr><th>Context</th><th>Fixture</th><th>Readiness</th><th>Allowed actions</th></tr>
      ${rows.map(row => `
        <tr>
          <td>${esc(row.context_id)}</td>
          <td>${esc(row.canonical_fixture_id)}</td>
          <td>${esc(row.prediction_readiness)}</td>
          <td>${list(row.allowed_actions)}</td>
        </tr>
      `).join('')}
    </table>
  `;
}

function renderSelected(match) {
  const panel = document.getElementById('live-source-selected');
  if (!panel) return;
  if (!match) {
    panel.innerHTML = '<div class="muted">Select a live/upcoming match first.</div>';
    return;
  }
  panel.innerHTML = `
    <h3>Selected source context</h3>
    <table>
      <tr><th>Field</th><th>Value</th></tr>
      <tr><td>Fixture</td><td>${esc(match.canonical_fixture_id)}</td></tr>
      <tr><td>Match</td><td>${esc(match.label)}</td></tr>
      <tr><td>Status</td><td>${esc(match.status)}</td></tr>
      <tr><td>Odds available</td><td>${esc(match.odds_available)}</td></tr>
      <tr><td>Lineups</td><td>${esc(match.lineup_available)}</td></tr>
      <tr><td>Events</td><td>${esc(match.event_data_available)}</td></tr>
      <tr><td>Stats</td><td>${esc(match.stats_available)}</td></tr>
      <tr><td>Readiness</td><td>${esc(match.prediction_readiness)}</td></tr>
    </table>
    <h4>Trust blockers</h4>
    ${list(match.trust_blockers)}
  `;
}

export function renderLiveSourceBridge(payload) {
  renderSummary(payload);
  renderMatches(payload);
  renderOdds(payload);
  renderContext(payload);
  renderSelected(null);
  return payload;
}

export async function loadAndRenderLiveSourceBridge(path = 'tauri-app/src/live-source.sample.json') {
  const payload = await loadJson(path);
  return renderLiveSourceBridge(payload);
}
