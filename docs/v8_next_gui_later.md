# GUI Later, Engine First

The current browser GUI is a rough prototype:

```text
web_gui/index.html
```

The Tauri folder exists, but it is not wired to the Rust core yet:

```text
tauri-app/
```

Project decision:

1. Build reliable engine and data pipeline first.
2. Verify Rust pack reading and inference.
3. Add more data and better models.
4. Only then build the real Tauri desktop GUI.

This avoids wasting time polishing a GUI around unstable data/model logic.
