import { predictSelectedUpcomingFixture } from './upcoming.js';

const DEFAULT_FEATURE_COUNT_STATUS = {
  source: 'static fallback',
  completedRowText: '3 / 200 required for v1',
  readinessText: 'Needs more rows',
  rowStatus: 'locked',
  readinessStatus: 'locked',
  realModelText: 'Locked until enough settled rows',
  realModelStatus: 'locked',
  notes: ['Status only. No training/import controls are exposed in the normal match screen.'],
};

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
      <div id="matches-data-status" class="card"></div>
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
    <p class="warn">Paper-only beta. Pick a fixture and preview a broad football market catalog. Internal training/evaluation stays hidden.</p>
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

function renderDataStatus(status = DEFAULT_FEATURE_COUNT_STATUS) {
  const panel = document.getElementById('matches-data-status');
  if (!panel) return;
  const notes = Array.isArray(status.notes) && status.notes.length ? status.notes : DEFAULT_FEATURE_COUNT_STATUS.notes;
  panel.innerHTML = `
    <h3>Data pipeline</h3>
    <div class="market-row-list">
      ${line('Local sample runner', 'Wired in Rust CI', 'preview')}
      ${line('Normalized sample pack', 'Available from local files', 'preview')}
      ${line('Feature-count source', status.source, status.sourceStatus || 'preview')}
      ${line('Completed row count', status.completedRowText, status.rowStatus)}
      ${line('V1 readiness', status.readinessText, status.readinessStatus)}
      ${line('Real model', status.realModelText, status.realModelStatus)}
      ${line('Network/live calls', 'Off in normal beta flow', 'locked')}
    </div>
    <p class="muted">${esc(notes[0])}</p>
  `;
}

async function loadGeneratedFeatureCountStatus() {
  const paths = [
    'reports/feature_counts.json',
    '../reports/feature_counts.json',
    './reports/feature_counts.json',
    'feature_counts.json',
  ];
  for (const path of paths) {
    try {
      const report = await loadJson(path);
      return featureCountReportToStatus(report, path);
    } catch (_err) {
      // Keep trying fallbacks. The normal beta GUI must stay usable even when reports are absent.
    }
  }
  return null;
}

async function renderGeneratedFeatureCountStatus() {
  const status = await loadGeneratedFeatureCountStatus();
  if (status) renderDataStatus(status);
}

function featureCountReportToStatus(report, path) {
  const eligible = Number(report?.eligible_feature_rows ?? report?.completed_match_rows ?? 0);
  const minRows = Number(report?.min_required_rows ?? 200);
  const ready = Boolean(report?.ready);
  const modelReady = Boolean(report?.real_model_ready);
  const countText = `${Number.isFinite(eligible) ? eligible : 0} / ${Number.isFinite(minRows) ? minRows : 200} required for v1`;
  const readinessText = ready ? 'Count gate passed; eval required' : 'Needs more rows';
  const realModelText = modelReady ? 'Evaluation gate passed' : 'Locked until walk-forward eval/calibration';
  return {
    source: `Rust feature_counts.json (${path})`,
    sourceStatus: 'preview',
    completedRowText: countText,
    readinessText,
    rowStatus: ready ? 'preview' : 'locked',
    readinessStatus: ready ? 'placeholder' : 'locked',
    realModelText,
    realModelStatus: modelReady ? 'preview' : 'locked',
    notes: Array.isArray(report?.notes) && report.notes.length
      ? report.notes
      : ['Status only. Generated count report loaded; model trust still requires evaluation.'],
  };
}

