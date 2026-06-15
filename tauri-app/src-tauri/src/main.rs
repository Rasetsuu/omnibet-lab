#[tauri::command]
fn ping() -> String {
    "omnibet-tauri-ok".to_string()
}

fn main() {
    tauri::Builder::default()
        .invoke_handler(tauri::generate_handler![ping])
        .run(tauri::generate_context!())
        .expect("error while running OmniBet Lab Tauri app");
}
