use omnibet_lab_core::value_report_from_pack;
use serde_json::json;
use std::env;
use std::path::PathBuf;

fn usage() {
    eprintln!(
        "Usage:
  omnibet-value report <pack_dir> <home_team> <away_team> <odds_csv> [model_trust_0_to_1]"
    );
}

fn main() {
    let mut args = env::args().skip(1);
    let Some(cmd) = args.next() else {
        usage();
        std::process::exit(2);
    };

    let output = match cmd.as_str() {
        "report" => {
            let Some(pack_dir) = args.next() else {
                usage();
                std::process::exit(2);
            };
            let Some(home) = args.next() else {
                usage();
                std::process::exit(2);
            };
            let Some(away) = args.next() else {
                usage();
                std::process::exit(2);
            };
            let Some(odds_csv) = args.next() else {
                usage();
                std::process::exit(2);
            };

            let model_trust = args
                .next()
                .and_then(|x| x.parse::<f64>().ok())
                .unwrap_or(0.25);

            match value_report_from_pack(
                &PathBuf::from(pack_dir),
                &home,
                &away,
                &PathBuf::from(odds_csv),
                model_trust,
            ) {
                Ok(report) => json!({"ok": true, "report": report}),
                Err(e) => json!({"ok": false, "error": e}),
            }
        }
        _ => {
            usage();
            std::process::exit(2);
        }
    };

    println!("{}", serde_json::to_string_pretty(&output).unwrap());
}