function renderActions() {
  const panel = document.getElementById('matches-paper-actions');
  if (!panel) return;
  panel.innerHTML = `
    <h3>Paper Market Catalog</h3>
    <button id="matches-predict-selected">Preview selected</button>
    <button id="matches-predict-all">Preview all paper</button>
    <p class="muted">This catalog shows what OmniBet can preview now and what is locked until data/training exists.</p>
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

function marketStatus(status) {
  if (status === 'preview') return 'Preview now';
  if (status === 'placeholder') return 'Placeholder';
  return 'Locked: needs data';
}

function statusClass(status) {
  if (status === 'preview') return 'status-preview';
  if (status === 'placeholder') return 'status-placeholder';
  return 'status-locked';
}

function predictionSummary(snapshot) {
  const prediction = snapshot?.prediction || {};
  const fixture = snapshot?.fixture || {};
  const homeTeam = prediction.home_team || fixture.home_name || '';
  const awayTeam = prediction.away_team || fixture.away_name || '';
  const paperLean = prediction.paper_lean || prediction.lean || prediction.predicted_team || homeTeam || 'No lean';
  const side = paperLean === awayTeam ? 'away' : 'home';
  const opponent = side === 'away' ? homeTeam : awayTeam;
  const modelTrust = prediction.model_trust ?? prediction.trust ?? 0.25;
  return {
    homeTeam,
    awayTeam,
    paperLean,
    opponent,
    modelTrust,
    confidence: confidenceLabel(modelTrust),
    mode: prediction.decision_mode || prediction.mode || 'PAPER_ONLY',
  };
}

function line(label, value, status = 'preview') {
  return `
    <div class="market-row ${esc(statusClass(status))}">
      <span class="market-label">${esc(label)}</span>
      <span class="market-value">${esc(value)}</span>
      <span class="market-status">${esc(marketStatus(status))}</span>
    </div>
  `;
}

function list(items) {
  return `<ul>${items.map(item => `<li>${esc(item)}</li>`).join('')}</ul>`;
}

function marketCatalog(snapshot) {
  const s = predictionSummary(snapshot);
  const dc = `${s.paperLean} or Draw`;
  return [
    {
      title: 'Result and qualification',
      rows: [
        ['Paper lean', s.paperLean, 'preview'],
        ['Confidence', s.confidence, 'preview'],
        ['Double chance style', dc, 'placeholder'],
        ['To qualify', 'Needs knockout/extra-time model', 'locked'],
        ['Draw no bet', 'Needs calibrated result probability', 'locked'],
      ],
    },
    {
      title: 'Goals',
      rows: [
        ['Over 0.5', 'Plausible preview', 'placeholder'],
        ['Over 1.5', 'Plausible preview', 'placeholder'],
        ['Over 2.5', 'Needs trained scoring model', 'locked'],
        ['Both teams to score', 'Needs trained scoring model', 'locked'],
        ['Team goals', 'Needs attack/defence model', 'locked'],
      ],
    },
    {
      title: 'Scorelines and periods',
      rows: [
        ['Score bands', sideScoreBands(s).join(', '), 'placeholder'],
        ['Correct score', 'Needs score distribution model', 'locked'],
        ['Half-time result', 'Needs period model', 'locked'],
        ['First team to score', 'Needs time-to-goal model', 'locked'],
      ],
    },
    {
      title: 'Corners',
      rows: [
        ['Total corners', 'Needs corner event history', 'locked'],
        ['Team corners', 'Needs team crossing/pressure data', 'locked'],
        ['Corner handicap', 'Needs corner distribution model', 'locked'],
        ['Corners by half', 'Needs period corner model', 'locked'],
      ],
    },
    {
      title: 'Cards and discipline',
      rows: [
        ['Total cards', 'Needs card/referee history', 'locked'],
        ['Team cards', 'Needs team discipline model', 'locked'],
        ['Player carded', 'Needs lineup/player discipline data', 'locked'],
        ['Red card', 'Needs rare-event model', 'locked'],
      ],
    },
    {
      title: 'Player attack props',
      rows: [
        ['Anytime scorer', 'Needs lineups and player xG', 'locked'],
        ['First scorer', 'Needs scorer/time model', 'locked'],
        ['Player shots', 'Needs player shot history', 'locked'],
        ['Shots on target', 'Needs player SOT history', 'locked'],
        ['Assists', 'Needs player chance creation data', 'locked'],
      ],
    },
    {
      title: 'Player work-rate props',
      rows: [
        ['Tackles', 'Needs defensive event data', 'locked'],
        ['Fouls committed', 'Needs player foul history', 'locked'],
        ['Fouls won', 'Needs player touch/duel data', 'locked'],
        ['Passes', 'Needs passing and possession model', 'locked'],
      ],
    },
    {
      title: 'Set pieces and misc events',
      rows: [
        ['Free kicks', 'Needs granular event feed', 'locked'],
        ['Offsides', 'Needs attacking line/style data', 'locked'],
        ['Throw-ins', 'Needs event feed', 'locked'],
        ['Penalties awarded', 'Needs rare-event + referee model', 'locked'],
      ],
    },
  ];
}

function sideScoreBands(s) {
  if (s.paperLean === s.awayTeam) return ['0-1', '1-2', '1-1 risk'];
  return ['1-0', '2-1', '1-1 risk'];
}

function renderMarketSection(section) {
  return `
    <div class="card market-catalog-section">
      <h3>${esc(section.title)}</h3>
      <div class="market-row-list">
        ${section.rows.map(row => line(row[0], row[1], row[2])).join('')}
      </div>
    </div>
  `;
}

function renderPredictionCard(snapshot) {
  const s = predictionSummary(snapshot);
  const sections = marketCatalog(snapshot);
  return `
    <div class="card prediction-card">
      <h3>${esc(s.homeTeam)} vs ${esc(s.awayTeam)}</h3>
      <div class="card market-builder-main">
        <h2>Paper lean: ${esc(s.paperLean)}</h2>
        ${line('Confidence', s.confidence, 'preview')}
        ${line('Mode', s.mode, 'preview')}
        ${line('Model trust', s.modelTrust, 'preview')}
      </div>
      <div class="grid market-catalog-grid">
        ${sections.map(renderMarketSection).join('')}
      </div>
      <div class="card">
        <h3>Capability warning</h3>
        ${list([
          'Only fixture-level preview is active right now.',
          'Corners, cards, free kicks, offsides, player props and passes need future data.',
          'Training/evaluation must happen on completed timestamp-safe rows before confidence is real.',
          'Paper-only preview; not advice and not staking output.',
        ])}
      </div>
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
    result.innerHTML = '<h3>Paper Market Catalog</h3><p class="muted">Select a match, then press Preview selected.</p>';
    return;
  }
  result.innerHTML = `<h3>Paper Market Catalog</h3><p class="muted">Ready to preview ${esc(fixture.home_name)} vs ${esc(fixture.away_name)}.</p>`;
}

async function runPredictSelected() {
  const result = document.getElementById('matches-result');
  try {
    if (result) result.innerHTML = '<h3>Paper Market Catalog</h3><p class="muted">Building broad paper market preview...</p>';
    scrollResultIntoView();
    const snapshot = await predictSelectedUpcomingFixture();
    if (result) {
      result.innerHTML = `<h3>Paper Market Catalog Preview</h3>${renderPredictionCard(snapshot)}`;
      scrollResultIntoView();
    }
  } catch (err) {
    if (result) result.innerHTML = `<h3>Paper Market Catalog</h3><p class="warn">${esc(err)}</p>`;
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
  if (result) result.innerHTML = `<h3>Preview all paper</h3><p class="muted">Building ${esc(fixtures.length)} broad market previews...</p>`;
  scrollResultIntoView();
  for (const fixture of fixtures) {
    selectFixture(fixture);
    const snapshot = await predictSelectedUpcomingFixture();
    snapshots.push(snapshot);
  }
  window.__omnibetLastForecastBatch = snapshots;
  if (result) {
    result.innerHTML = `<h3>Paper Market Catalog Batch</h3>${snapshots.map(renderPredictionCard).join('')}`;
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
  renderDataStatus();
  renderGeneratedFeatureCountStatus();
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
