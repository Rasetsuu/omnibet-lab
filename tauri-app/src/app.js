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
import { loadAndRenderBetaReleaseTrain } from './beta_release_train.js';
import { generateAndRenderSourceTerminal, loadAndRenderSourceTerminal } from './source_terminal.js';
import { loadAndRenderLiveSourceBridge } from './live_source.js';
import { loadAndRenderMarketTerminalMvp } from './market_terminal.js';
import { generateAndRenderDatasetMaterialization, loadAndRenderDatasetMaterialization } from './dataset_materialization.js';
import { loadAndRenderStorageWritersStatus } from './storage_writers.js';
import { loadAndRenderWalkForwardEvaluatorStatus } from './walk_forward_evaluator.js';
import { loadAndRenderBaselineReportsStatus } from './baseline_reports.js';
import { loadAndRenderCalibrationClvStatus } from './calibration_clv.js';

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

function bindSourceGenerateButton(id) {
  document.getElementById(id)?.addEventListener('click', () => safeRun(() => generateAndRenderSourceTerminal()));
}

function bindSourceLoadButton(id, pathHint = null) {
  document.getElementById(id)?.addEventListener('click', () => safeRun(() => loadAndRenderSourceTerminal(pathHint)));
}

function bindDatasetMaterializationLoadButton(id, pathHint = 'tauri-app/src/dataset-materialization.sample.json') {
  document.getElementById(id)?.addEventListener('click', () => safeRun(() => loadAndRenderDatasetMaterialization(pathHint)));
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
  bindSourceLoadButton('load-source-terminal-report', null);
  bindSourceLoadButton('load-source-terminal-report-topbar', null);
  bindSourceLoadButton('load-source-terminal-sample', 'tauri-app/src/source-terminal.sample.json');
  bindSourceLoadButton('load-source-terminal-sample-topbar', 'tauri-app/src/source-terminal.sample.json');
  bindSourceGenerateButton('generate-source-terminal-report');
  bindSourceGenerateButton('generate-source-terminal-report-topbar');
  document.getElementById('load-live-source-bridge')?.addEventListener('click', () => safeRun(() => loadAndRenderLiveSourceBridge()));
  document.getElementById('load-market-terminal-mvp')?.addEventListener('click', () => safeRun(() => loadAndRenderMarketTerminalMvp()));
  document.getElementById('generate-dataset-materialization-preview')?.addEventListener('click', () => safeRun(() => generateAndRenderDatasetMaterialization()));
  bindDatasetMaterializationLoadButton('load-dataset-materialization-preview');
  bindDatasetMaterializationLoadButton('load-dataset-materialization-sample', 'tauri-app/src/dataset-materialization.sample.json');
  document.getElementById('load-storage-writers-status')?.addEventListener('click', () => safeRun(() => loadAndRenderStorageWritersStatus()));
  document.getElementById('load-walk-forward-evaluator-status')?.addEventListener('click', () => safeRun(() => loadAndRenderWalkForwardEvaluatorStatus()));
  document.getElementById('load-baseline-reports-status')?.addEventListener('click', () => safeRun(() => loadAndRenderBaselineReportsStatus()));
  document.getElementById('load-calibration-clv-status')?.addEventListener('click', () => safeRun(() => loadAndRenderCalibrationClvStatus()));
  document.getElementById('load-phase2-forecast')?.addEventListener('click', () => safeRun(() => loadAndRenderPhase2Forecast()));
  document.getElementById('load-upcoming-fixtures')?.addEventListener('click', () => safeRun(() => loadAndRenderUpcomingFixtures()));
  document.getElementById('load-external-data')?.addEventListener('click', () => safeRun(() => loadAndRenderExternalData()));
  document.getElementById('load-beta-workflow')?.addEventListener('click', () => safeRun(() => loadAndRenderBetaWorkflow()));
  document.getElementById('load-beta-release-train')?.addEventListener('click', () => safeRun(() => loadAndRenderBetaReleaseTrain()));
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
