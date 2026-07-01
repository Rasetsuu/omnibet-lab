use omnibet_lab_core::{
    build_feature_count_gate_report_v921, write_feature_count_gate_report_v921, FeatureCountGateConfigV921,
};
use std::env;
use std::fs;
use std::path::PathBuf;

fn main() {
    if let Err(err) = run() {
        eprintln!("omnibet-feature-count-gate failed: {err}");
        std::process::exit(1);
    }
}

fn run() -> Result<(), String> {
    let args: Vec<String> = env::args().collect();
    if args.iter().any(|arg| arg == "--help" || arg == "-h") {
        print_help();
        return Ok(());
    }
    let matches_path = required_arg(&args, "--matches")?;
    let out_path = optional_arg(&args, "--out").unwrap_or_else(|| "reports/feature_counts.json".to_string());
    let min_required_rows = optional_arg(&args, "--min-rows")
        .as_deref()
        .unwrap_or("200")
        .parse::<usize>()
        .map_err(|e| format!("invalid --min-rows: {e}"))?;
    let source_label = optional_arg(&args, "--source-label").unwrap_or_else(|| matches_path.clone());

    let text = fs::read_to_string(&matches_path).map_err(|e| format!("read {matches_path}: {e}"))?;
    let config = FeatureCountGateConfigV921 {
        min_required_rows,
        source_label,
    };
    let report = build_feature_count_gate_report_v921(&text, &config)?;
    write_feature_count_gate_report_v921(&report, &PathBuf::from(out_path))?;
    println!(
        "{}",
        serde_json::to_string_pretty(&report).map_err(|e| format!("serialize report: {e}"))?
    );
    Ok(())
}

fn required_arg(args: &[String], name: &str) -> Result<String, String> {
    optional_arg(args, name).ok_or_else(|| format!("missing required argument {name}; run --help"))
}

fn optional_arg(args: &[String], name: &str) -> Option<String> {
    let mut iter = args.iter();
    while let Some(arg) = iter.next() {
        if arg == name {
            return iter.next().cloned();
        }
        if let Some(rest) = arg.strip_prefix(&format!("{name}=")) {
            return Some(rest.to_string());
        }
    }
    None
}

fn print_help() {
    println!(
        "Usage: omnibet-feature-count-gate --matches <matches.jsonl> [--out reports/feature_counts.json] [--min-rows 200] [--source-label canonical_matches]\n\nCounts training-eligible completed match feature rows from canonical match JSONL.\nThis is only a count gate: it may allow baseline training to start, but real model readiness still requires later walk-forward evaluation and calibration."
    );
}
