use omnibet_lab_core::backtest_linear_model;
use serde_json::json;
use std::env;
use std::path::PathBuf;

fn usage() {
    eprintln!(
        "Usage:\n  omnibet-model backtest <pack_dir> <model_json> [min_train] [--rows]"
    );
}

fn main() {
    let mut args = env::args().skip(1);
    let Some(cmd) = args.next() else {
        usage();
        std::process::exit(2);
    };

    let output = match cmd.as_str() {
        "backtest" => {
            let Some(pack_dir) = args.next() else {
                usage();
                std::process::exit(2);
            };
            let Some(model_json) = args.next() else {
                usage();
                std::process::exit(2);
            };
            let mut min_train = 1usize;
            let mut include_rows = false;
            for arg in args {
                if arg == "--rows" {
                    include_rows = true;
                } else if let Ok(v) = arg.parse::<usize>() {
                    min_train = v;
                }
            }
            match backtest_linear_model(&PathBuf::from(pack_dir), &PathBuf::from(model_json), min_train, include_rows) {
                Ok(report) => json!({"ok": true, "linear_model_backtest": report}),
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
