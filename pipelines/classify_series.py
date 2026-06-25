#!/usr/bin/env python3
"""
Revolutionary Technology Company - Multicore Series Classification Engine
Parallelized multi-scanner hanging protocol organization pool layout.
"""

import os
import sys
import pydicom
import numpy as np
from multiprocessing import Pool, cpu_count

def worker_classify_and_save(args):
    """Processes, labels, and routes an individual scan file on a separate CPU core."""
    file_path, output_base_dir = args
    try:
        # Fast header metadata parsing pass
        ds = pydicom.dcmread(file_path, stop_before_pixels=True)
        if ds.get("Modality") != "MR": return False

        te = ds.get("EchoTime")
        tr = ds.get("RepetitionTime")
        ti = ds.get("InversionTime")
        seq_name = ds.get("SequenceName", ds.get("SeriesDescription", "UNKNOWN"))
        vectors = ds.get("ImageOrientationPatient")

        # Define plane type
        plane = "AXIAL"
        if vectors and len(vectors) >= 6:
            normal = np.abs(np.cross(np.array(vectors[0:3]), np.array(vectors[3:6])))
            max_idx = np.argmax(normal)
            plane = "SAGITTAL" if max_idx == 0 else "CORONAL" if max_idx == 1 else "AXIAL"

        # Define tissue weight contrast rules
        contrast = "T2"
        if tr and te and float(tr) < 800 and float(te) < 30: contrast = "T1"
        if "FLAIR" in str(seq_name).upper(): contrast = "FLAIR"

        protocol_label = f"{plane}_{contrast}"
        target_dir = os.path.join(output_base_dir, protocol_label)
        os.makedirs(target_dir, exist_ok=True)

        # Re-save full data block with standardized descriptors
        full_ds = pydicom.dcmread(file_path)
        full_ds.SeriesDescription = protocol_label
        full_ds.ProtocolName = protocol_label
        full_ds.save_as(os.path.join(target_dir, os.path.basename(file_path)))
        return True
    except Exception:
        return False

def parallel_classify_study(input_dir: str, output_base_dir: str):
    task_args = []
    for root, _, files in os.walk(input_dir):
        for f in files:
            task_args.append((os.path.join(root, f), output_base_dir))

    print(f"[CLASSIFY-MULTICORE] Sorting {len(task_args)} elements via {cpu_count()} concurrent workers...")
    with Pool(processes=cpu_count()) as pool:
        _ = pool.map(worker_classify_and_save, task_args)

if __name__ == "__main__":
    parallel_classify_study(sys.argv[1], sys.argv[2])
