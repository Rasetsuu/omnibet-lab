function esc(value) {
  return String(value ?? '').replace(/[&<>"]/g, ch => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[ch]));
}

async function loadJson(path) {
  const response = await fetch(path);
  if (!response.ok) throw new Error(`failed to load ${path}: ${response.status}`);
  return response.json();
}

function renderMilestones(items) {
  return `<ul>${(items || []).map(item => `<li>${esc(item)}</li>`).join('')}</ul>`;
}

function renderPhases(phases) {
  return (phases || []).map(phase => `
    <div class="card">
      <h3>${esc(phase.range)} · ${esc(phase.label)}</h3>
      <div class="stat-row"><span>Phase</span><strong>${esc(phase.phase_id)}</strong></div>
      <div class="stat-row"><span>Status</span><strong>${esc(phase.status)}</strong></div>
      ${renderMilestones(phase.milestones)}
    </div>
  `).join('');
}

function renderQa(items) {
  return `<ol>${(items || []).map(item => `<li>${esc(item)}</li>`).join('')}</ol>`;
}

function renderContract(contract) {
  const dirs = contract?.directories || [];
  const files = Object.entries(contract?.files || {});
  return `
    <h3>v197-v204 Local persistence</h3>
    <div class="stat-row"><span>Root</span><strong>${esc(contract?.root)}</strong></div>
    <div class="muted">Directories</div>
    ${renderMilestones(dirs)}
    <div class="muted">Files</div>
    <ul>${files.map(([k, v]) => `<li>${esc(k)} → ${esc(v)}</li>`).join('')}</ul>
  `;
}

function renderReleaseGate(gate) {
  return Object.entries(gate || {}).map(([key, value]) => `
    <div class="stat-row"><span>${esc(key)}</span><strong>${esc(value)}</strong></div>
  `).join('');
}

export function renderBetaReleaseTrain(payload) {
  const panel = document.getElementById('beta-release-train-panel');
  if (!panel) return payload;
  panel.innerHTML = `
    <div class="grid">
      <div id="beta-release-train-gate" class="card"><h3>v221-v228 Beta release gate</h3>${renderReleaseGate(payload.release_gate)}</div>
      <div id="beta-release-train-qa" class="card"><h3>v181-v188 QA checklist</h3>${renderQa(payload.qa_checklist)}</div>
      <div id="beta-release-train-persistence" class="card">${renderContract(payload.local_persistence_contract)}</div>
      <div id="beta-release-train-evaluation" class="card"><h3>v205-v212 Evaluation path</h3>${renderReleaseGate(payload.evaluation_contract)}</div>
      <div id="beta-release-train-boundaries" class="card"><h3>Boundaries</h3>${renderReleaseGate(payload.boundaries)}</div>
    </div>
    <div id="beta-release-train-phases" class="grid">${renderPhases(payload.phases)}</div>
  `;
  window.__omnibetBetaReleaseTrain = payload;
  return payload;
}

export async function loadAndRenderBetaReleaseTrain(path = 'tauri-app/src/beta-release-train.sample.json') {
  const payload = await loadJson(path);
  return renderBetaReleaseTrain(payload);
}
