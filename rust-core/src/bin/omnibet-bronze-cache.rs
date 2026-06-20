use omnibet_lab_core::{
    parse_api_football_live_state_sample, parse_the_odds_api_event_markets_sample,
    verify_bronze_snapshot_cache, write_bronze_snapshot_cache, BronzeSnapshotRows,
};
use serde::Serialize;
use std::env;
use std::fs;
use std::path::PathBuf;

#[derive(Debug, Serialize)]
struct BronzeCacheCliReport {
    ok: bool,
    schema: String,
    output_dir: String,
    total_rows: u64,
    tables: usize,
    cache_id: String,
    credential_values_stored: bool,
    network_calls_performed: bool,
    verify_errors: Vec<String>,
}

fn main() {
    if let Err(err) = run() {
        eprintln!("omnibet-bronze-cache error: {}", err);
        std::process::exit(1);
    }
}

fn run() -> Result<(), String> {
    let args: Vec<String> = env::args().collect();
    if args.len() < 2 || args.iter().any(|arg| arg == "--help" || arg == "-h") {
        print_help(&args[0]);
        return Ok(());
    }

    let out_dir = value_after(&args, "--out")
        .map(PathBuf::from)
        .unwrap_or_else(|| PathBuf::from("build/bronze_cache/v236_offline_samples"));
    let cache_id = value_after(&args, "--cache-id")
        .unwrap_or_else(|| "v236_offline_provider_samples".to_string());
    let created_at = value_after(&args, "--created-at")
        .unwrap_or_else(|| "2026-06-20T00:00:00Z".to_string());
    let odds_path = value_after(&args, "--odds-sample")
        .map(PathBuf::from)
        .unwrap_or_else(|| PathBuf::from("data/samples/the_odds_api_event_markets_sample.json"));
    let football_path = value_after(&args, "--football-sample")
        .map(PathBuf::from)
        .unwrap_or_else(|| PathBuf::from("data/samples/api_football_live_state_sample.json"));

    let odds_text = fs::read_to_string(&odds_path)
        .map_err(|e| format!("read odds sample {}: {}", odds_path.display(), e))?;
    let football_text = fs::read_to_string(&football_path)
        .map_err(|e| format!("read football sample {}: {}", football_path.display(), e))?;

    let odds = parse_the_odds_api_event_markets_sample(&odds_text, "2026-06-16T18:02:00Z")?;
    let football = parse_api_football_live_state_sample(&football_text, "2026-06-16T22:00:00Z")?;
    let rows = BronzeSnapshotRows::from_provider_samples(&odds, &football);
    let manifest = write_bronze_snapshot_cache(&rows, &out_dir, &cache_id, &created_at)?;
    let verify = verify_bronze_snapshot_cache(&out_dir)?;

    let report = BronzeCacheCliReport {
        ok: verify.ok,
        schema: manifest.schema,
        output_dir: out_dir.display().to_string(),
        total_rows: manifest.total_rows,
        tables: manifest.tables.len(),
        cache_id: manifest.cache_id,
        credential_values_stored: manifest.credential_values_stored,
        network_calls_performed: manifest.network_calls_performed,
        verify_errors: verify.errors,
    };
    println!(
        "{}",
        serde_json::to_string_pretty(&report).map_err(|e| format!("serialize CLI report: {}", e))?
    );
    if !report.ok {
        return Err("bronze cache verification failed".to_string());
    }
    Ok(())
}

fn value_after(args: &[String], flag: &str) -> Option<String> {
    args.windows(2)
        .find(|pair| pair[0] == flag)
        .map(|pair| pair[1].clone())
}

fn print_help(bin: &str) {
    println!(
        "Usage: {} --out build/bronze_cache/v236_offline_samples [--cache-id ID] [--created-at ISO] [--odds-sample PATH] [--football-sample PATH]",
        bin
    );
    println!("Writes an offline JSONL.GZ bronze snapshot cache from saved provider samples.");
}
