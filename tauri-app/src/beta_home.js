function esc(value) {
  return String(value ?? '').replace(/[&<>"]/g, ch => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[ch]));
}

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
    button.textContent = 'Start Here';
    nav.insertBefore(button, nav.firstChild);
  }

  const main = document.querySelector('.main-panel');
  if (main && !document.getElementById('beta-home')) {
    const section = document.createElement('section');
    section.id = 'beta-home';
    section.className = 'page';
    section.dataset.pagePanel = 'beta-home';
    section.innerHTML = `
      <div id="beta-home-hero" class="card"><div class="muted">Loading beta start page...</div></div>
      <div id="beta-home-actions" class="grid"></div>
      <div id="beta-home-world-cup" class="card"><div class="muted">World Cup paper lab status not loaded.</div></div>
      <div id="beta-home-trust" class="card"><div class="muted">Trust status not loaded.</div></div>
      <div id="beta-home-next" class="card"><div class="muted">Next steps not loaded.</div></div>
    `;
    const firstPage = document.querySelector('.page');
    if (firstPage) {
      main.insertBefore(section, firstPage);
    } else {
      main.appendChild(section);
    }
  }
}

ensureBetaHomePage();

async function loadJson(path) {
  const response = await fetch(path);
  if (!response.ok) throw new Error(`failed to load ${path}: ${response.status}`);
  return response.json();
}

function actionButton(action) {
  return `<button class="beta-home-action" data-target-page="${esc(action.target_page)}" data-run-button="${esc(action.button_id)}">${esc(action.title)}</button>`;
}

function renderHero(payload) {
  const panel = document.getElementById('beta-home-hero');
  if (!panel) return;
  panel.innerHTML = `
    <h2>${esc(payload.title || 'OmniBet Lab Desktop Beta')}</h2>
    <p class="warn">PAPER_ONLY beta. Local files and sample reports first. No real-money recommendations.</p>
    <p>${esc(payload.subtitle || '')}</p>
    <p class="muted">Use this page as the simple path. Advanced/debug panels remain in the sidebar.</p>
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
    <h3>World Cup paper lab</h3>
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
    <h3>Trust and training lock</h3>
    <table>
      <tr><th>Field</th><th>Value</th></tr>
      <tr><td>Ready for training</td><td>${esc(trust.ready_for_training)}</td></tr>
      <tr><td>Trust status</td><td>${esc(trust.trust_status)}</td></tr>
      <tr><td>Live provider calls</td><td>${esc(trust.live_provider_calls_allowed)}</td></tr>
      <tr><td>Recommendations</td><td>${esc(trust.recommendation_output_present)}</td></tr>
      <tr><td>Credentials present</td><td>${esc(trust.credential_values_present)}</td></tr>
    </table>
    <p class="warn">${esc(trust.message || 'GUI beta can move fast; prediction/training engine must move slow.')}</p>
  `;
}

function renderNext(payload) {
  const panel = document.getElementById('beta-home-next');
  if (!panel) return;
  const rows = Array.isArray(payload.next) ? payload.next : [];
  panel.innerHTML = `
    <h3>Next sensible steps</h3>
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

export async function loadAndRenderBetaHome(path = 'tauri-app/src/beta-home.sample.json') {
  const payload = await loadJson(path);
  renderBetaHome(payload);
  return payload;
}

loadAndRenderBetaHome().catch(err => {
  const panel = document.getElementById('beta-home-hero');
  if (panel) panel.innerHTML = `<h2>OmniBet Lab Desktop Beta</h2><p class="warn">Failed to load beta home: ${esc(err)}</p>`;
});
