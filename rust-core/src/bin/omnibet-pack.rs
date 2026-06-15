use omnibet_lab_core::{load_manifest, table_rows_as_json, verify_pack};
use serde_json::json;
use std::env;
use std::path::PathBuf;

fn usage() {
    eprintln!(
        "Usage:
  omnibet-pack verify <pack_dir>
  omnibet-pack summary <pack_dir>
  omnibet-pack head <pack_dir> <table> [limit]"
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

    let result = match cmd.as_str() {
        "verify" => match verify_pack(&pack_dir) {
            Ok(res) => json!(res),
            Err(e) => json!({"ok": false, "error": e}),
        },
        "summary" => match load_manifest(&pack_dir) {
            Ok(m) => json!({
                "ok": true,
                "pack_name": m.pack_name,
                "sport": m.sport,
                "format": m.format,
                "table_count": m.tables.len(),
                "total_rows": m.total_rows,
                "total_compressed_bytes": m.total_compressed_bytes,
                "overall_compression_ratio": m.overall_compression_ratio,
                "tables": m.tables.iter().map(|t| json!({
                    "table": t.table,
                    "rows": t.rows,
                    "compressed_bytes": t.compressed_bytes,
                    "compression": t.compression,
                    "compression_ratio": t.compression_ratio,
                })).collect::<Vec<_>>()
            }),
            Err(e) => json!({"ok": false, "error": e}),
        },
        "head" => {
            let Some(table) = args.next() else {
                usage();
                std::process::exit(2);
            };
            let limit: usize = args.next().and_then(|x| x.parse().ok()).unwrap_or(5);
            match table_rows_as_json(&pack_dir, &table, limit) {
                Ok(rows) => json!({"ok": true, "table": table, "rows": rows}),
                Err(e) => json!({"ok": false, "error": e}),
            }
        }
        _ => {
            usage();
            std::process::exit(2);
        }
    };

    println!("{}", serde_json::to_string_pretty(&result).unwrap());
}
