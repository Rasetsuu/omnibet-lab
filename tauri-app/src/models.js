import { esc, table } from './dashboard.js';

function setHtml(id, html) {
  const el = document.getElementById(id);
  if (el) el.innerHTML = html;
}

async function loadModelSample() {
  const preferred = await fetch('model-lab.sample.json', { cache: 'no-store' });
  if (preferred.ok) return await preferred.json();
  const fallback = await fetch('phase2-forecast.sample.json', { cache: 'no-store' });
  if (!fallback.ok) throw new Error(`failed to load model sample: ${fallback.status}`);
  return await fallback.json();
}

function metricRows(metrics = {}) {
  return Object.entries(metrics).map(([key, value]) => ({ key, value }));
}

function renderFactorList(row) {
  return (row.top_factors || []).map(f => `<span class="pill">${esc(f.name)}=${esc(f.value)} impact=${esc(f.impact)}</span>`).join(' ');
}

function renderModelLab(data) {
  const lab = data.model_lab || {};
  const manifest = data.manifest || {};
  const stability = lab.stability || data.stability || {};
  const calibration = stability.calibration || data.calibration || {};
  const examples = lab.example_predictions || [];

  setHtml('model-card-panel', `
    <h3>Model lab</h3>
    <p><b>Best model:</b> ${esc(lab.best_model || manifest.best_model)}</p>
    <p><b>Rows:</b> history=${esc(manifest.row_counts?.history)} training=${esc(manifest.row_counts?.training)} rolling folds=${esc(manifest.row_counts?.rolling_folds)}</p>
    <p>${(manifest.safety ? Object.entries(manifest.safety).map(([k, v]) => `<span class="pill">${esc(k)}=${esc(v)}</span>`).join(' ') : '')}</p>
  `);

  setHtml('model-backtest-panel', `
    <h3>Model comparison</h3>
    ${table(lab.models || [], [
      { key: 'model_id', label: 'Model' },
      { key: 'folds', label: 'Folds' },
      { key: 'avg_brier', label: 'Avg Brier' },
      { key: 'avg_logloss', label: 'Avg log loss' },
      { key: 'avg_accuracy_at_0_5', label: 'Accuracy @ 0.5' }
    ])}
    <h3>Feature ablation</h3>
    ${table(lab.ablation || [], [
      { key: 'comparison', label: 'Comparison' },
      { key: 'brier_delta', label: 'Brier delta' },
      { key: 'logloss_delta', label: 'Log loss delta' },
      { key: 'interpretation', label: 'Interpretation' }
    ])}
  `);

  setHtml('model-calibration-panel', `
    <h3>Calibration and stability</h3>
    <p>Expected calibration error: <b>${esc(calibration.expected_calibration_error)}</b></p>
    ${table(calibration.bins || [], [
      { key: 'bin', label: 'Bin' },
      { key: 'rows', label: 'Rows' },
      { key: 'avg_probability', label: 'Avg probability' },
      { key: 'observed_rate', label: 'Observed rate' },
      { key: 'gap', label: 'Gap' }
    ])}
    <h4>Fold stability</h4>
    ${table(metricRows(stability.fold_stability || {}), [{ key: 'key', label: 'Metric' }, { key: 'value', label: 'Value' }])}
  `);

  setHtml('model-explanations-panel', `
    <h3>Example forecast explanations</h3>
    <p class="muted">Research forecasts only, not recommendations.</p>
    ${examples.map(r => `
      <div class="card">
        <h4>${esc(r.home)} vs ${esc(r.away)}</h4>
        <p>Probability: <b>${esc(r.probability ?? r.forecast_probability)}</b> · label: ${esc(r.label_home_win)}</p>
        <p>${renderFactorList(r)}</p>
      </div>
    `).join('')}
  `);
}

export function renderPhase2Forecast(data) {
  if (data.model_lab) {
    renderModelLab(data);
    return;
  }
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
  const data = await loadModelSample();
  renderPhase2Forecast(data);
  return { ok: true, loaded: data.version, best_model: data.model_lab?.best_model || data.registry?.model_id, rows: data.manifest?.row_counts };
}
