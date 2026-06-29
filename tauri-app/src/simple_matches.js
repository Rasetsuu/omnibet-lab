import { predictSelectedUpcomingFixture } from './upcoming.js';

function esc(value) {
  return String(value ?? '').replace(/[&<>"]/g, ch => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[ch]));
}

async function loadJson(path) {
  const response = await fetch(path);
  if (!response.ok) throw new Error(`failed to load ${path}: ${response.status}`);
  return response.json();
}

function showPage(id) {
  document.querySelectorAll('.page').forEach(page => {
    page.classList.toggle('active-page', page.id === id);
  });
  document.querySelectorAll('.nav-button').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.page === id);
  });
}

function compactNormalMode() {
  document.body.classList.add('normal-matches-mode');
  document.querySelectorAll('.topbar-actions').forEach(el => {
    el.style.display = 'none';
  });
  document.querySelectorAll('.output-panel').forEach(el => {
    el.style.display = 'none';
  });
  document.querySelectorAll('.nav-button').forEach(btn => {
    const page = btn.dataset.page;
    const keep = page === 'matches' || page === 'upcoming' || page === 'settings';
    btn.style.display = keep ? '' : 'none';
  });
}

function ensureMatchesPage() {
  const nav = document.querySelector('.nav');
  if (nav && !document.querySelector('[data-page="matches"]')) {
    const button = document.createElement('button');
    button.className = 'nav-button';
    button.dataset.page = 'matches';
    button.textContent = 'Matches';
    nav.insertBefore(button, nav.firstChild);
    button.addEventListener('click', () => showPage('matches'));
  }

  const main = document.querySelector('.main-panel');
  if (main && !document.getElementById('matches')) {
    const section = document.createElement('section');
    section.id = 'matches';
    section.className = 'page';
    section.dataset.pagePanel = 'matches';
    section.innerHTML = `
      <div id="matches-hero" class="card"></div>
      <div id="matches-list" class="grid"></div>
      <div id="matches-selected" class="card"></div>
      <div id="matches-paper-actions" class="card"></div>
      <div id="matches-result" class="card"></div>
    `;
    const firstPage = document.querySelector('.page');
    if (firstPage) main.insertBefore(section, firstPage);
    else main.appendChild(section);
  }
}

function normalizeFixtures(payload) {
  const rows = Array.isArray(payload) ? payload : payload.fixtures || [];
  return rows.map((row, idx) => ({
    fixture_id: row.fixture_id || row.id || `match:${idx}`,
    competition_name: row.competition_name || row.competition_id || row.league || 'Football',
    round: row.round || '',
    kickoff_utc: row.kickoff_utc || row.kickoff || row.date || '',
    kickoff_label: row.kickoff_label || row.kickoff_utc || row.kickoff || row.date || '',
    home_name: row.home_name || row.home || row.home_team || '',
    away_name: row.away_name || row.away || row.away_team || '',
    status: row.status || 'scheduled',
    source: row.source || 'local',
  }));
}

function selectFixture(fixture) {
  window.__omnibetSelectedUpcomingFixture = fixture;
  const home = document.getElementById('home');
  const away = document.getElementById('away');
  if (home) home.value = fixture.home_name;
  if (away) away.value = fixture.away_name;
  renderSelected(fixture);
  renderIdleResult(fixture);
}

function renderHero(payload, fixtures) {
  const panel = document.getElementById('matches-hero');
  if (!panel) return;
  panel.innerHTML = `
    <h2>Matches</h2>
    <p class="warn">Paper-only beta. Pick a fixture and run a local paper market-builder preview. Internal training/evaluation stays hidden.</p>
    <p class="muted">Loaded ${esc(fixtures.length)} local fixtures from ${esc(payload.schema || 'local pack')}.</p>
  `;
}

function renderCards(fixtures) {
  const panel = document.getElementById('matches-list');
  if (!panel) return;
  if (!fixtures.length) {
    panel.innerHTML = '<div class="card"><h3>No matches loaded</h3><p class="muted">Local fixture pack is empty.</p></div>';
    return;
  }
  panel.innerHTML = fixtures.map((fixture, idx) => `
    <div class="card match-card">
      <h3>${esc(fixture.home_name)} vs ${esc(fixture.away_name)}</h3>
      <p>${esc(fixture.competition_name)} ${fixture.round ? '· ' + esc(fixture.round) : ''}</p>
      <div class="stat-row"><span>Kickoff</span><strong>${esc(fixture.kickoff_label || fixture.kickoff_utc)}</strong></div>
      <div class="stat-row"><span>Status</span><strong>${esc(fixture.status)}</strong></div>
      <button class="select-match" data-match-index="${idx}">Select</button>
    </div>
  `).join('');

  panel.querySelectorAll('.select-match').forEach(button => {
    button.addEventListener('click', () => {
      const fixture = fixtures[Number(button.dataset.matchIndex)];
      selectFixture(fixture);
    });
  });
}

