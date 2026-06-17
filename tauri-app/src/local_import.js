function esc(value) {
  return String(value ?? '').replace(/[&<>"]/g, ch => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[ch]));
}

function splitCsvLine(line) {
  const out = [];
  let current = '';
  let quoted = false;
  for (let i = 0; i < line.length; i += 1) {
    const ch = line[i];
    if (ch === '"') {
      quoted = !quoted;
    } else if (ch === ',' && !quoted) {
      out.push(current.trim());
      current = '';
    } else {
      current += ch;
    }
  }
  out.push(current.trim());
  return out;
}

export function parseCsvRows(text) {
  const lines = text.split(/\r?\n/).map(line => line.trim()).filter(Boolean);
  if (!lines.length) return [];
  const headers = splitCsvLine(lines[0]).map(h => h.trim());
  return lines.slice(1).map(line => {
    const values = splitCsvLine(line);
    const row = {};
    headers.forEach((header, idx) => { row[header] = values[idx] ?? ''; });
    return row;
  });
}

export function parseJsonRows(text) {
  const trimmed = text.trim();
  if (!trimmed) return [];
  if (trimmed.startsWith('[')) return JSON.parse(trimmed);
  return trimmed.split(/\r?\n/).filter(Boolean).map(line => JSON.parse(line));
}

export function parseLocalImportText(text, filename = '') {
  const lower = filename.toLowerCase();
  if (lower.endsWith('.csv')) return parseCsvRows(text);
  if (lower.endsWith('.json') || lower.endsWith('.jsonl')) return parseJsonRows(text);
  try {
    return parseJsonRows(text);
  } catch (_) {
    return parseCsvRows(text);
  }
}

export function normalizeImportRows(rows) {
  return rows.map((row, idx) => ({
    row_index: idx,
    source_id: row.source_id || row.source || 'local_import',
    competition_id: row.competition_id || row.competition || row.league || '',
    season: Number(row.season || row.year || 0),
    source_event_id: row.source_event_id || row.event_id || row.id || `local:${idx}`,
    kickoff_utc: row.kickoff_utc || row.date || row.kickoff || '',
    home_name: row.home_name || row.home || row.home_team || '',
    away_name: row.away_name || row.away || row.away_team || '',
    home_score: row.home_score === '' || row.home_score == null ? null : Number(row.home_score ?? row.home_goals),
    away_score: row.away_score === '' || row.away_score == null ? null : Number(row.away_score ?? row.away_goals),
  }));
}

export function integrityReport(rows) {
  const required = ['competition_id', 'season', 'source_event_id', 'home_name', 'away_name'];
  const seen = new Set();
  const duplicates = [];
  const missing = [];
  rows.forEach(row => {
    const key = `${row.source_id}:${row.source_event_id}`;
    if (seen.has(key)) duplicates.push(key);
    seen.add(key);
    const missingFields = required.filter(field => row[field] === '' || row[field] == null || Number.isNaN(row[field]));
    if (missingFields.length) missing.push({ row_index: row.row_index, missing_fields: missingFields });
  });
  return {
    ok: duplicates.length === 0 && missing.length === 0,
    input_rows: rows.length,
    duplicate_rows: duplicates,
    missing_rows: missing,
    trainable_rows: rows.filter(row => row.home_score !== null && row.away_score !== null && !Number.isNaN(row.home_score) && !Number.isNaN(row.away_score)).length,
  };
}

export function buildLocalImportBundle(rows, filename = 'local-import') {
  const integrity = integrityReport(rows);
  return {
    ok: integrity.ok,
    schema: 'omnibet.local_import_bundle.v141_v148',
    source_filename: filename,
    created_by: 'desktop_local_import_preview',
    row_count: rows.length,
    integrity,
    rows,
    policy: { local_only: true, no_credentials: true },
  };
}

function renderPreview(bundle) {
  const preview = bundle.rows.slice(0, 8).map(row => `
    <tr>
      <td>${esc(row.competition_id)}</td>
      <td>${esc(row.season)}</td>
      <td>${esc(row.home_name)}</td>
      <td>${esc(row.away_name)}</td>
      <td>${esc(row.home_score)}-${esc(row.away_score)}</td>
    </tr>
  `).join('');
  return `
    <h3>v143 Row preview</h3>
    <table class="mini-table">
      <thead><tr><th>Competition</th><th>Season</th><th>Home</th><th>Away</th><th>Score</th></tr></thead>
      <tbody>${preview || '<tr><td colspan="5" class="muted">No rows.</td></tr>'}</tbody>
    </table>
  `;
}

function renderIntegrity(bundle) {
  const report = bundle.integrity;
  return `
    <h3>v144 Integrity</h3>
    <div class="stat-row"><span>Status</span><strong>${report.ok ? 'OK' : 'Needs review'}</strong></div>
    <div class="stat-row"><span>Input rows</span><strong>${esc(report.input_rows)}</strong></div>
    <div class="stat-row"><span>Trainable rows</span><strong>${esc(report.trainable_rows)}</strong></div>
    <div class="stat-row"><span>Duplicates</span><strong>${esc(report.duplicate_rows.length)}</strong></div>
    <div class="stat-row"><span>Missing rows</span><strong>${esc(report.missing_rows.length)}</strong></div>
  `;
}

function renderBundle(bundle) {
  return `
    <h3>v145 Import bundle</h3>
    <div class="stat-row"><span>Schema</span><strong>${esc(bundle.schema)}</strong></div>
    <div class="stat-row"><span>Rows</span><strong>${esc(bundle.row_count)}</strong></div>
    <div class="stat-row"><span>Source</span><strong>${esc(bundle.source_filename)}</strong></div>
  `;
}

function downloadBundle(bundle) {
  const blob = new Blob([JSON.stringify(bundle, null, 2)], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = 'omnibet-local-import-bundle.json';
  a.click();
  URL.revokeObjectURL(url);
}

export function renderLocalImportBundle(bundle) {
  const preview = document.getElementById('local-import-preview');
  const integrity = document.getElementById('local-import-integrity');
  const bundlePanel = document.getElementById('local-import-bundle');
  if (preview) preview.innerHTML = renderPreview(bundle);
  if (integrity) integrity.innerHTML = renderIntegrity(bundle);
  if (bundlePanel) bundlePanel.innerHTML = renderBundle(bundle);
}

export async function runLocalImportPreview(file) {
  if (!file) throw new Error('Choose a local CSV/JSON/JSONL file first.');
  const text = await file.text();
  const rawRows = parseLocalImportText(text, file.name);
  const normalizedRows = normalizeImportRows(rawRows);
  const bundle = buildLocalImportBundle(normalizedRows, file.name);
  window.__omnibetLastLocalImportBundle = bundle;
  renderLocalImportBundle(bundle);
  return bundle;
}

export function exportLocalImportBundle() {
  const bundle = window.__omnibetLastLocalImportBundle;
  if (!bundle) throw new Error('Run local import preview first.');
  downloadBundle(bundle);
  return { ok: true, exported: true, rows: bundle.row_count };
}
