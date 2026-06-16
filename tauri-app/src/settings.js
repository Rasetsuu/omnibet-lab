import { loadAppSettings, runLocalWorkflow } from './api.js';
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
    { key: 'provider_id', label: 'Provider' },
    { key: 'enabled', label: 'Enabled' },
    { key: 'api_key_env', label: 'Env key name' },
    { key: 'key_status_only', label: 'Key status only' },
    { key: 'live_calls_in_ci', label: 'Live calls in CI' }
  ]);
}

function renderWorkflowButtons(workflows = []) {
  if (!workflows.length) return '<div class="muted">No workflows configured.</div>';
  return workflows.map(w => `
    <div class="card workflow-card">
      <h3>${esc(w.label)}</h3>
      <p class="muted">${esc(w.description)}</p>
      <p>${badge(w.workflow_id)}</p>
      <button class="local-workflow-button" data-workflow-id="${esc(w.workflow_id)}">Run local workflow</button>
    </div>
  `).join('');
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
  setHtml('settings-providers', `<h3>Providers</h3><p class="muted">API key values are never displayed here; only env var names/status are shown.</p>${renderProviderStatus(data.providers || [])}`);
  setHtml('settings-safety', `<h3>Safety</h3>${table(safetyRows, [{ key: 'key', label: 'Rule' }, { key: 'value', label: 'Value' }])}`);
  setHtml('local-run-buttons', `<h3>Local workflow controls</h3><p class="muted">Allowlisted offline workflows only. No shell execution.</p>${renderWorkflowButtons(workflows)}`);
  bindWorkflowButtons();
}

function bindWorkflowButtons() {
  document.querySelectorAll('.local-workflow-button').forEach(btn => {
    btn.addEventListener('click', async () => {
      const workflowId = btn.dataset.workflowId;
      const result = await runLocalWorkflow(workflowId);
      const out = document.getElementById('out');
      if (out) out.textContent = JSON.stringify(result, null, 2);
    });
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
