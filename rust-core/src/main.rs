use omnibet_lab_core::{
    expected_value, fair_odds, quarter_kelly, remove_overround_multiplicative,
};

fn main() {
    println!("OmniBet Rust core v7 skeleton");

    let p = 0.55;
    let odds = 2.10;
    println!("prob={:.3} fair_odds={:.3}", p, fair_odds(p));
    println!("ev={:?} quarter_kelly={:?}", expected_value(p, odds), quarter_kelly(p, odds));

    if let Some(devig) = remove_overround_multiplicative(&[2.70, 2.30, 4.40]) {
        println!("devig={:?}", devig);
    }
}
