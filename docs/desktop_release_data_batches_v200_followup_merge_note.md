# Merge note

PR #200 originally fixed only Windows archive quoting and was merged before the data-batch packaging expansion finished.

This branch now has the follow-up changes needed for extracted desktop packages:

- bundled data-batch scripts
- bundled batch configs/docs
- bundled Python batch checks/runners
- bundled Rust data CLIs
- portable scripts that prefer `./bin` CLIs before falling back to `cargo run`

Open this branch as a new follow-up PR if these commits are not already on `master`.
