use omnibet_lab_core::{
    build_baseline_eval_report_v961, write_baseline_eval_report_v961, BaselineEvalConfigV961,
};
use std::env;
use std::fs;
use std::path::PathBuf;

fn main() {
    if let Err(err) = run() {
        eprintln!("omnibet-baseline-eval failed: {err}");
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
    let out_path = optional_arg(&args, "--out").unwrap_or_else(|| "reports/model_eval.json".to_string());
    let min_training_rows = optional_arg(&args, "--min-train")
        .as_deref()
        .unwrap_or("200")
        .parse::<usize>()
        .map_err(|e| format!("invalid --min-train: {e}"))?;
    let min_eval_rows = optional_arg(&args, "--min-eval")
        .as_deref()
        .unwrap_or("50")
        .parse::<usize>()
        .map_err(|e| format!("invalid --min-eval: {e}"))?;
    let eval_fraction = optional_arg(&args, "--eval-fraction")
        .as_deref()
        .unwrap_or("0.20")
        .parse::<f64>()
        .map_err(|e| format!("invalid --eval-fraction: {e}"))?;
    let source_label = optional_arg(&args, "--source-label").unwrap_or_else(|| matches_path.clone());

    let text = fs::read_to_string(&matches_path).map_err(|e| format!("read {matches_path}: {e}"))?;
    let config = BaselineEvalConfigV961 {
        min_training_rows,
        min_eval_rows,
        eval_fraction,
        source_label,
    };
    let report = build_baseline_eval_report_v961(&text, &config)?;
    write_baseline_eval_report_v961(&report, &PathBuf::from(out_path))?;
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
        "Usage: omnibet-baseline-eval --matches <matches.jsonl> [--out reports/model_eval.json] [--min-train 200] [--min-eval 50] [--eval-fraction 0.20] [--source-label canonical_matches]\n\nRuns a chronological expanding-frequency 1X2 baseline evaluation.\nThis is not a betting model and real_model_ready remains false until later stronger model/evaluation gates pass."
    );
}
