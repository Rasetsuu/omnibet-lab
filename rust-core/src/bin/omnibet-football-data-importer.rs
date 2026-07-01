use omnibet_lab_core::{
    parse_football_data_csv_v891, write_football_data_import_outputs_v891, FootballDataImportConfigV891,
};
use std::env;
use std::fs;
use std::path::PathBuf;

fn main() {
    if let Err(err) = run() {
        eprintln!("omnibet-football-data-importer failed: {err}");
        std::process::exit(1);
    }
}

fn run() -> Result<(), String> {
    let args: Vec<String> = env::args().collect();
    if args.iter().any(|arg| arg == "--help" || arg == "-h") {
        print_help();
        return Ok(());
    }
    let input = required_arg(&args, "--input")?;
    let competition = required_arg(&args, "--competition")?;
    let season = required_arg(&args, "--season")?;
    let out = required_arg(&args, "--out")?;
    let source_id = optional_arg(&args, "--source-id").unwrap_or_else(|| "football_data_co_uk".to_string());

    let text = fs::read_to_string(&input).map_err(|e| format!("read {input}: {e}"))?;
    let config = FootballDataImportConfigV891 {
        source_id,
        competition_id: competition,
        season_id: season,
    };
    let output = parse_football_data_csv_v891(&text, &config)?;
    write_football_data_import_outputs_v891(&output, &PathBuf::from(out))?;
    println!(
        "{}",
        serde_json::to_string_pretty(&output.report).map_err(|e| format!("serialize report: {e}"))?
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
        "Usage: omnibet-football-data-importer --input <csv> --competition <id> --season <id> --out <dir> [--source-id football_data_co_uk]\n\nImports historical Football-Data style CSV rows into offline canonical JSONL outputs.\nNo live provider calls are made and ready_for_training remains false until later feature/eval gates pass."
    );
}
