import { invokeCommand, loadAppSettings, runLocalWorkflow } from './api.js';
import { esc, table } from './dashboard.js';

let settingsState = null;

function setHtml(id, html) {
  const el = document.getElementById(id);
  if (el) el.innerHTML = html;
}

function unwrapSettingsPayload(payload) {
  if (payload && payload.settings_json) return payload.settings_json;
  return payload;
}

function badge(value) {
  return `<span class="pill">${esc(value)}</span>`;
}

function renderPaths(paths = {}) {
  return table(Object.entries(paths).map(([key, value]) => ({ key, value })), [
    { key: 'key', label: 'Path key' },
    { key: 'value', label: 'Local path' }
  ]);
}

function renderProviderStatus(providers = []) {
  return table(providers, [
    { key: 'provider_id', label: 'Source' },
    { key: 'enabled', label: 'Enabled' },
    { key: 'api_key_env', label: 'Env name' },
    { key: 'key_status_only', label: 'Status only' },
    { key: 'live_calls_in_ci', label: 'CI external calls' }
  ]);
}

function renderSourceControls(sources = []) {
  if (!sources.length) return '<div class="muted">No source controls configured.</div>';
  return sources.map(s => `
    <div class="card source-card">
      <h3>${esc(s.label || s.source_id)}</h3>
      <p>${badge(s.source_id)} ${badge('enabled: ' + String(s.enabled))} ${badge('manual only: ' + String(s.manual_action_only))}</p>
      <p class="muted">Credential env: ${esc(s.credential_env)} · status only: ${esc(s.credential_status_only)}</p>
      <button class="source-status-button" data-source-id="${esc(s.source_id)}">Refresh source status</button>
      <button class="source-cache-button" data-source-id="${esc(s.source_id)}">Cache local sample snapshot</button>
      <div class="source-status" id="source-status-${esc(s.source_id)}">state: idle</div>
    </div>
  `).join('');
}

function renderWorkflowButtons(workflows = []) {
  if (!workflows.length) return '<div class="muted">No workflows configured.</div>';
  return workflows.map(w => `
    <div class="card workflow-card">
      <h3>${esc(w.label)}</h3>
      <p class="muted">${esc(w.description)}</p>
      <p>${badge(w.workflow_id)} ${w.refresh_hint ? badge('refresh: ' + w.refresh_hint) : ''}</p>
      <p class="muted">Expected report: ${esc(w.expected_report || 'reported by workflow result')}</p>
      <button class="local-workflow-button" data-workflow-id="${esc(w.workflow_id)}">Run local workflow</button>
      <div class="workflow-status" id="workflow-status-${esc(w.workflow_id)}">state: idle</div>
    </div>
  `).join('');
}

function renderPromotionControls(promotion = {}) {
  if (!promotion.enabled) return '<div class="muted">Promotion controls disabled.</div>';
  return `
    <div class="card promotion-card">
      <h3>${esc(promotion.label || 'Promote accepted review decisions')}</h3>
      <p>${badge('candidate only: ' + String(promotion.candidate_only))}</p>
      <p class="muted">Output: ${esc(promotion.candidate_output || '.omnibet-local/exports/mapping_rule_candidates.v66.json')}</p>
      <button id="promote-review-decisions">Write candidate rule file</button>
      <div id="promotion-status">state: idle</div>
    </div>
  `;
}

