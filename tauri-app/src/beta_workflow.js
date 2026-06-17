function esc(value) {
  return String(value ?? '').replace(/[&<>"]/g, ch => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[ch]));
}

async function loadJson(path) {
  const response = await fetch(path);
  if (!response.ok) throw new Error(`failed to load ${path}: ${response.status}`);
  return response.json();
}

function renderSteps(steps) {
  if (!steps || !steps.length) return '<div class="muted">No workflow steps.</div>';
  return steps.map(step => `
    <div class="card">
      <h3>${esc(step.label)}</h3>
      <div class="stat-row"><span>Step</span><strong>${esc(step.step_id)}</strong></div>
      <div class="stat-row"><span>Page</span><strong>${esc(step.page)}</strong></div>
      <div class="stat-row"><span>Status</span><strong>${esc(step.status)}</strong></div>
    </div>
  `).join('');
}

function renderState(state) {
  const rows = Object.entries(state || {});
  if (!rows.length) return '<div class="muted">No state.</div>';
  return rows.map(([key, value]) => `
    <div class="stat-row"><span>${esc(key)}</span><strong>${value ? 'ready' : 'pending'}</strong></div>
  `).join('');
}

function renderReadiness(readiness) {
  const remaining = readiness?.remaining_before_live_beta || [];
  return `
    <h3>v178 Readiness</h3>
    <div class="stat-row"><span>Completed parts</span><strong>${esc(readiness?.completed_parts)}</strong></div>
    <ul>${remaining.map(item => `<li>${esc(item)}</li>`).join('')}</ul>
  `;
}

function renderBoundaries(boundaries) {
  return `
    <h3>v179 Boundaries</h3>
    ${Object.entries(boundaries || {}).map(([key, value]) => `<div class="stat-row"><span>${esc(key)}</span><strong>${value ? 'yes' : 'no'}</strong></div>`).join('')}
  `;
}

export function renderBetaWorkflow(payload) {
  const panel = document.getElementById('beta-workflow-panel');
  if (!panel) return payload;
  panel.innerHTML = `
    <div class="grid">
      <div id="beta-workflow-state" class="card"><h3>v174 Workflow state</h3>${renderState(payload.workflow_state)}</div>
      <div id="beta-workflow-readiness" class="card">${renderReadiness(payload.readiness)}</div>
      <div id="beta-workflow-boundaries" class="card">${renderBoundaries(payload.boundaries)}</div>
    </div>
    <div id="beta-workflow-steps" class="grid">${renderSteps(payload.steps)}</div>
  `;
  window.__omnibetBetaWorkflow = payload;
  return payload;
}

export async function loadAndRenderBetaWorkflow(path = 'tauri-app/src/beta-workflow.sample.json') {
  const payload = await loadJson(path);
  return renderBetaWorkflow(payload);
}
