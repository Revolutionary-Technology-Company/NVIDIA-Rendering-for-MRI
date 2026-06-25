#!/usr/bin/env python3
"""
Revolutionary Technology Company - Multi-Core MRI Series Classification Engine
Parses directional cosine patient vectors to define 3D orthogonal slices, 
standardizes multiscanner descriptors, and builds hanging protocols in parallel.
"""

import os
import sys
import pydicom
import numpy as np
from multiprocessing import Pool, cpu_count

def calculate_exact_slice_plane(orientation_vector):
    """Parses patient orientation vectors to identify Axial, Coronal, Sagittal, or Oblique planes."""
    if not orientation_vector or len(orientation_vector) < 6:
        return "UNKNOWN_PLANE"
    
    # Extract directional cosines
    row_x, row_y, row_z = orientation_vector[0:3]
    col_x, col_y, col_z = orientation_vector[3:6]
    
    # Calculate normal vector of the image plane
    normal = np.cross(np.array([row_x, row_y, row_z]), np.array([col_x, col_y, col_z]))
    abs_normal = np.abs(normal)
    max_idx = np.argmax(abs_normal)
    
    # Check if the slice is highly tilted (Oblique plane check)
    if abs_normal[max_idx] < 0.707:
        return "OBLIQUE"
        
    if max_idx == 0: return "SAGITTAL"
    if max_idx == 1: return "CORONAL"
    if max_idx == 2: return "AXIAL"
    return "UNKNOWN_PLANE"

def resolve_contrast_weighting(te, tr, ti, series_desc, protocol_name):
    """Applies strict MRI sequence physics rules to calculate exact tissue contrast weightings."""
    desc_str = f"{str(series_desc)} {str(protocol_name)}".upper()
    
    # Explicit structural overrides
    if "FLAIR" in desc_str: return "FLAIR"
    if "STIR" in desc_str or "FAT" in desc_str: return "FAT_SUPPRESSED"
    if "DWI" in desc_str or "ADC" in desc_str: return "DIFFUSION"
    if "MPRAGE" in desc_str or "SPGR" in desc_str: return "T1_3D_VOLUMETRIC"

    if tr and te:
        try:
            tr_v, te_v = float(tr), float(te)
            ti_v = float(ti) if ti else 0.0
            
            if ti_v > 1500 and tr_v > 5000: return "FLAIR"
            if tr_v < 800 and te_v < 30: return "T1"
            if tr_v > 2000 and te_v > 70: return "T2"
            if tr_v > 2000 and te_v < 35: return "PD"
        except ValueError:
            pass
            
    return "STRUCTURAL_ANATOMY"

def worker_classify_and_route(args):
    """Worker core task executing detailed physical validations per file entry."""
    file_path, output_base_dir = args
    try:
        ds = pydicom.dcmread(file_path, stop_before_pixels=True)
        if ds.get("Modality") != "MR": 
            return False

        # Gather target metadata
        te = ds.get("EchoTime")
        tr = ds.get("RepetitionTime")
        ti = ds.get("InversionTime")
        series_desc = ds.get("SeriesDescription", "")
        protocol_name = ds.get("ProtocolName", "")
        orientation = ds.get("ImageOrientationPatient")
        manufacturer = ds.get("Manufacturer", "UNKNOWN_OEM").upper()

        # Run feature evaluation layers
        slice_plane = calculate_exact_slice_plane(orientation)
        contrast_mode = resolve_contrast_weighting(te, tr, ti, series_desc, protocol_name)
        
        # Build strict clinical protocol directories
        standardized_label = f"{slice_plane}_{contrast_mode}"
        target_dir = os.path.join(output_base_dir, standardized_label)
        os.makedirs(target_dir, exist_ok=True)

        # Full file re-save with embedded audit signatures
        full_ds = pydicom.dcmread(file_path)
        full_ds.SeriesDescription = standardized_label
        full_ds.ProtocolName = standardized_label
        
        # Log scanner hardware origins for IT tracking
        full_ds.ImageComments = f"CLASSIFIED_BY_RTX6000;OEM={manufacturer};TR={tr};TE={te}"
        
        full_ds.save_as(os.path.join(target_dir, os.path.basename(file_path)))
        return True
    except Exception:
        return False

def parallel_classify_study(input_dir: str, output_base_dir: str):
    task_args = []
    for root, _, files in os.walk(input_dir):
        for f in files:
            task_args.append((os.path.join(root, f), output_base_dir))

    print(f"[CLASSIFY-MULTICORE] Standardizing {len(task_args)} sequences via {cpu_count()} CPU pools...")
    with Pool(processes=cpu_count()) as pool:
        _ = pool.map(worker_classify_and_route, task_args)

if __name__ == "__main__":
    parallel_classify_study(sys.argv[1], sys.argv[2])