export function renderSettings(data) {
  settingsState = data;
  const runtime = data.runtime || {};
  const safety = data.safety || {};
  const workflows = data.local_workflows || [];
  const runtimeRows = Object.entries(runtime).map(([key, value]) => ({ key, value }));
  const safetyRows = Object.entries(safety).map(([key, value]) => ({ key, value }));

  setHtml('settings-paths', `<h3>Local paths</h3>${renderPaths(data.paths || {})}`);
  setHtml('settings-runtime', `<h3>Runtime</h3>${table(runtimeRows, [{ key: 'key', label: 'Setting' }, { key: 'value', label: 'Value' }])}`);
  setHtml('settings-providers', `<h3>Sources</h3><p class="muted">Credential values are never displayed here; only env names/status are shown.</p>${renderProviderStatus(data.providers || [])}<h3>Source opt-in/cache controls</h3>${renderSourceControls(data.source_controls || [])}`);
  setHtml('settings-safety', `<h3>Safety</h3>${table(safetyRows, [{ key: 'key', label: 'Rule' }, { key: 'value', label: 'Value' }])}`);
  setHtml('local-run-buttons', `<h3>Local workflow controls</h3><p class="muted">Allowlisted offline workflows only. No shell execution.</p>${renderWorkflowButtons(workflows)}<h3>Review promotion</h3>${renderPromotionControls(data.promotion_controls || {})}`);
  bindWorkflowButtons();
  bindSourceButtons();
  bindPromotionButton();
}

function updateWorkflowStatus(workflowId, text) {
  const el = document.getElementById(`workflow-status-${workflowId}`);
  if (el) el.textContent = text;
}

function updateSourceStatus(sourceId, text) {
  const el = document.getElementById(`source-status-${sourceId}`);
  if (el) el.textContent = text;
}

function bindWorkflowButtons() {
  document.querySelectorAll('.local-workflow-button').forEach(btn => {
    btn.addEventListener('click', async () => {
      const workflowId = btn.dataset.workflowId;
      btn.disabled = true;
      updateWorkflowStatus(workflowId, 'state: running');
      try {
        const result = await runLocalWorkflow(workflowId);
        const state = result.state || (result.ok ? 'completed' : 'failed');
        updateWorkflowStatus(workflowId, `state: ${state}; report: ${result.report_path_hint || 'n/a'}; refresh: ${result.refresh_hint || 'none'}`);
        const out = document.getElementById('out');
        if (out) out.textContent = JSON.stringify(result, null, 2);
      } catch (err) {
        updateWorkflowStatus(workflowId, `state: failed; ${String(err)}`);
      } finally {
        btn.disabled = false;
      }
    });
  });
}

function bindSourceButtons() {
  document.querySelectorAll('.source-status-button').forEach(btn => {
    btn.addEventListener('click', async () => {
      const result = await invokeCommand('source_status', {});
      const out = document.getElementById('out');
      if (out) out.textContent = JSON.stringify(result, null, 2);
      updateSourceStatus(btn.dataset.sourceId, 'state: status refreshed');
    });
  });
  document.querySelectorAll('.source-cache-button').forEach(btn => {
    btn.addEventListener('click', async () => {
      const sourceId = btn.dataset.sourceId;
      updateSourceStatus(sourceId, 'state: caching');
      const result = await invokeCommand('cache_source_sample', { sourceId });
      const out = document.getElementById('out');
      if (out) out.textContent = JSON.stringify(result, null, 2);
      updateSourceStatus(sourceId, `state: ${result.ok ? 'cached' : 'failed'}`);
    });
  });
}

function bindPromotionButton() {
  document.getElementById('promote-review-decisions')?.addEventListener('click', async () => {
    const result = await invokeCommand('promote_review_decisions', {});
    const out = document.getElementById('out');
    if (out) out.textContent = JSON.stringify(result, null, 2);
    const status = document.getElementById('promotion-status');
    if (status) status.textContent = `state: ${result.ok ? 'written' : 'failed'}; candidates: ${result.candidate_rows ?? 0}`;
  });
}

export async function loadAndRenderSettings(pathHint = null) {
  const payload = await loadAppSettings(pathHint);
  const data = unwrapSettingsPayload(payload);
  renderSettings(data);
  return { ok: true, loaded: data.version, bridge_mode: payload?.mode || 'browser_fallback', workflows: (data.local_workflows || []).map(w => w.workflow_id) };
}

export function currentSettingsState() {
  return settingsState;
}
