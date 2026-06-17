function esc(value) {
  return String(value ?? '').replace(/[&<>"]/g, ch => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[ch]));
}

async function loadJson(path) {
  const response = await fetch(path);
  if (!response.ok) throw new Error(`failed to load ${path}: ${response.status}`);
  return response.json();
}

function renderList(items, renderItem) {
  if (!items || !items.length) return '<div class="muted">None.</div>';
  return `<ul>${items.map(renderItem).join('')}</ul>`;
}

function renderWizard(payload) {
  const wizard = payload?.desktop_beta?.import_wizard || payload?.import_wizard || {};
  return `
    <h3>v134 Import wizard</h3>
    <p class="muted">Local-file guided import shell. No credentials and no live calls.</p>
    ${renderList(wizard.steps || [], step => `<li><strong>${esc(step.label || step.step_id)}</strong> ${step.required ? '<span class="pill">required</span>' : '<span class="pill">optional</span>'}</li>`)}
    <div class="muted">Accepted: ${esc((wizard.accepted_file_kinds || []).join(', ') || 'n/a')}</div>
  `;
}

function renderCoverage(payload) {
  const coverage = payload?.desktop_beta?.coverage || payload?.coverage || {};
  const summary = coverage.summary || {};
  const competitions = coverage.competitions || [];
  return `
    <h3>v135 Coverage</h3>
    <div class="stat-row"><span>Competitions</span><strong>${esc(summary.covered_competitions)}</strong></div>
    <div class="stat-row"><span>Trainable rows</span><strong>${esc(summary.trainable_rows)}</strong></div>
    <div class="stat-row"><span>Evaluation rows</span><strong>${esc(summary.evaluation_rows)}</strong></div>
    ${renderList(competitions.slice(0, 8), comp => `<li>${esc(comp.competition_id)} — ${esc(comp.status)} / ${esc(comp.seasons)} seasons</li>`)}
  `;
}

function renderEvaluation(payload) {
  const evaluation = payload?.desktop_beta?.evaluation || payload?.evaluation || {};
  const summary = evaluation.summary || {};
  const metrics = evaluation.metrics || [];
  return `
    <h3>v136 Evaluation</h3>
    <div class="stat-row"><span>Family</span><strong>${esc(summary.model_family)}</strong></div>
    <div class="stat-row"><span>Rows</span><strong>${esc(summary.evaluation_rows)}</strong></div>
    <div class="stat-row"><span>Calibration rows</span><strong>${esc(summary.calibration_rows)}</strong></div>
    ${renderList(metrics, row => `<li>${esc(row.competition_id)} — Brier ${esc(row.brier)}, Acc ${esc(row.accuracy_at_0_5)}</li>`)}
  `;
}

function renderReports(payload) {
  const viewer = payload?.desktop_beta?.report_viewer || payload?.report_viewer || {};
  return `
    <h3>v137 Report viewer</h3>
    ${renderList(viewer.reports || [], report => `<li><strong>${esc(report.report_id)}</strong> — ${esc(report.kind)} / ${esc(report.severity)}</li>`)}
  `;
}

function renderBackup(payload) {
  const backup = payload?.desktop_beta?.backup_contract || payload?.backup_contract || {};
  return `
    <h3>v138 Local bundle</h3>
    <p class="muted">Local backup/export/import contract for app data.</p>
    ${renderList(backup.operations || [], op => `<li>${esc(op)}</li>`)}
  `;
}

function renderChecklist(payload) {
  const checklist = payload?.desktop_beta?.release_checklist || payload?.release_checklist || {};
  return `
    <h3>v139 Readiness checklist</h3>
    ${renderList(checklist.items || [], item => `<li>${esc(item.check_id)} ${item.required ? '<span class="pill">required</span>' : ''}</li>`)}
  `;
}

export function renderDesktopBeta(payload) {
  const root = document.getElementById('desktop-beta-panel');
  if (!root) return payload;
  root.innerHTML = `
    <div class="grid">
      <div id="desktop-beta-import-wizard" class="card">${renderWizard(payload)}</div>
      <div id="desktop-beta-coverage" class="card">${renderCoverage(payload)}</div>
      <div id="desktop-beta-evaluation" class="card">${renderEvaluation(payload)}</div>
      <div id="desktop-beta-reports" class="card">${renderReports(payload)}</div>
      <div id="desktop-beta-backup" class="card">${renderBackup(payload)}</div>
      <div id="desktop-beta-checklist" class="card">${renderChecklist(payload)}</div>
    </div>
  `;
  return payload;
}

export async function loadAndRenderDesktopBeta(path = 'tauri-app/src/desktop-beta.sample.json') {
  const payload = await loadJson(path);
  return renderDesktopBeta(payload);
}
