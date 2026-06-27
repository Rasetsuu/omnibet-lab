use serde::{Deserialize, Serialize};
use std::collections::BTreeMap;

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct StorageV2CompressionContract {
    pub schema: String,
    pub milestone: String,
    pub paper_only: bool,
    pub local_first: bool,
    pub live_provider_calls_allowed: bool,
    pub credential_values_allowed: bool,
    pub versions: BTreeMap<String, String>,
    pub runtime_compatibility: RuntimeCompatibility,
    pub layers: CompressionLayers,
    pub provider_cache_manifest: ProviderCacheManifestContract,
    pub writer_migration_plan: WriterMigrationPlan,
    pub walk_forward_dataset_loader: WalkForwardDatasetLoaderShape,
    pub acceptance: StorageV2CompressionAcceptance,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct RuntimeCompatibility {
    pub keep_jsonl_gzip_for_ci_runtime_packs: bool,
    pub existing_pack_format: String,
    pub existing_pack_codec: String,
    pub small_runtime_cache_allowed: Vec<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct CompressionLayers {
    pub bronze_raw_snapshots: BronzeCompressionLayer,
    pub silver_canonical_facts: TableCompressionLayer,
    pub gold_training_features: TableCompressionLayer,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct BronzeCompressionLayer {
    pub codec: String,
    pub alternate_codec: String,
    pub purpose: String,
    pub retention_days_default: u32,
    pub delete_raw_after_verified_promotion: bool,
    pub partition_keys: Vec<String>,
    pub required_manifest_fields: Vec<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct TableCompressionLayer {
    pub codec: String,
    pub purpose: String,
    pub partition_keys: Vec<String>,
    pub tables: Vec<String>,
    pub keep_long_term: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct ProviderCacheManifestContract {
    pub target_runtime: String,
    pub python_allowed_for_prototypes: bool,
    pub required_fields: Vec<String>,
    pub forbidden_fields: Vec<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct WriterMigrationPlan {
    pub target_runtime: String,
    pub silver_writer_inputs: Vec<String>,
    pub gold_writer_inputs: Vec<String>,
    pub writer_outputs: Vec<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct WalkForwardDatasetLoaderShape {
    pub target_runtime: String,
    pub random_split_allowed: bool,
    pub required_window_fields: Vec<String>,
    pub required_safety_checks: Vec<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct StorageV2CompressionAcceptance {
    pub jsonl_gzip_compat_preserved: bool,
    pub bronze_uses_zstd_and_is_temporary: bool,
    pub silver_gold_use_parquet_zstd: bool,
    pub provider_cache_manifest_has_no_credentials: bool,
    pub silver_gold_writer_plan_is_rust_targeted: bool,
    pub walk_forward_loader_shape_forbids_random_split: bool,
    pub content_hashes_and_row_counts_required: bool,
    pub docs_smoke_and_workflow_added: bool,
}

pub fn parse_storage_v2_compression_contract(
    text: &str,
) -> Result<StorageV2CompressionContract, serde_json::Error> {
    serde_json::from_str(text)
}

pub fn validate_storage_v2_compression_contract(
    contract: &StorageV2CompressionContract,
) -> Result<(), String> {
    if contract.schema != "omnibet.storage_v2_compression_contract.v266_v270" {
        return Err(format!("unexpected storage compression schema: {}", contract.schema));
    }
    if !contract.paper_only || !contract.local_first {
        return Err("storage compression contract must remain paper-only and local-first".to_string());
    }
    if contract.live_provider_calls_allowed {
        return Err("storage compression foundation must not allow live provider calls".to_string());
    }
    if contract.credential_values_allowed {
        return Err("storage compression foundation must not allow credential values".to_string());
    }
    if contract.runtime_compatibility.existing_pack_codec != "jsonl.gzip" {
        return Err("existing CI/runtime pack codec must remain jsonl.gzip".to_string());
    }
    if !contract.runtime_compatibility.keep_jsonl_gzip_for_ci_runtime_packs {
        return Err("jsonl.gzip compatibility must be preserved for small CI/runtime packs".to_string());
    }
    let bronze = &contract.layers.bronze_raw_snapshots;
    if !bronze.codec.contains("zstd") || bronze.retention_days_default == 0 {
        return Err("bronze raw snapshots must use zstd and have a positive retention window".to_string());
    }
    if !bronze.delete_raw_after_verified_promotion {
        return Err("bronze raw snapshots must be deletable after verified promotion".to_string());
    }
    for required in ["payload_sha256", "payload_path", "row_count", "compressed_bytes"] {
        if !bronze.required_manifest_fields.contains(&required.to_string()) {
            return Err(format!("bronze manifest missing required field: {required}"));
        }
    }
    if contract.layers.silver_canonical_facts.codec != "parquet.zstd" {
        return Err("silver canonical facts must use parquet.zstd".to_string());
    }
    if contract.layers.gold_training_features.codec != "parquet.zstd" {
        return Err("gold training features must use parquet.zstd".to_string());
    }
    if !contract.layers.silver_canonical_facts.keep_long_term || !contract.layers.gold_training_features.keep_long_term {
        return Err("silver and gold data must be kept long-term".to_string());
    }
    if contract.provider_cache_manifest.target_runtime != "rust" {
        return Err("provider cache manifest target runtime must be rust".to_string());
    }
    for forbidden in ["api_key", "secret", "bearer_token", "credential_value"] {
        if !contract.provider_cache_manifest.forbidden_fields.contains(&forbidden.to_string()) {
            return Err(format!("provider cache manifest must forbid: {forbidden}"));
        }
    }
    if contract.writer_migration_plan.target_runtime != "rust" {
        return Err("silver/gold writer migration must target rust".to_string());
    }
    if contract.walk_forward_dataset_loader.target_runtime != "rust" {
        return Err("walk-forward dataset loader must target rust".to_string());
    }
    if contract.walk_forward_dataset_loader.random_split_allowed {
        return Err("walk-forward dataset loader must forbid random splits".to_string());
    }
    for safety in [
        "feature_observed_at_lte_prediction_time",
        "label_created_after_settlement",
        "no_random_shuffle_split",
        "market_family_specific_validation",
    ] {
        if !contract.walk_forward_dataset_loader.required_safety_checks.contains(&safety.to_string()) {
            return Err(format!("walk-forward loader missing safety check: {safety}"));
        }
    }
    if !contract.acceptance.jsonl_gzip_compat_preserved
        || !contract.acceptance.silver_gold_use_parquet_zstd
        || !contract.acceptance.walk_forward_loader_shape_forbids_random_split
    {
        return Err("storage compression acceptance gates are not satisfied".to_string());
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn validates_storage_v2_compression_contract() {
        let text = include_str!("../../configs/storage_v2_compression.v266_v270.json");
        let contract = parse_storage_v2_compression_contract(text).expect("parse v266-v270 contract");
        validate_storage_v2_compression_contract(&contract).expect("validate v266-v270 contract");
        assert_eq!(contract.layers.bronze_raw_snapshots.codec, "jsonl.zstd");
        assert_eq!(contract.layers.silver_canonical_facts.codec, "parquet.zstd");
        assert!(!contract.walk_forward_dataset_loader.random_split_allowed);
    }
}
