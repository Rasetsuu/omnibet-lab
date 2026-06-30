use omnibet_lab_core::build_pack_from_sample_contents_v651;
use std::env;
use std::fs;
use std::path::Path;

const DEFAULT_CSV_PATH: &str = "data/source_samples/v591_v620/football_data_sample.csv";
const DEFAULT_JSON_MATCH_PATH: &str = "data/source_samples/v591_v620/openfootball_sample.json";
const DEFAULT_EVENT_PATH: &str = "data/source_samples/v591_v620/statsbomb_events_sample.json";
const DEFAULT_OUT_PATH: &str = "reports/rust_sample_pack_v681_v710.json";

fn escape_json(value: &str) -> String {
    value
        .replace('\\', "\\\\")
        .replace('"', "\\\"")
        .replace('\n', "\\n")
        .replace('\r', "\\r")
        .replace('\t', "\\t")
}

fn arg_or_default(args: &[String], index: usize, default_value: &str) -> String {
    args.get(index)
        .cloned()
        .unwrap_or_else(|| default_value.to_owned())
}

fn read_text(path: &str) -> Result<String, String> {
    fs::read_to_string(path).map_err(|err| format!("failed to read {path}: {err}"))
}

fn write_report(path: &str, report: &str) -> Result<(), String> {
    if let Some(parent) = Path::new(path).parent() {
        if !parent.as_os_str().is_empty() {
            fs::create_dir_all(parent).map_err(|err| format!("failed to create {}: {err}", parent.display()))?;
        }
    }
    fs::write(path, report).map_err(|err| format!("failed to write {path}: {err}"))
}

fn run() -> Result<(), String> {
    let args: Vec<String> = env::args().collect();
    let csv_path = arg_or_default(&args, 1, DEFAULT_CSV_PATH);
    let json_match_path = arg_or_default(&args, 2, DEFAULT_JSON_MATCH_PATH);
    let event_path = arg_or_default(&args, 3, DEFAULT_EVENT_PATH);
    let out_path = arg_or_default(&args, 4, DEFAULT_OUT_PATH);

    let csv_content = read_text(&csv_path)?;
    let json_match_content = read_text(&json_match_path)?;
    let event_content = read_text(&event_path)?;
    let pack = build_pack_from_sample_contents_v651(&csv_content, &json_match_content, &event_content)?;

    let report = format!(
        "{{\n  \"schema\": \"omnibet.rust_sample_pack_report.v681_v710\",\n  \"ok\": true,\n  \"ready_for_real_model\": {},\n  \"inputs\": {{\n    \"csv\": \"{}\",\n    \"json_match\": \"{}\",\n    \"events\": \"{}\"\n  }},\n  \"counts\": {{\n    \"fixtures\": {},\n    \"results\": {},\n    \"events\": {}\n  }}\n}}\n",
        if pack.ready_for_real_model { "true" } else { "false" },
        escape_json(&csv_path),
        escape_json(&json_match_path),
        escape_json(&event_path),
        pack.fixtures.len(),
        pack.results.len(),
        pack.events.len(),
    );
    write_report(&out_path, &report)?;
    println!("{report}");
    Ok(())
}

fn main() {
    if let Err(err) = run() {
        eprintln!("omnibet-sample-pack-runner failed: {err}");
        std::process::exit(1);
    }
}
