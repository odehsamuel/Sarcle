//! Attester B: Independent Rust Vegetation Cover Analyzer.
//!
//! Uses fixed-point integer mathematics and CIELAB a* channel thresholding.
//! Completely independent of OpenCV and floating-point chromaticity normalization.

use clap::Parser;
use image::{GenericImageView, Pixel, Rgb};
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::fs;
use std::path::PathBuf;

#[derive(Parser, Debug)]
#[command(name = "attester-b")]
#[command(about = "Proof-of-Weeding Independent Rust CIELAB Analyzer")]
struct Args {
    #[arg(short, long, help = "Path to input JPEG image")]
    image: PathBuf,

    #[arg(short, long, help = "Path to canonical ROI JSON file")]
    roi: PathBuf,

    #[arg(long, default_value_t = -50, help = "CIELAB a* green threshold")]
    threshold: i32,
}

#[derive(Debug, Deserialize)]
struct RoiPoint {
    x: String,
    y: String,
}

#[derive(Debug, Deserialize)]
struct RoiDefinition {
    points: Vec<RoiPoint>,
}

#[derive(Debug, Serialize)]
struct AnalysisOutput {
    algorithm_id: String,
    algorithm_family: u32,
    metric_id: u32,
    cover_bps: u32,
    analyzer_hash_hex: String,
    roi_pixels: usize,
    vegetation_pixels: usize,
}

/// Point-in-polygon algorithm (Ray casting)
fn is_point_in_poly(x: f64, y: f64, poly: &[(f64, f64)]) -> bool {
    let mut inside = false;
    let n = poly.len();
    let mut j = n - 1;
    for i in 0..n {
        let (xi, yi) = poly[i];
        let (xj, yj) = poly[j];
        if ((yi > y) != (yj > y)) && (x < (xj - xi) * (y - yi) / (yj - yi + 1e-12) + xi) {
            inside = !inside;
        }
        j = i;
    }
    inside
}

/// Fast fixed-point approximation of sRGB to CIELAB a* channel.
/// Green pixels exhibit negative a* values (towards green opponent).
fn srgb_to_cielab_a_fixed(r: u8, g: u8, b: u8) -> i32 {
    let r_i = r as i32;
    let g_i = g as i32;
    let b_i = b as i32;

    // Approximate XYZ coordinate weights scaled by 1024:
    // X ~ 0.4124*R + 0.3576*G + 0.1805*B
    // Y ~ 0.2126*R + 0.7152*G + 0.0722*B
    let x_scaled = (422 * r_i + 366 * g_i + 185 * b_i) >> 10;
    let y_scaled = (218 * r_i + 732 * g_i + 74 * b_i) >> 10;

    // a* = 500 * (f(X/Xn) - f(Y/Yn))
    // Green strongly suppresses a* into negative integers
    let diff = x_scaled - y_scaled;
    (diff * 500) >> 8
}

fn compute_analyzer_hash(threshold: i32) -> String {
    let canonical = format!(
        "{{\"algorithm_id\":\"cielab_fixed_point\",\"threshold\":{},\"version\":\"1.0.0\"}}",
        threshold
    );
    let mut hasher = Sha256::new();
    hasher.update(canonical.as_bytes());
    hex::encode(hasher.finalize())
}

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let args = Args::parse();

    // 1. Load ROI
    let roi_content = fs::read_to_string(&args.roi)?;
    let roi_def: RoiDefinition = serde_json::from_str(&roi_content)?;
    let poly: Vec<(f64, f64)> = roi_def
        .points
        .iter()
        .map(|p| (p.x.parse::<f64>().unwrap(), p.y.parse::<f64>().unwrap()))
        .collect();

    // 2. Load Image
    let img = image::open(&args.image)?;
    let (width, height) = img.dimensions();

    let mut total_roi_pixels = 0usize;
    let mut veg_pixels = 0usize;

    for y in 0..height {
        let norm_y = y as f64 / height as f64;
        for x in 0..width {
            let norm_x = x as f64 / width as f64;
            if is_point_in_poly(norm_x, norm_y, &poly) {
                total_roi_pixels += 1;
                let pixel = img.get_pixel(x, y).to_rgb();
                let a_star = srgb_to_cielab_a_fixed(pixel[0], pixel[1], pixel[2]);
                if a_star < args.threshold {
                    veg_pixels += 1;
                }
            }
        }
    }

    let cover_bps = if total_roi_pixels > 0 {
        ((veg_pixels as u64 * 10000) / total_roi_pixels as u64) as u32
    } else {
        0
    };

    let output = AnalysisOutput {
        algorithm_id: "cielab_fixed_point".to_string(),
        algorithm_family: 2,
        metric_id: 1,
        cover_bps,
        analyzer_hash_hex: compute_analyzer_hash(args.threshold),
        roi_pixels: total_roi_pixels,
        vegetation_pixels: veg_pixels,
    };

    println!("{}", serde_json::to_string_pretty(&output)?);
    Ok(())
}
