use std::fs;
use std::path::Path;

const ICON_ICO: &[u8] = &[
    0, 0, 1, 0, 1, 0, 1, 1, 0, 0, 1, 0, 32, 0, 48, 0, 0, 0, 22, 0, 0, 0,
    40, 0, 0, 0, 1, 0, 0, 0, 2, 0, 0, 0, 1, 0, 32, 0, 0, 0, 0, 0, 8, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 32, 80, 160, 255, 0, 0, 0, 0,
    0, 0, 0, 0,
];

const ICON_PNG: &[u8] = &[
    137, 80, 78, 71, 13, 10, 26, 10, 0, 0, 0, 13, 73, 72, 68, 82, 0, 0, 0, 1,
    0, 0, 0, 1, 8, 6, 0, 0, 0, 31, 21, 196, 137, 0, 0, 0, 13, 73, 68, 65, 84,
    120, 156, 99, 16, 80, 160, 248, 15, 0, 4, 2, 1, 114, 215, 208, 122, 190, 0, 0,
    0, 0, 73, 69, 78, 68, 174, 66, 96, 130,
];

fn ensure_file(path: &str, bytes: &[u8]) {
    let path = Path::new(path);
    if !path.exists() {
        if let Some(parent) = path.parent() {
            fs::create_dir_all(parent).expect("create Tauri icon directory");
        }
        fs::write(path, bytes).expect("write placeholder Tauri icon");
    }
}

fn main() {
    ensure_file("icons/icon.ico", ICON_ICO);
    ensure_file("icons/icon.png", ICON_PNG);
    tauri_build::build();
}
