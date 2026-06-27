function esc(value) {
  return String(value ?? '').replace(/[&<>"]/g, ch => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[ch]));
}

async function loadJson(path) {
  const response = await fetch(path);
  if (!response.ok) throw new Error(`failed to load ${path}: ${response.status}`);
  return response.json();
}

function list(items = []) {
  if (!items.length) return '<span class="muted">None</span>';
  return `<ul>${items.map(item => `<li>${esc(item)}</li>`).join('')}</ul>`;
}

function renderSummary(payload) {
  const panel = document.getElementById('storage-writers-summary');
  if (!panel) return;
  const s = payload.summary || {};
  panel.innerHTML = `
    <h3>v311-v320 Rust Storage V2 writers</h3>
    <p class="warn">Local preview writers only. Real storage promotion remains gated.</p>
    <table>
      <tr><th>Metric</th><th>Value</th></tr>
      <tr><td>Writer targets</td><td>${esc(s.writer_targets)}</td></tr>
      <tr><td>Implemented now</td><td>${esc(s.implemented_now)}</td></tr>
      <tr><td>Manifest-only now</td><td>${esc(s.manifest_only_now)}</td></tr>
      <tr><td>Sample manifests</td><td>${esc(s.sample_manifests)}</td></tr>
      <tr><td>Ready for real storage</td><td>${esc(s.ready_for_real_storage)}</td></tr>
    </table>
  `;
}

function renderTargets(payload) {
  const panel = document.getElementById('storage-writers-targets');
  if (!panel) return;
  const rows = payload.writer_rows || [];
  panel.innerHTML = `
    <h3>Writer targets</h3>
    <table>
      <tr><th>Writer</th><th>Layer</th><th>Codec</th><th>Status</th><th>Next action</th></tr>
      ${rows.map(row => `
        <tr>
          <td>${esc(row.writer_id)}</td>
          <td>${esc(row.layer)}</td>
          <td>${esc(row.codec)}</td>
          <td>${esc(row.status)}</td>
          <td>${esc(row.next_action)}</td>
        </tr>
      `).join('')}
    </table>
  `;
}

function renderManifests(payload) {
  const panel = document.getElementById('storage-writers-manifests');
  if (!panel) return;
  const rows = payload.manifest_rows || [];
  panel.innerHTML = `
    <h3>Table manifests</h3>
    <table>
      <tr><th>Table</th><th>Codec</th><th>Rows</th><th>Compressed bytes</th><th>Retention</th><th>Promotion</th></tr>
      ${rows.map(row => `
        <tr>
          <td>${esc(row.table)}</td>
          <td>${esc(row.codec)}</td>
          <td>${esc(row.row_count)}</td>
          <td>${esc(row.compressed_bytes)}</td>
          <td>${esc(row.retention_policy)}</td>
          <td>${esc(row.promotion_state)}</td>
        </tr>
      `).join('')}
    </table>
  `;
}

function renderRetention(payload) {
  const panel = document.getElementById('storage-writers-retention');
  if (!panel) return;
  const gate = payload.retention_gate || {};
  panel.innerHTML = `
    <h3>Retention gate</h3>
    <p class="warn">Bronze delete is blocked until promotion is verified and hashes/rows match.</p>
    <table>
      <tr><th>Field</th><th>Value</th></tr>
      <tr><td>Bronze can delete</td><td>${esc(gate.bronze_can_delete)}</td></tr>
      <tr><td>Reason</td><td>${esc(gate.reason)}</td></tr>
    </table>
    <h4>Requires</h4>
    ${list(gate.requires)}
  `;
}

function renderNext(payload) {
  const panel = document.getElementById('storage-writers-next');
  if (!panel) return;
  panel.innerHTML = `
    <h3>Next</h3>
    <p>${esc(payload.next_phase)}</p>
  `;
}

export function renderStorageWritersStatus(payload) {
  renderSummary(payload);
  renderTargets(payload);
  renderManifests(payload);
  renderRetention(payload);
  renderNext(payload);
  return payload;
}

export async function loadAndRenderStorageWritersStatus(path = 'tauri-app/src/storage-writers.sample.json') {
  const payload = await loadJson(path);
  return renderStorageWritersStatus(payload);
}
