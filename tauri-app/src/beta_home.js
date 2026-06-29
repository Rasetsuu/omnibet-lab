function esc(value) {
  return String(value ?? '').replace(/[&<>"]/g, ch => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[ch]));
}

const FALLBACK_BETA_HOME = {
  title: 'OmniBet Lab',
  subtitle: 'Simple match screen. Pick matches and run the local research flow.',
  primary_actions: [
    { title: 'Incoming matches', description: 'Open the upcoming match screen.', target_page: 'upcoming', button_id: 'load-upcoming-fixtures' },
    { title: 'Start demo', description: 'Open bundled sample output.', target_page: 'generated-green', button_id: 'load-generated-green-status-page' },
    { title: 'Historical files', description: 'Open local file adapter.', target_page: 'historical-file-adapter', button_id: 'load-historical-file-adapter-status-page' },
    { title: 'Materialization', description: 'Open local materialization status.', target_page: 'historical-materialization', button_id: 'load-historical-materialization-status-page' }
  ],
  world_cup_paper_lab: {
    status: 'local_placeholder',
    safe_use: 'Next phase should add local World Cup fixtures and one obvious action.',
    next_step: 'Keep background work internal and keep this screen simple.'
  },
  trust: {
    ready_for_training: false,
    trust_status: 'sample_only',
    message: 'Background evaluation stays internal. The visible app stays simple.'
  },
  next: [
    'Replace the debug dashboard with incoming matches.',
    'Hide internal pages behind advanced mode.',
    'Add local World Cup fixtures next.',
    'Use completed matches for background learning only.'
  ]
};

function showBetaPage(id) {
  document.querySelectorAll('.page').forEach(page => {
    page.classList.toggle('active-page', page.id === id);
  });
  document.querySelectorAll('.nav-button').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.page === id);
  });
}

function ensureBetaHomePage() {
  const nav = document.querySelector('.nav');
  if (nav && !document.querySelector('[data-page="beta-home"]')) {
    const button = document.createElement('button');
    button.className = 'nav-button';
    button.dataset.page = 'beta-home';
    button.textContent = 'Matches';
    nav.insertBefore(button, nav.firstChild);
  }

  const main = document.querySelector('.main-panel');
  if (main && !document.getElementById('beta-home')) {
    const section = document.createElement('section');
    section.id = 'beta-home';
    section.className = 'page';
    section.dataset.pagePanel = 'beta-home';
    section.innerHTML = `
      <div id="beta-home-hero" class="card"><div class="muted">Loading...</div></div>
      <div id="beta-home-actions" class="grid"></div>
      <div id="beta-home-world-cup" class="card"></div>
      <div id="beta-home-trust" class="card"></div>
      <div id="beta-home-next" class="card"></div>
    `;
    const firstPage = document.querySelector('.page');
    if (firstPage) main.insertBefore(section, firstPage);
    else main.appendChild(section);
  }
}

ensureBetaHomePage();

async function loadJson(path) {
  const response = await fetch(path);
  if (!response.ok) throw new Error(`failed to load ${path}: ${response.status}`);
  return response.json();
}

async function loadFirstAvailableBetaHome(pathHint) {
  const candidates = [pathHint, 'beta-home.sample.json', './beta-home.sample.json', 'tauri-app/src/beta-home.sample.json'].filter(Boolean);
  for (const path of candidates) {
    try {
      return await loadJson(path);
    } catch (_err) {
    }
  }
  return FALLBACK_BETA_HOME;
}

function actionButton(action) {
  return `<button class="beta-home-action" data-target-page="${esc(action.target_page)}" data-run-button="${esc(action.button_id)}">${esc(action.title)}</button>`;
}

function renderHero(payload) {
  const panel = document.getElementById('beta-home-hero');
  if (!panel) return;
  panel.innerHTML = `
    <h2>${esc(payload.title || 'OmniBet Lab')}</h2>
    <p>${esc(payload.subtitle || '')}</p>
  `;
}

function renderActions(payload) {
  const panel = document.getElementById('beta-home-actions');
  if (!panel) return;
  const actions = Array.isArray(payload.primary_actions) ? payload.primary_actions : [];
  panel.innerHTML = actions.map(action => `
    <div class="card beta-home-card">
      <h3>${esc(action.title)}</h3>
      <p>${esc(action.description)}</p>
      ${actionButton(action)}
    </div>
  `).join('');

  panel.querySelectorAll('.beta-home-action').forEach(button => {
    button.addEventListener('click', () => {
      const target = button.dataset.targetPage;
      const runButton = button.dataset.runButton;
      if (target) showBetaPage(target);
      if (runButton) document.getElementById(runButton)?.click();
    });
  });
}

function renderWorldCup(payload) {
  const panel = document.getElementById('beta-home-world-cup');
  if (!panel) return;
  const wc = payload.world_cup_paper_lab || {};
  panel.innerHTML = `
    <h3>World Cup lab</h3>
    <p>Status: ${esc(wc.status || 'placeholder')}</p>
    <p>${esc(wc.safe_use || '')}</p>
    <p class="muted">${esc(wc.next_step || '')}</p>
  `;
}

function renderTrust(payload) {
  const panel = document.getElementById('beta-home-trust');
  if (!panel) return;
  const trust = payload.trust || {};
  panel.innerHTML = `
    <h3>Internal status</h3>
    <p>${esc(trust.message || '')}</p>
    <p class="muted">Status: ${esc(trust.trust_status)} · Training ready: ${esc(trust.ready_for_training)}</p>
  `;
}

function renderNext(payload) {
  const panel = document.getElementById('beta-home-next');
  if (!panel) return;
  const rows = Array.isArray(payload.next) ? payload.next : [];
  panel.innerHTML = `
    <h3>Next</h3>
    <ol>${rows.map(row => `<li>${esc(row)}</li>`).join('')}</ol>
  `;
}

export function renderBetaHome(payload) {
  ensureBetaHomePage();
  renderHero(payload);
  renderActions(payload);
  renderWorldCup(payload);
  renderTrust(payload);
  renderNext(payload);
  return payload;
}

export async function loadAndRenderBetaHome(path = 'beta-home.sample.json') {
  const payload = await loadFirstAvailableBetaHome(path);
  renderBetaHome(payload);
  return payload;
}

loadAndRenderBetaHome().catch(_err => {
  renderBetaHome(FALLBACK_BETA_HOME);
});