function renderSelected(fixture) {
  const panel = document.getElementById('matches-selected');
  if (!panel) return;
  if (!fixture) {
    panel.innerHTML = '<h3>Selected match</h3><p class="muted">Select a match first.</p>';
    return;
  }
  panel.innerHTML = `
    <h3>Selected match</h3>
    <div class="stat-row"><span>Home</span><strong>${esc(fixture.home_name)}</strong></div>
    <div class="stat-row"><span>Away</span><strong>${esc(fixture.away_name)}</strong></div>
    <div class="stat-row"><span>Kickoff</span><strong>${esc(fixture.kickoff_label || fixture.kickoff_utc)}</strong></div>
  `;
}

function renderActions() {
  const panel = document.getElementById('matches-paper-actions');
  if (!panel) return;
  panel.innerHTML = `
    <h3>Paper Market Builder</h3>
    <button id="matches-predict-selected">Preview selected</button>
    <button id="matches-predict-all">Preview all paper</button>
    <p class="muted">This is not a betting slip. Training and evaluation stay internal; the GUI only shows paper previews.</p>
  `;
  document.getElementById('matches-predict-selected')?.addEventListener('click', async () => {
    await runPredictSelected();
  });
  document.getElementById('matches-predict-all')?.addEventListener('click', async () => {
    await runPredictAll();
  });
}

