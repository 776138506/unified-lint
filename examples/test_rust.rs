// Test Rust file with intentional violations

pub fn undocumented_public_function() {
    // This public function lacks documentation
    println!("Hello");
}

/// This one is documented
pub fn documented_function() {
    println!("OK");
}

fn very_long_function() {
    let x = 1;
    let y = 2;
    let z = 3;
    let a = 4;
    let b = 5;
    let c = 6;
    let d = 7;
    let e = 8;
    let f = 9;
    let g = 10;
    let h = 11;
    let i = 12;
    let j = 13;
    let k = 14;
    let l = 15;
    let m = 16;
    let n = 17;
    let o = 18;
    let p = 19;
    let q = 20;
    let r = 21;
    let s = 22;
    let t = 23;
    let u = 24;
    let v = 25;
    let w = 26;
    let x2 = 27;
    let y2 = 28;
    let z2 = 29;
    let a2 = 30;
    let b2 = 31;
    let c2 = 32;
    let d2 = 33;
    let e2 = 34;
    let f2 = 35;
    let g2 = 36;
    let h2 = 37;
    let i2 = 38;
    let j2 = 39;
    let k2 = 40;
    let l2 = 41;
    let m2 = 42;
    let n2 = 43;
    let o2 = 44;
    let p2 = 45;
    let q2 = 46;
    let r2 = 47;
    let s2 = 48;
    println!("Done");
}

fn use_unsafe() {
    unsafe {
        // Unsafe block without documentation
        let ptr = std::ptr::null::<i32>();
    }
}
