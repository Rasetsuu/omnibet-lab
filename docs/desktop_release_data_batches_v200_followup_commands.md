# Extracted package commands

After the follow-up release packaging fix lands, an extracted Linux package should support:

```bash
cd package
bash scripts/download_football_data_batch_002.sh
bash scripts/run_football_data_batch_002.sh
bash scripts/download_football_data_batch_003.sh
bash scripts/run_football_data_batch_003.sh
```

The runners prefer bundled binaries under `./bin`:

```text
bin/omnibet-football-data-importer
bin/omnibet-feature-count-gate
bin/omnibet-baseline-eval
```

and only fall back to `cargo run` in a development checkout.
