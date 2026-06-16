export const fallbackDashboard = {
  ok: true,
  version: 'omnibet.dashboard.v50_fallback',
  sections: {
    events: [{ canonical_event_id: 'fallback:event', home_team_name: 'France', away_team_name: 'Senegal', competition: 'FIFA World Cup', commence_time: '2026-06-16T20:00:00Z', provider_links: [], match_state: [{ match_status: 'FT', home_score: 2, away_score: 1 }] }],
    market_snapshots: [{ bookmaker: 'Example', raw_market_name: '1X2', raw_selection_name: 'France', mapped_market_id: 'football_1x2_regulation', decimal_odds: 1.5, needs_mapping: 0 }],
    unknown_market_queue: [{ raw_market_name: 'special combo unknown', raw_selection_name: 'example unknown combo' }],
    feature_snapshot_preview: { counts: [{ snapshot_stage: 'pre_event_market', rows: 14, model_eligible_rows: 13 }], rows: [] },
    settlement_report: { counts: [{ settlement_status: 'settled', settlement_result: 'win', rows: 5 }], rows: [] },
    result_accounting_report: { counts: [{ settlement_result: 'win', rows: 5, paper_units: 4.2 }], rows: [], note: 'Fallback preview.' }
  }
};

const fallback = {
  ping: () => 'browser-preview-ok',
  pack_summary: () => ({ ok: true, format: 'omnibet.pack.v1', pack_name: 'browser preview', total_rows: 0, note: 'Open in Tauri for backend command invocation.' }),
  predict_fixture: ({ homeTeam, awayTeam }) => ({ ok: true, home_team: homeTeam, away_team: awayTeam, model_trust: 0.25, decision_mode: 'PAPER_ONLY', note: 'Browser fallback preview.' }),
  value_report: ({ homeTeam, awayTeam }) => ({ ok: true, fixture: `${homeTeam} vs ${awayTeam}`, mode: 'PAPER_ONLY_OFFLINE_PREVIEW', note: 'Browser fallback preview; no recommendation output.' }),
  load_dashboard_report: async () => {
    try {
      const res = await fetch('dashboard-data.sample.json', { cache: 'no-store' });
      if (res.ok) return await res.json();
    } catch (_) {}
    return fallbackDashboard;
  }
};

export async function invokeCommand(name, args = {}) {
  if (window.__TAURI__ && window.__TAURI__.core && window.__TAURI__.core.invoke) {
    return await window.__TAURI__.core.invoke(name, args);
  }
  if (!fallback[name]) throw new Error(`No fallback command registered for ${name}`);
  return await fallback[name](args);
}

export async function loadDashboardReport(pathHint = null) {
  return await invokeCommand('load_dashboard_report', { pathHint });
}

export function fixtureTeams() {
  return {
    homeTeam: document.getElementById('home')?.value || 'Spain',
    awayTeam: document.getElementById('away')?.value || 'Cape Verde'
  };
}
