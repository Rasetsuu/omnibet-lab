use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct StorageV2Contract {
    pub schema: String,
    pub goal: String,
    pub compatibility: StorageCompatibility,
    pub layers: StorageLayers,
    pub manifest_requirements: ManifestRequirements,
    pub training_safety: TrainingSafety,
    pub rust_migration: RustMigrationPlan,
    pub acceptance: StorageAcceptance,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct StorageCompatibility {
    pub current_runtime_pack_format: String,
    pub current_runtime_pack_codec: String,
    pub keep_jsonl_gzip_for_ci_and_small_runtime_packs: bool,
    pub add_parquet_zstd_for_large_history_and_training: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct StorageLayers {
    pub bronze_raw_snapshots: BronzeLayer,
    pub silver_canonical_facts: TableLayer,
    pub gold_training_features: TableLayer,
    pub model_artifacts: ModelLayer,
    pub recent_runtime_cache: RuntimeCacheLayer,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct BronzeLayer {
    pub purpose: String,
    pub default_codec: String,
    pub partition_keys: Vec<String>,
    pub required_fields: Vec<String>,
    pub retention_days_default: u32,
    pub delete_or_archive_after_promotion: bool,
    pub credential_values_allowed: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct TableLayer {
    pub purpose: String,
    pub default_codec: String,
    pub partition_keys: Vec<String>,
    pub tables: Vec<String>,
    pub keep_forever: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct ModelLayer {
    pub purpose: String,
    pub default_codec: String,
    pub required_fields: Vec<String>,
    pub keep_forever: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct RuntimeCacheLayer {
    pub purpose: String,
    pub default_codec: String,
    pub not_authoritative_history: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct ManifestRequirements {
    pub dataset_id_required: bool,
    pub schema_version_required: bool,
    pub row_counts_required: bool,
    pub byte_counts_required: bool,
    pub content_hashes_required: bool,
    pub created_at_required: bool,
    pub source_lineage_required: bool,
    pub prediction_time_boundary_required: bool,
    pub observed_at_boundary_required: bool,
    pub compression_ratio_required_for_pack_outputs: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct TrainingSafety {
    pub random_split_allowed: bool,
    pub walk_forward_required: bool,
    pub features_must_be_observed_before_prediction_time: bool,
    pub labels_only_after_settlement: bool,
    pub model_claims_require_market_specific_validation: bool,
    pub paper_only_until_validated: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct RustMigrationPlan {
    pub phase_a: Vec<String>,
    pub phase_b: Vec<String>,
    pub phase_c: Vec<String>,
    pub python_allowed_for: Vec<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct StorageAcceptance {
    pub current_jsonl_gzip_pack_still_supported: bool,
    pub large_history_prefers_parquet_zstd: bool,
    pub raw_provider_payloads_are_temporary: bool,
    pub canonical_facts_and_features_are_reproducible: bool,
    pub credential_values_never_stored: bool,
}

pub fn parse_storage_v2_contract(text: &str) -> Result<StorageV2Contract, serde_json::Error> {
    serde_json::from_str(text)
}

pub fn validate_storage_v2_contract(contract: &StorageV2Contract) -> Result<(), String> {
    if contract.schema != "omnibet.storage_v2_big_data.v233" {
        return Err(format!("unexpected storage schema: {}", contract.schema));
    }
    if contract.compatibility.current_runtime_pack_codec != "jsonl.gzip" {
        return Err("runtime pack codec must remain jsonl.gzip for compatibility".to_string());
    }
    if !contract.compatibility.keep_jsonl_gzip_for_ci_and_small_runtime_packs {
        return Err("jsonl.gzip CI/runtime pack compatibility must remain enabled".to_string());
    }
    if !contract.compatibility.add_parquet_zstd_for_large_history_and_training {
        return Err("parquet.zstd must be the preferred large-history/training direction".to_string());
    }
    if !contract.layers.silver_canonical_facts.default_codec.contains("parquet.zstd") {
        return Err("silver canonical facts must prefer parquet.zstd".to_string());
    }
    if !contract.layers.gold_training_features.default_codec.contains("parquet.zstd") {
        return Err("gold training features must prefer parquet.zstd".to_string());
    }
    if contract.layers.bronze_raw_snapshots.credential_values_allowed {
        return Err("bronze raw snapshots must not allow credential values".to_string());
    }
    if contract.training_safety.random_split_allowed {
        return Err("random training splits must remain forbidden".to_string());
    }
    if !contract.training_safety.walk_forward_required {
        return Err("walk-forward validation must be required".to_string());
    }
    if !contract.training_safety.features_must_be_observed_before_prediction_time {
        return Err("feature observed_at <= prediction_time boundary must be required".to_string());
    }
    if !contract.training_safety.labels_only_after_settlement {
        return Err("labels must only attach after settlement".to_string());
    }
    if !contract.acceptance.credential_values_never_stored {
        return Err("credential values must never be stored".to_string());
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn validates_minimal_storage_contract() {
        let text = include_str!("../../configs/storage_v2_big_data.v233.json");
        let contract = parse_storage_v2_contract(text).expect("parse storage contract");
        validate_storage_v2_contract(&contract).expect("validate storage contract");
        assert_eq!(contract.layers.bronze_raw_snapshots.retention_days_default, 30);
        assert!(contract.layers.gold_training_features.tables.contains(&"gold_market_features".to_string()));
    }
}
