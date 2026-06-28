use serde::{Deserialize, Serialize};
use serde_json::{json, Value};
use sha2::{Digest, Sha256};
use std::env;
use std::fs;
use std::path::{Path, PathBuf};
use std::time::{SystemTime, UNIX_EPOCH};

#[derive(Debug, Clone)]
struct CliArgs {
    root: PathBuf,
    artifact_dir: PathBuf,
    out_dir: PathBuf,
    manifest_out: PathBuf,
    verification_out: PathBuf,
    run_id: String,
}

impl Default for CliArgs {
    fn default() -> Self {
        let root = PathBuf::from(".");
        Self {
            artifact_dir: root.join("reports/materialized/v421_v430"),
            out_dir: root.join("reports/materialized/v441_v450/compressed"),
            manifest_out: root.join("reports/materialized/v441_v450/materialized_storage_manifest.json"),
            verification_out: root.join("reports/materialized/v441_v450/materialized_storage_verification_report.json"),
            run_id: default_run_id(),
            root,
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
struct ArtifactRecordV441 {
    artifact_id: String,
    source_path: String,
    compressed_path: String,
    codec: String,
    source_bytes: u64,
    compressed_bytes: u64,
    sha256: String,
    compressed_sha256: String,
    compression_ratio: f64,
    status: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
struct StorageManifestV441 {
    schema: String,
    paper_only: bool,
    status: String,
    run_id: String,
    artifact_count: usize,
    artifacts: Vec<ArtifactRecordV441>,
    all_hashes_present: bool,
    all_compressed_copies_present: bool,
    ready_for_training: bool,
    trust_status: String,
    credential_values_present: bool,
    recommendation_output_present: bool,
}

fn default_run_id() -> String {
    let secs = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|d| d.as_secs())
        .unwrap_or(0);
    format!("storage_hash_run_{secs}")
}

fn sanitize_run_id(raw: &str) -> String {
    let cleaned: String = raw
        .chars()
        .map(|c| if c.is_ascii_alphanumeric() || c == '-' || c == '_' { c } else { '_' })
        .collect();
    if cleaned.is_empty() { "storage_hash_run_unknown".to_string() } else { cleaned }
}

fn parse_args() -> Result<CliArgs, String> {
    let mut args = CliArgs::default();
    let mut iter = env::args().skip(1);
    while let Some(arg) = iter.next() {
        match arg.as_str() {
            "--root" => args.root = PathBuf::from(iter.next().ok_or("--root requires a value")?),
            "--artifact-dir" => args.artifact_dir = PathBuf::from(iter.next().ok_or("--artifact-dir requires a value")?),
            "--out-dir" => args.out_dir = PathBuf::from(iter.next().ok_or("--out-dir requires a value")?),
            "--manifest-out" => args.manifest_out = PathBuf::from(iter.next().ok_or("--manifest-out requires a value")?),
            "--verification-out" => args.verification_out = PathBuf::from(iter.next().ok_or("--verification-out requires a value")?),
            "--run-id" => args.run_id = sanitize_run_id(&iter.next().ok_or("--run-id requires a value")?),
            "--help" | "-h" => {
                println!("omnibet-materialized-storage-hasher --root . --artifact-dir reports/materialized/v421_v430 --out-dir reports/materialized/v441_v450/compressed --manifest-out reports/materialized/v441_v450/materialized_storage_manifest.json --verification-out reports/materialized/v441_v450/materialized_storage_verification_report.json --run-id ci_v441_v450");
                std::process::exit(0);
            }
            other => return Err(format!("unknown argument: {other}")),
        }
    }
    Ok(args)
}

fn ensure_parent(path: &Path) -> Result<(), String> {
    if let Some(parent) = path.parent() {
        fs::create_dir_all(parent).map_err(|e| format!("create {}: {e}", parent.display()))?;
    }
    Ok(())
}

fn sha256_hex(bytes: &[u8]) -> String {
    let mut hasher = Sha256::new();
    hasher.update(bytes);
    let digest = hasher.finalize();
    digest.iter().map(|b| format!("{b:02x}")).collect::<String>()
}

fn write_json(path: &Path, payload: &Value) -> Result<(), String> {
    ensure_parent(path)?;
    let text = serde_json::to_string_pretty(payload).map_err(|e| format!("serialize {}: {e}", path.display()))?;
    fs::write(path, format!("{}\n", text)).map_err(|e| format!("write {}: {e}", path.display()))
}

fn artifact_files() -> Vec<&'static str> {
    vec![
        "bronze_fixtures.generated.json",
        "bronze_odds.generated.json",
        "bronze_settlements.generated.json",
        "silver_fixtures.generated.json",
        "silver_odds.generated.json",
        "gold_evaluation_candidates.generated.json",
        "materialization_manifest.json",
        "command_result.json",
    ]
}

fn artifact_id(file_name: &str) -> String {
    file_name
        .trim_end_matches(".json")
        .replace(".generated", "")
        .replace('.', "_")
        .replace('-', "_")
}

fn compress_zstd(bytes: &[u8]) -> Result<Vec<u8>, String> {
    zstd::stream::encode_all(bytes, 3).map_err(|e| format!("zstd encode: {e}"))
}

fn build_record(args: &CliArgs, file_name: &str) -> Result<ArtifactRecordV441, String> {
    let source_path = args.artifact_dir.join(file_name);
    let source = fs::read(&source_path).map_err(|e| format!("read {}: {e}", source_path.display()))?;
    let compressed = compress_zstd(&source)?;
    let compressed_path = args.out_dir.join(format!("{file_name}.zst"));
    ensure_parent(&compressed_path)?;
    fs::write(&compressed_path, &compressed).map_err(|e| format!("write {}: {e}", compressed_path.display()))?;
    let source_bytes = source.len() as u64;
    let compressed_bytes = compressed.len() as u64;
    Ok(ArtifactRecordV441 {
        artifact_id: artifact_id(file_name),
        source_path: source_path.to_string_lossy().to_string(),
        compressed_path: compressed_path.to_string_lossy().to_string(),
        codec: "zstd".to_string(),
        source_bytes,
        compressed_bytes,
        sha256: sha256_hex(&source),
        compressed_sha256: sha256_hex(&compressed),
        compression_ratio: if source_bytes == 0 { 0.0 } else { compressed_bytes as f64 / source_bytes as f64 },
        status: "hashed_and_compressed".to_string(),
    })
}

fn build_manifest(args: &CliArgs) -> Result<StorageManifestV441, String> {
    fs::create_dir_all(&args.out_dir).map_err(|e| format!("create {}: {e}", args.out_dir.display()))?;
    let mut records = Vec::new();
    for file_name in artifact_files() {
        records.push(build_record(args, file_name)?);
    }
    let all_hashes_present = records.iter().all(|r| r.sha256.len() == 64 && r.compressed_sha256.len() == 64);
    let all_compressed_copies_present = records.iter().all(|r| Path::new(&r.compressed_path).exists());
    Ok(StorageManifestV441 {
        schema: "omnibet.materialized_storage_manifest.v441_v450".to_string(),
        paper_only: true,
        status: if all_hashes_present && all_compressed_copies_present { "storage_hashes_verified".to_string() } else { "storage_hashes_incomplete".to_string() },
        run_id: args.run_id.clone(),
        artifact_count: records.len(),
        artifacts: records,
        all_hashes_present,
        all_compressed_copies_present,
        ready_for_training: false,
        trust_status: "sample_only".to_string(),
        credential_values_present: false,
        recommendation_output_present: false,
    })
}

fn verification_report(manifest: &StorageManifestV441) -> Value {
    let total_source_bytes: u64 = manifest.artifacts.iter().map(|r| r.source_bytes).sum();
    let total_compressed_bytes: u64 = manifest.artifacts.iter().map(|r| r.compressed_bytes).sum();
    json!({
        "schema": "omnibet.materialized_storage_verification_report.v441_v450",
        "paper_only": true,
        "status": manifest.status,
        "run_id": manifest.run_id,
        "artifact_count": manifest.artifact_count,
        "total_source_bytes": total_source_bytes,
        "total_compressed_bytes": total_compressed_bytes,
        "overall_compression_ratio": if total_source_bytes == 0 { 0.0 } else { total_compressed_bytes as f64 / total_source_bytes as f64 },
        "all_hashes_present": manifest.all_hashes_present,
        "all_compressed_copies_present": manifest.all_compressed_copies_present,
        "ready_for_training": false,
        "trust_status": "sample_only",
        "credential_values_present": false,
        "recommendation_output_present": false
    })
}

fn run() -> Result<Value, String> {
    let args = parse_args()?;
    let manifest = build_manifest(&args)?;
    let manifest_value = serde_json::to_value(&manifest).map_err(|e| format!("manifest to value: {e}"))?;
    write_json(&args.manifest_out, &manifest_value)?;
    let verification = verification_report(&manifest);
    write_json(&args.verification_out, &verification)?;
    Ok(verification)
}

fn main() {
    match run() {
        Ok(payload) => println!("{}", serde_json::to_string_pretty(&payload).unwrap()),
        Err(err) => {
            eprintln!("{err}");
            std::process::exit(1);
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn materialized_storage_hashes_sha256_is_hex_v441() {
        let digest = sha256_hex(b"omnibet");
        assert_eq!(digest.len(), 64);
        assert!(digest.chars().all(|c| c.is_ascii_hexdigit()));
    }

    #[test]
    fn materialized_storage_hashes_run_id_sanitizes_v441() {
        assert_eq!(sanitize_run_id("ci;bad id"), "ci_bad_id");
    }

    #[test]
    fn materialized_storage_hashes_artifact_id_is_stable_v441() {
        assert_eq!(artifact_id("bronze_fixtures.generated.json"), "bronze_fixtures");
        assert_eq!(artifact_id("command_result.json"), "command_result");
    }
}
