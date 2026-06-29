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
}

function renderHero(payload, fixtures) {
  const panel = document.getElementById('matches-hero');
  if (!panel) return;
  panel.innerHTML = `
    <h2>Matches</h2>
    <p class="warn">Paper-only beta. Pick a fixture and run a local paper prediction. Internal training/evaluation stays hidden.</p>
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
    <h3>Paper prediction</h3>
    <button id="matches-predict-selected">Predict selected</button>
    <button id="matches-predict-all">Predict all paper</button>
    <p class="muted">Training is not a visible user action. Background model/evaluation status will be added later.</p>
  `;
  document.getElementById('matches-predict-selected')?.addEventListener('click', async () => {
    await runPredictSelected();
  });
  document.getElementById('matches-predict-all')?.addEventListener('click', () => {
    const result = document.getElementById('matches-result');
    if (result) result.innerHTML = '<h3>Predict all paper</h3><p class="muted">Queued placeholder. Next phase wires batch paper predictions.</p>';
  });
}

async function runPredictSelected() {
  const result = document.getElementById('matches-result');
  try {
    if (result) result.innerHTML = '<h3>Prediction</h3><p class="muted">Running local paper prediction...</p>';
    const snapshot = await predictSelectedUpcomingFixture();
    if (result) {
      result.innerHTML = `<h3>Prediction</h3><pre>${esc(JSON.stringify(snapshot, null, 2))}</pre>`;
    }
  } catch (err) {
    if (result) result.innerHTML = `<h3>Prediction</h3><p class="warn">${esc(err)}</p>`;
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
