import { fixtureTeams, invokeCommand } from './api.js';
import { loadAndRenderDashboard } from './dashboard.js';
import { loadAndRenderReviews } from './review.js';
import { loadAndRenderSettings } from './settings.js';
import { loadAndRenderPhase2Forecast } from './models.js';
import { loadAndRenderDesktopBeta } from './desktop_beta.js';
import { exportLocalImportBundle, runLocalImportPreview } from './local_import.js';
import { exportForecastSnapshot, loadAndRenderUpcomingFixtures, predictSelectedUpcomingFixture } from './upcoming.js';
import { importExternalFixtureCacheToUpcoming, loadAndRenderExternalData } from './external_data.js';
import { loadAndRenderBetaWorkflow } from './beta_workflow.js';

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

function selectedLocalImportFile() {
  const input = document.getElementById('local-import-file');
  return input?.files?.[0] || null;
}

function bind() {
  document.querySelectorAll('.nav-button').forEach(btn => {
    btn.addEventListener('click', () => showPage(btn.dataset.page));
  });

  document.getElementById('load-dashboard-report')?.addEventListener('click', () => safeRun(() => loadAndRenderDashboard(null)));
  document.getElementById('load-dashboard-sample')?.addEventListener('click', () => safeRun(() => loadAndRenderDashboard('tauri-app/src/dashboard-data.sample.json')));
  document.getElementById('load-review-report')?.addEventListener('click', () => safeRun(() => loadAndRenderReviews(null)));
  document.getElementById('load-review-sample')?.addEventListener('click', () => safeRun(() => loadAndRenderReviews('tauri-app/src/review-data.sample.json')));
  document.getElementById('load-settings-report')?.addEventListener('click', () => safeRun(() => loadAndRenderSettings(null)));
  document.getElementById('load-settings-sample')?.addEventListener('click', () => safeRun(() => loadAndRenderSettings('tauri-app/src/settings-data.sample.json')));
  document.getElementById('load-phase2-forecast')?.addEventListener('click', () => safeRun(() => loadAndRenderPhase2Forecast()));
  document.getElementById('load-upcoming-fixtures')?.addEventListener('click', () => safeRun(() => loadAndRenderUpcomingFixtures()));
  document.getElementById('load-external-data')?.addEventListener('click', () => safeRun(() => loadAndRenderExternalData()));
  document.getElementById('load-beta-workflow')?.addEventListener('click', () => safeRun(() => loadAndRenderBetaWorkflow()));
  document.getElementById('load-desktop-beta')?.addEventListener('click', () => safeRun(() => loadAndRenderDesktopBeta()));
  document.getElementById('import-external-fixtures')?.addEventListener('click', () => safeRun(() => importExternalFixtureCacheToUpcoming()));
  document.getElementById('predict-selected-upcoming-fixture')?.addEventListener('click', () => safeRun(() => predictSelectedUpcomingFixture()));
  document.getElementById('export-forecast-snapshot')?.addEventListener('click', () => safeRun(() => exportForecastSnapshot()));
  document.getElementById('run-local-import-preview')?.addEventListener('click', () => safeRun(() => runLocalImportPreview(selectedLocalImportFile())));
  document.getElementById('export-local-import-bundle')?.addEventListener('click', () => safeRun(() => exportLocalImportBundle()));
  document.getElementById('ping-button')?.addEventListener('click', () => safeRun(() => invokeCommand('ping')));
  document.getElementById('pack-summary-button')?.addEventListener('click', () => safeRun(() => invokeCommand('pack_summary')));
  document.getElementById('detailed-pack-summary-button')?.addEventListener('click', () => safeRun(() => invokeCommand('pack_summary')));
  document.getElementById('predict-fixture-button')?.addEventListener('click', () => safeRun(() => invokeCommand('predict_fixture', fixtureTeams())));
  document.getElementById('value-report-button')?.addEventListener('click', () => safeRun(() => invokeCommand('value_report', fixtureTeams())));
}

bind();
showPage('dashboard');
