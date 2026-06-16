import { loadReviewReport, saveReviewDecision } from './api.js';
import { esc, table } from './dashboard.js';

let localReviewState = new Map();

function setHtml(id, html) {
  const el = document.getElementById(id);
  if (el) el.innerHTML = html;
}

function unwrapReviewPayload(payload) {
  if (payload && payload.review_json) return payload.review_json;
  return payload;
}

function actionButtons(reviewType, reviewId) {
  return `
    <button class="review-action" data-review-type="${esc(reviewType)}" data-review-id="${esc(reviewId)}" data-decision="accepted">Accept</button>
    <button class="review-action" data-review-type="${esc(reviewType)}" data-review-id="${esc(reviewId)}" data-decision="rejected">Reject</button>
    <button class="review-action" data-review-type="${esc(reviewType)}" data-review-id="${esc(reviewId)}" data-decision="needs_review">Needs review</button>
  `;
}

function withLocalDecision(row) {
  const id = row.review_id || row.raw_name || row.source_ref;
  return { ...row, local_decision: localReviewState.get(id) || row.decision || 'needs_review' };
}

export async function applyLocalReviewAction(reviewType, reviewId, decision) {
  localReviewState.set(reviewId, decision);
  document.querySelectorAll(`[data-local-decision-for="${CSS.escape(reviewId)}"]`).forEach(el => {
    el.textContent = decision;
  });
  const result = await saveReviewDecision(reviewType, reviewId, decision, 'desktop review button');
  const out = document.getElementById('out');
  if (out) out.textContent = JSON.stringify(result, null, 2);
}

function bindLocalReviewActions(root = document) {
  root.querySelectorAll('.review-action').forEach(btn => {
    btn.addEventListener('click', () => {
      applyLocalReviewAction(btn.dataset.reviewType, btn.dataset.reviewId, btn.dataset.decision);
    });
  });
}

function renderUnknownRows(rows) {
  if (!rows || rows.length === 0) return '<div class="muted">No unknown rows.</div>';
  return rows.map(row => {
    const r = withLocalDecision(row);
    const reviewType = r.review_type || 'unknown_market';
    return `
      <div class="card review-card">
        <h3>${esc(r.raw_name)}</h3>
        <p><span class="pill">${esc(r.provider_id)}</span> <span class="pill">${esc(r.source_name)}</span></p>
        <p><b>Selection:</b> ${esc(r.raw_selection)}</p>
        <p><b>Candidate:</b> ${esc(r.candidate_id || 'none yet')} · <b>Confidence:</b> ${esc(r.confidence)}</p>
        <p><b>Decision:</b> <span data-local-decision-for="${esc(r.review_id)}">${esc(r.local_decision)}</span></p>
        <p class="muted">${esc(r.reason)}</p>
        <div>${actionButtons(reviewType, r.review_id)}</div>
      </div>
    `;
  }).join('');
}

function renderIdentityQueue(rows) {
  if (!rows || rows.length === 0) return '<div class="muted">No identity review rows.</div>';
  return rows.map(row => {
    const r = withLocalDecision(row);
    const reviewType = r.review_type || 'provider_identity';
    return `
      <div class="card review-card">
        <h3>${esc(r.raw_name)}</h3>
        <p><span class="pill">${esc(r.canonical_entity_type)}</span> <span class="pill">${esc(r.provider_id)}</span></p>
        <p><b>Candidate:</b> ${esc(r.candidate_canonical_id)} · <b>Confidence:</b> ${esc(r.confidence)}</p>
        <p><b>Decision:</b> <span data-local-decision-for="${esc(r.review_id)}">${esc(r.local_decision)}</span></p>
        <p class="muted">${esc(r.reason)}</p>
        <div>${actionButtons(reviewType, r.review_id)}</div>
      </div>
    `;
  }).join('');
}

export function renderReviewData(data) {
  const sections = data.sections || {};
  const unknown = sections.unknown_market_review || [];
  const identity = sections.provider_identity_review || {};
  const reviewQueue = identity.review_queue || [];
  const candidatePreview = identity.candidate_preview || [];

  const unknownHtml = `
    <h3>Unknown market review</h3>
    <p class="muted">Persisted locally to the review decision store. Production alias promotion still comes later.</p>
    <div id="review-unknown-markets">${renderUnknownRows(unknown)}</div>
  `;
  setHtml('page-unknowns', unknownHtml);
  setHtml('review-unknown-markets-panel', unknownHtml);

  const identityHtml = `
    <h3>Provider identity review</h3>
    <p class="muted">Persisted locally to the review decision store. Ambiguous rows are not auto-merged.</p>
    <div id="review-identity-candidates">${renderIdentityQueue(reviewQueue)}</div>
    <h3>Auto-match candidate preview</h3>
    ${table(candidatePreview, [
      { key: 'canonical_entity_type', label: 'Type' },
      { key: 'canonical_id', label: 'Canonical' },
      { key: 'provider_id', label: 'Provider' },
      { key: 'raw_name', label: 'Raw name' },
      { key: 'confidence', label: 'Confidence' },
      { key: 'decision', label: 'Decision' }
    ])}
  `;
  setHtml('page-identity-review', identityHtml);
  setHtml('review-identity-candidates-panel', identityHtml);
  bindLocalReviewActions();
}

export async function loadAndRenderReviews(pathHint = null) {
  const payload = await loadReviewReport(pathHint);
  const data = unwrapReviewPayload(payload);
  renderReviewData(data);
  return { ok: true, loaded: data.version, bridge_mode: payload?.mode || 'browser_fallback', sections: Object.keys(data.sections || {}) };
}
