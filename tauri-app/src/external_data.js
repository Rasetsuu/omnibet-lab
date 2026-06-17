import { renderUpcomingFixtures } from './upcoming.js';

function esc(value) {
  return String(value ?? '').replace(/[&<>"]/g, ch => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[ch]));
}

async function loadJson(path) {
  const response = await fetch(path);
  if (!response.ok) throw new Error(`failed to load ${path}: ${response.status}`);
  return response.json();
}

export function mapExternalFixtureCacheToUpcoming(cache) {
  const rows = cache?.rows || [];
  return rows.map((row, idx) => ({
    fixture_id: row.external_id || `external:${idx}`,
    competition_id: row.competition || '',
    competition_name: row.league_name || row.competition || '',
    kickoff_utc: row.kickoff || '',
    home_name: row.home || '',
    away_name: row.away || '',
    status: row.status || 'scheduled',
    source: cache.connector_id || 'external_cache',
  }));
}

function renderCapabilities(payload) {
  const rows = payload.capabilities || [];
  if (!rows.length) return '<div class="muted">No capabilities.</div>';
  return rows.map(row => `
    <div class="stat-row"><span>${esc(row.label)}</span><strong>${esc(row.mode)}</strong></div>
  `).join('');
}

function renderConnectors(payload) {
  const rows = payload.connectors || [];
  if (!rows.length) return '<div class="muted">No entries.</div>';
  return rows.map(row => `
    <div class="card">
      <h3>${esc(row.label)}</h3>
      <div class="stat-row"><span>Status</span><strong>${esc(row.status)}</strong></div>
      <div class="stat-row"><span>Manual only</span><strong>${row.manual_refresh_only ? 'yes' : 'no'}</strong></div>
      <div class="stat-row"><span>Secret value required</span><strong>${row.requires_secret_value ? 'yes' : 'no'}</strong></div>
    </div>
  `).join('');
}

function renderCache(payload) {
  const cache = payload.fixture_cache_sample || {};
  const rows = cache.rows || [];
  return `
    <h3>v167 cached fixture sample</h3>
    <div class="stat-row"><span>Connector</span><strong>${esc(cache.connector_id)}</strong></div>
    <div class="stat-row"><span>Rows</span><strong>${esc(rows.length)}</strong></div>
    <ul>${rows.map(row => `<li>${esc(row.home)} vs ${esc(row.away)} · ${esc(row.kickoff)}</li>`).join('')}</ul>
  `;
}

export function renderExternalData(payload) {
  const cap = document.getElementById('external-data-capabilities');
  const con = document.getElementById('external-data-connectors');
  const cache = document.getElementById('external-data-cache');
  if (cap) cap.innerHTML = `<h3>v165 Capabilities</h3>${renderCapabilities(payload)}`;
  if (con) con.innerHTML = `<h3>v166 Contracts</h3>${renderConnectors(payload)}`;
  if (cache) cache.innerHTML = renderCache(payload);
  window.__omnibetExternalDataPayload = payload;
  return payload;
}

export async function loadAndRenderExternalData(path = 'tauri-app/src/external-data.sample.json') {
  const payload = await loadJson(path);
  return renderExternalData(payload);
}

export function importExternalFixtureCacheToUpcoming() {
  const payload = window.__omnibetExternalDataPayload;
  if (!payload) throw new Error('Load external data sample first.');
  const fixtures = mapExternalFixtureCacheToUpcoming(payload.fixture_cache_sample || {});
  window.__omnibetUpcomingFixtures = fixtures;
  renderUpcomingFixtures(fixtures);
  const pageButton = document.querySelector('.nav-button[data-page="upcoming"]');
  if (pageButton) pageButton.click();
  return {
    ok: true,
    schema: 'omnibet.external_cache_to_upcoming.v170',
    fixture_count: fixtures.length,
    fixtures,
    policy: { local_cache_first: true, no_secret_values: true },
  };
}
