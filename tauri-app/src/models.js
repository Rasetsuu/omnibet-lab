import { esc, table } from './dashboard.js';

function setHtml(id, html) {
  const el = document.getElementById(id);
  if (el) el.innerHTML = html;
}

async function loadPhase2Sample() {
  const res = await fetch('phase2-forecast.sample.json', { cache: 'no-store' });
  if (!res.ok) throw new Error(`failed to load phase2 sample: ${res.status}`);
  return await res.json();
}

function metricRows(metrics = {}) {
  return Object.entries(metrics).map(([key, value]) => ({ key, value }));
}

function renderFactorList(row) {
  return (row.top_factors || []).map(f => `<span class="pill">${esc(f.name)}=${esc(f.value)} impact=${esc(f.impact)}</span>`).join(' ');
}

export function renderPhase2Forecast(data) {
  const registry = data.registry || {};
  const backtest = data.backtest || {};
  const calibration = data.calibration || {};
  const explanation = data.explanation || {};
  const manifest = data.manifest || {};

  setHtml('model-card-panel', `
    <h3>Model registry</h3>
    <p><b>${esc(registry.model_id)}</b></p>
    <p>${esc(registry.model_family)} · target: ${esc(registry.target)}</p>
    <p>${(manifest.safety ? Object.entries(manifest.safety).map(([k, v]) => `<span class="pill">${esc(k)}=${esc(v)}</span>`).join(' ') : '')}</p>
  `);

  setHtml('model-backtest-panel', `
    <h3>Chronological backtest</h3>
    <p>Split: ${esc((backtest.split || {}).strategy)} · train rows: ${esc((backtest.split || {}).train_rows)} · test rows: ${esc((backtest.split || {}).test_rows)}</p>
    <h4>Forecast metrics</h4>
    ${table(metricRows(backtest.forecast_metrics || {}), [{ key: 'key', label: 'Metric' }, { key: 'value', label: 'Value' }])}
    <h4>Baseline metrics</h4>
    ${table(metricRows(backtest.baseline_metrics || {}), [{ key: 'key', label: 'Metric' }, { key: 'value', label: 'Value' }])}
  `);

  setHtml('model-calibration-panel', `
    <h3>Calibration</h3>
    <p>Expected calibration error: <b>${esc(calibration.expected_calibration_error)}</b></p>
    ${table(calibration.bins || [], [
      { key: 'bin', label: 'Bin' },
      { key: 'rows', label: 'Rows' },
      { key: 'avg_probability', label: 'Avg probability' },
      { key: 'observed_rate', label: 'Observed rate' },
      { key: 'gap', label: 'Gap' }
    ])}
  `);

  setHtml('model-explanations-panel', `
    <h3>Example explanations</h3>
    <p class="muted">${esc(explanation.explanation_note)}</p>
    ${(backtest.rows || []).map(r => `
      <div class="card">
        <h4>${esc(r.home)} vs ${esc(r.away)}</h4>
        <p>Forecast probability: <b>${esc(r.forecast_probability)}</b> · label: ${esc(r.label_home_win)}</p>
        <p>${renderFactorList(r)}</p>
      </div>
    `).join('')}
  `);
}

export async function loadAndRenderPhase2Forecast() {
  const data = await loadPhase2Sample();
  renderPhase2Forecast(data);
  return { ok: true, loaded: data.version, model_id: data.registry?.model_id, rows: data.manifest?.row_counts };
}
