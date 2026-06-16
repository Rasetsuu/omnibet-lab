import { fixtureTeams, invokeCommand } from './api.js';
import { loadAndRenderDashboard } from './dashboard.js';

function out(x) {
  const el = document.getElementById('out');
  if (el) el.textContent = typeof x === 'string' ? x : JSON.stringify(x, null, 2);
}

function showPage(id) {
  document.querySelectorAll('.page').forEach(page => {
    page.classList.toggle('active-page', page.id === id);
  });
  document.querySelectorAll('.nav-button').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.page === id);
  });
}

async function safeRun(fn) {
  try {
    out(await fn());
  } catch (err) {
    out({ ok: false, error: String(err) });
  }
}

function bind() {
  document.querySelectorAll('.nav-button').forEach(btn => {
    btn.addEventListener('click', () => showPage(btn.dataset.page));
  });

  document.getElementById('load-dashboard-report')?.addEventListener('click', () => safeRun(() => loadAndRenderDashboard(null)));
  document.getElementById('load-dashboard-sample')?.addEventListener('click', () => safeRun(() => loadAndRenderDashboard('tauri-app/src/dashboard-data.sample.json')));
  document.getElementById('ping-button')?.addEventListener('click', () => safeRun(() => invokeCommand('ping')));
  document.getElementById('pack-summary-button')?.addEventListener('click', () => safeRun(() => invokeCommand('pack_summary')));
  document.getElementById('detailed-pack-summary-button')?.addEventListener('click', () => safeRun(() => invokeCommand('pack_summary')));
  document.getElementById('predict-fixture-button')?.addEventListener('click', () => safeRun(() => invokeCommand('predict_fixture', fixtureTeams())));
  document.getElementById('value-report-button')?.addEventListener('click', () => safeRun(() => invokeCommand('value_report', fixtureTeams())));
}

bind();
showPage('dashboard');
