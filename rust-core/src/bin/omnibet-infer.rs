use omnibet_lab_core::{backtest_from_pack, backtest_gold_from_pack, compare_models_from_pack, predict_from_pack, read_gold_match_features, read_matches};
use serde_json::json;
use std::env;
use std::path::PathBuf;

fn usage() {
    eprintln!(
        "Usage:
  omnibet-infer inspect <pack_dir> [limit]
  omnibet-infer predict <pack_dir> <home_team> <away_team>
  omnibet-infer backtest <pack_dir> [min_train] [--rows]
  omnibet-infer backtest-gold <pack_dir> [--rows]
  omnibet-infer compare <pack_dir> [min_train]"
    );
}

fn main() {
    let mut args = env::args().skip(1);
    let Some(cmd) = args.next() else {
        usage();
        std::process::exit(2);
    };
    let Some(pack_dir) = args.next() else {
        usage();
        std::process::exit(2);
    };
    let pack_dir = PathBuf::from(pack_dir);

    let output = match cmd.as_str() {
        "inspect" => {
            let limit = args.next().and_then(|x| x.parse::<usize>().ok()).unwrap_or(3);
            let matches = read_matches(&pack_dir, limit);
            let gold = read_gold_match_features(&pack_dir, limit);
            match (matches, gold) {
                (Ok(m), Ok(g)) => json!({
                    "ok": true,
                    "matches_norm_sample_rows": m,
                    "gold_match_features_sample_rows": g,
                }),
                (Err(e), _) | (_, Err(e)) => json!({"ok": false, "error": e}),
            }
        }
        "predict" => {
            let Some(home) = args.next() else {
                usage();
                std::process::exit(2);
            };
            let Some(away) = args.next() else {
                usage();
                std::process::exit(2);
            };
            match predict_from_pack(&pack_dir, &home, &away) {
                Ok(pred) => json!({"ok": true, "prediction": pred}),
                Err(e) => json!({"ok": false, "error": e}),
            }
        }

        "backtest" => {
            let min_train = args
                .next()
                .and_then(|x| x.parse::<usize>().ok())
                .unwrap_or(80);
            let include_rows = args.any(|x| x == "--rows");
            match backtest_from_pack(&pack_dir, min_train, include_rows) {
                Ok(summary) => json!({"ok": true, "backtest": summary}),
                Err(e) => json!({"ok": false, "error": e}),
            }
        }

        "backtest-gold" => {
            let mut min_train = 80usize;
            let mut include_rows = false;
            for arg in args {
                if arg == "--rows" {
                    include_rows = true;
                } else if let Ok(v) = arg.parse::<usize>() {
                    min_train = v;
                }
            }
            match backtest_gold_from_pack(&pack_dir, min_train, include_rows) {
                Ok(summary) => json!({"ok": true, "backtest": summary}),
                Err(e) => json!({"ok": false, "error": e}),
            }
        }
        "compare" => {
            let min_train = args
                .next()
                .and_then(|x| x.parse::<usize>().ok())
                .unwrap_or(80);
            match compare_models_from_pack(&pack_dir, min_train) {
                Ok(summary) => json!({"ok": true, "comparison": summary}),
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
