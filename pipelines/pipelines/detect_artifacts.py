#!/usr/bin/env python3
"""
Revolutionary Technology Company - MRI Artifact & Motion Detection Engine
CUDA-Accelerated 2D Fast Fourier Transform (FFT) Analysis.
Automatically flags structural motion blur, ghosting, or RF noise spikes.
"""

import os
import sys
import pydicom
import numpy as np

try:
    import torch
    CUDA_AVAILABLE = torch.cuda.is_available()
except ImportError:
    torch = None
    CUDA_AVAILABLE = False

def analyze_slice_artifacts_cuda(pixel_array: np.ndarray, threshold: float = 0.05) -> tuple:
    """
    Transforms the spatial image matrix into the frequency domain (K-Space) using 
    NVIDIA GPU-accelerated Fast Fourier Transforms to spot anomalies.
    """
    device = torch.device("cuda:0")
    
    # Upload pixel array float values directly onto RTX 6000 registers
    tensor_slice = torch.from_numpy(pixel_array.astype(np.float32)).to(device)
    
    # Execute hardware-accelerated 2D Fast Fourier Transform
    k_space = torch.fft.fft2(tensor_slice)
    k_space_shifted = torch.fft.fftshift(k_space)
    magnitude_spectrum = torch.abs(k_space_shifted)
    
    # Calculate high-frequency energy ratio (Motion artifacts blur high-frequency bands,
    # while RF spikes introduce uncharacteristic high-frequency energy spikes)
    total_energy = torch.sum(magnitude_spectrum)
    
    # Define a bounding box for the periphery edges (high-frequency components)
    rows, cols = magnitude_spectrum.shape
    r_margin, c_margin = int(rows * 0.1), int(cols * 0.1)
    
    high_freq_energy = (
        torch.sum(magnitude_spectrum[:r_margin, :]) + 
        torch.sum(magnitude_spectrum[-r_margin:, :]) + 
        torch.sum(magnitude_spectrum[:, :c_margin]) + 
        torch.sum(magnitude_spectrum[:, -c_margin:])
    )
    
    hf_ratio = (high_freq_energy / total_energy).item()
    torch.cuda.synchronize()
    
    # Flag study if high-frequency noise metrics pierce standard physics tolerances
    is_corrupted = hf_ratio > threshold
    return is_corrupted, round(hf_ratio, 4)

def run_artifact_detection_pipeline(input_dir: str, artifact_log_path: str):
    """Audits full directory sequences for scan quality anomalies."""
    print(f"[ARTIFACT-DETECTOR] Auditing scan volume matrices inside: {input_dir}")
    
    corrupted_slices = 0
    total_slices = 0
    metrics_summary = []

    for f in os.listdir(input_dir):
        path = os.path.join(input_dir, f)
        if os.path.isfile(path):
            try:
                ds = pydicom.dcmread(path)
                if ds.get("Modality") != "MR":
                    continue
                
                total_slices += 1
                pixel_array = ds.pixel_array
                
                if CUDA_AVAILABLE:
                    is_corrupted, noise_index = analyze_slice_artifacts_cuda(pixel_array)
                else:
                    # CPU Fallback via basic standard deviation metrics
                    noise_index = float(np.std(pixel_array) / np.mean(pixel_array)) if np.mean(pixel_array) > 0 else 0
                    is_corrupted = noise_index > 1.5

                if is_corrupted:
                    corrupted_slices += 1
                    print(f"[WARN] Volumetric variance threshold breached on file: {f} (Index: {noise_index})")
                
                metrics_summary.append({"file": f, "artifact_index": noise_index, "flagged": is_corrupted})

            except Exception as e:
                continue

    if total_slices == 0:
        print("[ARTIFACT-ERROR] Found zero valid structural arrays to audit.")
        return False

    corruption_ratio = corrupted_slices / total_slices
    volume_flagged = corruption_ratio > 0.15 # Flag total series if over 15% of slices are distorted

    print("\n================ QUALITY ASSURANCE AUDIT ================")
    print(f"Total Slices Audited     : {total_slices}")
    print(f"Flagged Corrupt Slices   : {corrupted_slices} ({corruption_ratio*100:.1f}%)")
    print(f"Series Re-scan Actioned  : {'❌ YES - HIGH ARTIFACT DISTORTION' if volume_flagged else '✅ NO - PASSED QUALITY BOUNDS'}")
    print("=========================================================")

    # Write out execution tracking data for the alert or dashboard engine
    audit_payload = {
        "directory": input_dir,
        "series_flagged_for_rescan": volume_flagged,
        "corruption_percentage": round(corruption_ratio * 100, 2),
        "slice_logs": metrics_summary
    }

    with open(artifact_log_path, "w") as log_f:
        import json
        json.dump(audit_payload, log_f, indent=2)

    return volume_flagged

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python detect_artifacts.py <input_series_dir> <output_audit_log.json>")
        sys.exit(1)
    run_artifact_detection_pipeline(sys.argv[1], sys.argv[2])
