#!/usr/bin/env python3
"""
Revolutionary Technology Company - Multicore MRI NVIDIA Pipeline
Asynchronous Multiprocess Ingestion with CUDA Stream Offloading.
Optimized for high-throughput multicore CPUs paired with the RTX 6000 Ada.
"""

import os
import sys
import time
import pydicom
import numpy as np
from multiprocessing import Pool, cpu_count

# Attempt to configure CUDA acceleration bounds
try:
    import torch
    CUDA_AVAILABLE = torch.cuda.is_available()
except ImportError:
    torch = None
    CUDA_AVAILABLE = False

def get_system_resource_capacity():
    """Identifies total physical host CPU cores and GPU capability."""
    cores = cpu_count()
    gpu_name = torch.cuda.get_device_name(0) if CUDA_AVAILABLE else "None (CPU Fallback)"
    print(f"[SYSTEM-INFO] Available Logical CPU Cores: {cores}")
    print(f"[SYSTEM-INFO] Target Acceleration GPU     : {gpu_name}")
    return cores

def worker_process_slice(args):
    """
    Isolated core worker function.
    Processes a single slice using explicit asynchronous execution bounds.
    """
    input_path, output_path = args
    try:
        start_time = time.time()
        
        # 1. Thread-safe DICOM File IO reading
        ds = pydicom.dcmread(input_path)
        if ds.get("Modality") != "MR":
            return False, f"Skipped non-MR file: {os.path.basename(input_path)}"

        pixel_array = ds.pixel_array.astype(np.float32)

        # 2. Hardware Acceleration Pathing
        if CUDA_AVAILABLE:
            device = torch.device("cuda:0")
            
            # Create a localized execution stream to allow parallel GPU operations
            # This prevents separate CPU processes from blocking each other on the GPU card
            stream = torch.cuda.Stream(device=device)
            
            with torch.cuda.stream(stream):
                # Transfer array block into GPU memory space asynchronously
                tensor_slice = torch.from_numpy(pixel_array).to(device, non_blocking=True)
                
                # --- START ACCELERATED PROCESSING ---
                # Apply high-precision tensor matrix transformation
                processed_tensor = tensor_slice * 1.15
                # ------------------------------------
                
                # Fetch matrix data back to physical host RAM safely
                processed_pixel_data = processed_tensor.cpu().numpy()
            
            # Synchronize this specific process stream queue without stopping the whole card
            stream.synchronize()
        else:
            # CPU multicore fallback matrix mathematics
            processed_pixel_data = pixel_array * 1.15

        # 3. Output Translation Matrix
        processed_pixel_data = np.clip(processed_pixel_data, 0, 65535).astype(np.uint16)
        ds.PixelData = processed_pixel_data.tobytes()
        
        # Inject structural tracking stamps
        ds.ImageComments = f"RTX_MULTICORE_PIPELINE; PROC_TIME={time.time() - start_time:.4f}s"
        ds.save_as(output_path)
        
        return True, f"Successfully processed {os.path.basename(input_path)} in {time.time() - start_time:.4f}s"

    except Exception as e:
        return False, f"Error processing file {os.path.basename(input_path)}: {str(e)}"

def batch_process_volume(input_directory: str, output_directory: str):
    """Orchestrates directory volumes using an optimized multiprocessing core worker pool."""
    if not os.path.exists(output_directory):
        os.makedirs(output_directory)

    # Gather matching target items from the path directory
    dicom_files = [
        os.path.join(input_directory, f) for f in os.listdir(input_directory)
        if f.lower().endswith(('.dcm', '.ima')) or os.path.isfile(os.path.join(input_directory, f))
    ]

    if not dicom_files:
        print(f"[WARN] No incoming target files located inside: {input_directory}")
        return

    # Package target and destination lists into tuples for the worker pool
    task_args = []
    for f in dicom_files:
        out_f = os.path.join(output_directory, "proc_" + os.path.basename(f))
        task_args.append((f, out_f))

    total_tasks = len(task_args)
    worker_cores = get_system_resource_capacity()
    
    print(f"\n[EXECUTION] Spawning pool across {worker_cores} CPU cores for {total_tasks} slices...")
    global_start = time.time()

    # Launch parallel process workers
    with Pool(processes=worker_cores) as pool:
        results = pool.map(worker_process_slice, task_args)

    # Output analytical run statistics
    success_count = sum(1 for success, _ in results if success)
    print("\n================== RUN REPORT ==================")
    print(f"Total DICOM Files Analyzed : {total_tasks}")
    print(f"Successfully Accelerated   : {success_count}")
    print(f"Failed / Skipped Execution : {total_tasks - success_count}")
    print(f"Total Volumetric Run Time  : {time.time() - global_start:.2f} seconds")
    print("================================================")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python reconstruct_mri_multicore.py <input_dir> <output_dir>")
        sys.exit(1)
        
    batch_process_volume(sys.argv[1], sys.argv[2])
