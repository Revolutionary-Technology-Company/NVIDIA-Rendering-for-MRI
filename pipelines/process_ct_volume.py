#!/usr/bin/env python3
"""
Revolutionary Technology Company - CT Dose Audit & Lung Segmenter
Extracts radiation metrics and applies CUDA-accelerated volume thresholding.
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

def extract_ct_dose_metrics(ds: pydicom.dataset.Dataset) -> dict:
    """Extracts CT Dose Index (CTDIvol) and Dose Length Product (DLP) from metadata."""
    # CTDIvol is typically stored in Hounsfield/Exposure elements or vendor tags
    ctdi = ds.get((0x0018, 0x9345), "N/A") # CTDIvol tag
    dlp = ds.get((0x0018, 0x9346), "N/A")  # Total DLP tag
    return {"CTDIvol_mGy": str(ctdi), "DLP_mGy_cm": str(dlp)}

def segment_lungs_cuda(volume: np.ndarray, lower_hu: int = -900, upper_hu: int = -400) -> np.ndarray:
    """Uses GPU arrays to mask Hounsfield Unit (HU) ranges corresponding to lung air spaces."""
    device = torch.device("cuda:0")
    tensor_vol = torch.from_numpy(volume.astype(np.float32)).to(device)
    
    # Create binary mask for air tissue density (-900 to -400 HU)
    mask = (tensor_vol >= lower_hu) & (tensor_vol <= upper_hu)
    
    # Apply mask: keep lung tissue structures, zero out everything else
    segmented_tensor = torch.where(mask, tensor_vol, torch.tensor(0.0, device=device))
    
    segmented_vol = segmented_tensor.cpu().numpy().astype(np.int16)
    torch.cuda.synchronize()
    return segmented_vol

def run_ct_pipeline(input_dir: str, output_dir: str):
    print(f"[CT-PIPELINE] Processing CT slices inside: {input_dir}")
    slices = [pydicom.dcmread(os.path.join(input_dir, f)) for f in os.listdir(input_dir) if os.path.isfile(os.path.join(input_dir, f))]
    slices.sort(key=lambda x: float(x.SliceLocation) if "SliceLocation" in x else 0)
    
    # Audit radiation dose profiles from the primary slice
    dose_info = extract_ct_dose_metrics(slices[0])
    print(f"[CT-DOSE-AUDIT] Extracted metrics: {dose_info}")

    # Reconstruct 3D matrix block
    rows, cols = int(slices[0].Rows), int(slices[0].Columns)
    volume_matrix = np.zeros((len(slices), rows, cols), dtype=np.int16)
    for i, s in enumerate(slices):
        volume_matrix[i, :, :] = s.pixel_array

    # Rescale pixel values to true Hounsfield Units (HU) using vendor slope/intercept
    slope = float(slices[0].get("RescaleSlope", 1))
    intercept = float(slices[0].get("RescaleIntercept", 0))
    hu_volume = (volume_matrix * slope) + intercept

    # Segment lung tissue on GPU
    if CUDA_AVAILABLE:
        segmented_hu = segment_lungs_cuda(hu_volume)
    else:
        segmented_hu = np.where((hu_volume >= -900) & (hu_volume <= -400), hu_volume, 0)

    # Convert back to raw pixel data mapping and save
    final_volume = ((segmented_hu - intercept) / slope).astype(np.uint16)
    
    os.makedirs(output_dir, exist_ok=True)
    for i, s in enumerate(slices):
        s.PixelData = final_volume[i, :, :].tobytes()
        s.ImageComments = f"CT_LUNG_SEGMENTED_RTX6000;DLP={dose_info['DLP_mGy_cm']}"
        s.save_as(os.path.join(output_dir, f"segmented_ct_{i:04d}.dcm"))
        
    print(f"[CT-SUCCESS] Volume processed and routed to: {output_dir}")

if __name__ == "__main__":
    run_ct_pipeline(sys.argv[1], sys.argv[2])