function scrollResultIntoView() {
  document.getElementById('matches-result')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function confidenceLabel(modelTrust) {
  const trust = Number(modelTrust);
  if (!Number.isFinite(trust)) return 'LOW preview';
  if (trust >= 0.65) return 'HIGH preview';
  if (trust >= 0.4) return 'MEDIUM preview';
  return 'LOW preview';
}

function scoreBandsFor(side) {
  if (side === 'away') return ['0-1', '1-2', '1-1 draw risk'];
  return ['1-0', '2-1', '1-1 draw risk'];
}

function marketBuilderSummary(snapshot) {
  const prediction = snapshot?.prediction || {};
  const fixture = snapshot?.fixture || {};
  const homeTeam = prediction.home_team || fixture.home_name || '';
  const awayTeam = prediction.away_team || fixture.away_name || '';
  const rawLean = prediction.paper_lean || prediction.lean || prediction.predicted_team || prediction.home_team || homeTeam;
  const paperLean = rawLean || homeTeam || 'No lean';
  const side = paperLean === awayTeam ? 'away' : 'home';
  const opponent = side === 'away' ? homeTeam : awayTeam;
  const modelTrust = prediction.model_trust ?? prediction.trust ?? 0.25;
  const confidence = confidenceLabel(modelTrust);
  const doubleChance = side === 'away' ? `${awayTeam} or Draw` : `${homeTeam} or Draw`;
  return {
    fixture,
    homeTeam,
    awayTeam,
    paperLean,
    opponent,
    modelTrust,
    confidence,
    decisionMode: prediction.decision_mode || prediction.mode || 'PAPER_ONLY',
    mainLine: `${paperLean} lean`,
    doubleChance,
    goals: [
      { label: 'Over 0.5 goals', view: 'Very plausible preview' },
      { label: 'Over 1.5 goals', view: 'Plausible preview' },
      { label: 'Over 2.5 goals', view: 'Uncertain until trained scoring model' },
    ],
    btts: 'Uncertain / needs trained scoring model',
    teamGoals: [
      { label: `${paperLean} 0.5+ team goals`, view: 'Plausible preview' },
      { label: `${opponent || 'Opponent'} 0.5+ team goals`, view: 'Uncertain preview' },
    ],
    scoreBands: scoreBandsFor(side),
    riskFlags: [
      'Untrained fallback preview',
      'No live odds/context yet',
      'No settled World Cup training ingest yet',
      'Paper-only, not advice',
    ],
  };
}

function builderRow(label, value) {
  return `<div class="stat-row"><span>${esc(label)}</span><strong>${esc(value)}</strong></div>`;
}

function renderList(items) {
  return `<ul>${items.map(item => `<li>${esc(item)}</li>`).join('')}</ul>`;
}

function renderPredictionCard(snapshot) {
  const s = marketBuilderSummary(snapshot);
  return `
    <div class="card prediction-card">
      <h3>${esc(s.homeTeam)} vs ${esc(s.awayTeam)}</h3>
      <div class="card market-builder-main">
        <h2>Paper lean: ${esc(s.paperLean)}</h2>
        ${builderRow('Confidence', s.confidence)}
        ${builderRow('Mode', s.decisionMode)}
        ${builderRow('Model trust', s.modelTrust)}
      </div>
      <div class="grid">
        <div class="card">
          <h3>Main lines</h3>
          ${builderRow('Result preview', s.mainLine)}
          ${builderRow('Double chance style', s.doubleChance)}
          ${builderRow('GG / BTTS', s.btts)}
        </div>
        <div class="card">
          <h3>Goals preview</h3>
          ${s.goals.map(row => builderRow(row.label, row.view)).join('')}
        </div>
        <div class="card">
          <h3>Team goals</h3>
          ${s.teamGoals.map(row => builderRow(row.label, row.view)).join('')}
        </div>
        <div class="card">
          <h3>Score-band candidates</h3>
          ${renderList(s.scoreBands)}
        </div>
      </div>
      <div class="card">
        <h3>Risk flags</h3>
        ${renderList(s.riskFlags)}
      </div>
      <p class="warn">PAPER_ONLY market-builder preview. Not betting advice, not staking advice, not proof of edge.</p>
      <details>
        <summary>Raw snapshot</summary>
        <pre>${esc(JSON.stringify(snapshot, null, 2))}</pre>
      </details>
    </div>
  `;
}

function renderIdleResult(fixture) {
  const result = document.getElementById('matches-result');
  if (!result) return;
  if (!fixture) {
    result.innerHTML = '<h3>Paper Market Builder</h3><p class="muted">Select a match, then press Preview selected.</p>';
    return;
  }
  result.innerHTML = `<h3>Paper Market Builder</h3><p class="muted">Ready to preview ${esc(fixture.home_name)} vs ${esc(fixture.away_name)}.</p>`;
}

async function runPredictSelected() {
  const result = document.getElementById('matches-result');
  try {
    if (result) result.innerHTML = '<h3>Paper Market Builder</h3><p class="muted">Building paper market preview...</p>';
    scrollResultIntoView();
    const snapshot = await predictSelectedUpcomingFixture();
    if (result) {
      result.innerHTML = `<h3>Paper Market Builder Preview</h3>${renderPredictionCard(snapshot)}`;
      scrollResultIntoView();
    }
  } catch (err) {
    if (result) result.innerHTML = `<h3>Paper Market Builder</h3><p class="warn">${esc(err)}</p>`;
    scrollResultIntoView();
  }
}

async function runPredictAll() {
  const result = document.getElementById('matches-result');
  const fixtures = window.__omnibetUpcomingFixtures || [];
  if (!fixtures.length) {
    if (result) result.innerHTML = '<h3>Preview all paper</h3><p class="warn">No fixtures loaded.</p>';
    scrollResultIntoView();
    return;
  }
  const snapshots = [];
  if (result) result.innerHTML = `<h3>Preview all paper</h3><p class="muted">Building ${esc(fixtures.length)} paper market previews...</p>`;
  scrollResultIntoView();
  for (const fixture of fixtures) {
    selectFixture(fixture);
    const snapshot = await predictSelectedUpcomingFixture();
    snapshots.push(snapshot);
  }
  window.__omnibetLastForecastBatch = snapshots;
  if (result) {
    result.innerHTML = `<h3>Paper Market Builder Batch</h3>${snapshots.map(renderPredictionCard).join('')}`;
    scrollResultIntoView();
  }
}

export function renderSimpleMatches(payload) {
  ensureMatchesPage();
  compactNormalMode();
  const fixtures = normalizeFixtures(payload);
  window.__omnibetUpcomingFixtures = fixtures;
  renderHero(payload, fixtures);
  renderCards(fixtures);
  renderSelected(null);
  renderActions();
  renderIdleResult(null);
  showPage('matches');
  return fixtures;
}

export async function loadAndRenderSimpleMatches(path = 'tauri-app/src/world-cup-fixtures.local.json') {
  let payload;
  try {
    payload = await loadJson(path);
  } catch (_err) {
    payload = await loadJson('world-cup-fixtures.local.json');
  }
  return renderSimpleMatches(payload);
}
