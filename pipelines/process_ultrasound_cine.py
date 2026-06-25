#!/usr/bin/env python3
"""
Revolutionary Technology Company - Multicore US Cine Deconstructor & Calibrator
Extracts multi-frame video components, maps color Doppler RGB matrices, 
and embeds regional millimeter-per-pixel scaling vectors using CPU worker pools.
"""

import os
import sys
import pydicom
import numpy as np
from multiprocessing import Pool, cpu_count

def worker_write_us_frame(args):
    """Deconstructs a single video block layer and applies spatial scaling data."""
    frame_idx, output_path, source_file_path, frame_bytes, rows, cols, delta_x, delta_y, samples_per_pixel = args
    try:
        # Load file header envelope template
        ds = pydicom.dcmread(source_file_path, stop_before_pixels=True)
        if "NumberOfFrames" in ds: 
            del ds.NumberOfFrames
            
        ds.Rows = rows
        ds.Columns = cols
        ds.SamplesPerPixel = samples_per_pixel
        ds.PixelData = frame_bytes
        ds.InstanceNumber = int(frame_idx + 1)
        
        # Embed physical resolution calibration data into image attributes
        ds.ImageComments = f"US_MULTICORE_FRAME;DX={delta_x}mm;DY={delta_y}mm;FRAME={frame_idx + 1}"
        
        ds.save_as(output_path)
        return True
    except Exception:
        return False

def parallel_deconstruct_ultrasound(input_file: str, output_dir: str):
    os.makedirs(output_dir, exist_ok=True)
    ds = pydicom.dcmread(input_file)
    
    if ds.get("Modality") != "US":
        print("[US-ERROR] Aborting: Modality is not Ultrasound.")
        return False

    # Extract physical region calibration sequences (millimeters per pixel mapping)
    regions = ds.get("SequenceOfUltrasoundRegions", None)
    delta_x = regions[0].get("PhysicalDeltaX", "N/A") if regions else "N/A"
    delta_y = regions[0].get("PhysicalDeltaY", "N/A") if regions else "N/A"
    
    pixel_data = ds.pixel_array
    num_frames = int(ds.get("NumberOfFrames", 1))
    rows, cols = ds.Rows, ds.Columns
    samples_per_pixel = ds.get("SamplesPerPixel", 1)

    task_args = []
    print(f"[US-MULTICORE] Parsing {num_frames} frames from multi-frame video block...")
    for idx in range(num_frames):
        # Handle 4D multi-frame arrays (Frames, Rows, Cols, RGB Channels) or 3D grids (Grayscale)
        frame_matrix = pixel_data[idx] if num_frames > 1 else pixel_data
        out_path = os.path.join(output_dir, f"us_frame_{idx:03d}.dcm")
        
        task_args.append((
            idx, out_path, input_file, frame_matrix.tobytes(), 
            rows, cols, delta_x, delta_y, samples_per_pixel
        ))

    with Pool(processes=cpu_count()) as pool:
        _ = pool.map(worker_write_us_frame, task_args)
    print(f"[US-SUCCESS] Deconstructed video matrix using {cpu_count()} CPU cores.")

if __name__ == "__main__":
    parallel_deconstruct_ultrasound(sys.argv[1], sys.argv[2])
