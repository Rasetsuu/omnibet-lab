import { fixtureTeams, invokeCommand } from './api.js';

function esc(value) {
  return String(value ?? '').replace(/[&<>"]/g, ch => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[ch]));
}

async function loadJson(path) {
  const response = await fetch(path);
  if (!response.ok) throw new Error(`failed to load ${path}: ${response.status}`);
  return response.json();
}

export function normalizeUpcomingFixtures(payload) {
  const rows = Array.isArray(payload) ? payload : payload.fixtures || [];
  return rows.map((row, idx) => ({
    fixture_id: row.fixture_id || row.id || `local:${idx}`,
    competition_id: row.competition_id || row.competition || row.league || '',
    competition_name: row.competition_name || row.competition_id || row.league || '',
    kickoff_utc: row.kickoff_utc || row.kickoff || row.date || '',
    home_name: row.home_name || row.home || row.home_team || '',
    away_name: row.away_name || row.away || row.away_team || '',
    status: row.status || 'scheduled',
    source: row.source || 'local',
  }));
}

function renderFixtureCards(fixtures) {
  if (!fixtures.length) return '<div class="muted">No upcoming fixtures loaded.</div>';
  return fixtures.map((fixture, idx) => `
    <div class="card fixture-card" data-fixture-index="${idx}">
      <h3>${esc(fixture.home_name)} vs ${esc(fixture.away_name)}</h3>
      <div class="muted">${esc(fixture.competition_name)} · ${esc(fixture.kickoff_utc)}</div>
      <div class="stat-row"><span>Status</span><strong>${esc(fixture.status)}</strong></div>
      <button class="select-upcoming-fixture" data-fixture-index="${idx}">Use this fixture</button>
    </div>
  `).join('');
}

function setPredictionInputs(fixture) {
  const home = document.getElementById('home');
  const away = document.getElementById('away');
  if (home) home.value = fixture.home_name;
  if (away) away.value = fixture.away_name;
}

export function buildForecastSnapshot(fixture, prediction) {
  return {
    ok: true,
    schema: 'omnibet.forecast_snapshot.v162',
    fixture,
    prediction,
    policy: {
      paper_only: true,
      local_preview: true,
      no_recommendation: true,
    },
  };
}

function renderSelectedFixture(fixture) {
  const panel = document.getElementById('upcoming-selected-fixture');
  if (!panel) return;
  panel.innerHTML = `
    <h3>Selected fixture</h3>
    <div class="stat-row"><span>Home</span><strong>${esc(fixture.home_name)}</strong></div>
    <div class="stat-row"><span>Away</span><strong>${esc(fixture.away_name)}</strong></div>
    <div class="stat-row"><span>Competition</span><strong>${esc(fixture.competition_name)}</strong></div>
    <div class="stat-row"><span>Kickoff</span><strong>${esc(fixture.kickoff_utc)}</strong></div>
  `;
}

function renderSnapshot(snapshot) {
  const panel = document.getElementById('upcoming-forecast-snapshot');
  if (!panel) return;
  panel.innerHTML = `
    <h3>v162 Forecast snapshot</h3>
    <pre>${esc(JSON.stringify(snapshot, null, 2))}</pre>
  `;
}

function downloadJson(obj, filename) {
  const blob = new Blob([JSON.stringify(obj, null, 2)], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

export function renderUpcomingFixtures(fixtures) {
  const panel = document.getElementById('upcoming-fixtures-panel');
  if (!panel) return fixtures;
  panel.innerHTML = renderFixtureCards(fixtures);
  panel.querySelectorAll('.select-upcoming-fixture').forEach(button => {
    button.addEventListener('click', () => {
      const fixture = fixtures[Number(button.dataset.fixtureIndex)];
      window.__omnibetSelectedUpcomingFixture = fixture;
      setPredictionInputs(fixture);
      renderSelectedFixture(fixture);
      const pageButton = document.querySelector('.nav-button[data-page="simple"]');
      if (pageButton) pageButton.click();
    });
  });
  return fixtures;
}

export async function loadAndRenderUpcomingFixtures(path = 'tauri-app/src/upcoming-fixtures.sample.json') {
  const payload = await loadJson(path);
  const fixtures = normalizeUpcomingFixtures(payload);
  window.__omnibetUpcomingFixtures = fixtures;
  return renderUpcomingFixtures(fixtures);
}

export async function predictSelectedUpcomingFixture() {
  const fixture = window.__omnibetSelectedUpcomingFixture || null;
  if (!fixture) throw new Error('Select an upcoming fixture first.');
  setPredictionInputs(fixture);
  const prediction = await invokeCommand('predict_fixture', fixtureTeams());
  const snapshot = buildForecastSnapshot(fixture, prediction);
  window.__omnibetLastForecastSnapshot = snapshot;
  renderSnapshot(snapshot);
  return snapshot;
}

export function exportForecastSnapshot() {
  const snapshot = window.__omnibetLastForecastSnapshot;
  if (!snapshot) throw new Error('Create a forecast snapshot first.');
  downloadJson(snapshot, 'omnibet-forecast-snapshot.json');
  return { ok: true, exported: true, schema: snapshot.schema };
}
