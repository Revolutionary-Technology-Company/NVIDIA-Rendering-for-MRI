#!/usr/bin/env python3
"""
Revolutionary Technology Company - MRI Pipeline Anonymizer
Strips HIPAA PHI fields from incoming GE and Siemens DICOM instances 
before routing offsite to Cloud PACS endpoints.
"""

import sys
import os
import pydicom
from pydicom.dataset import Dataset

# Define Safe Harbor fields to clear or replace
TAGS_TO_DELETE = [
    (0x0010, 0x0010),  # Patient's Name
    (0x0010, 0x0020),  # Patient ID
    (0x0010, 0x0030),  # Patient's Birth Date
    (0x0010, 0x1040),  # Patient's Address
    (0x0010, 0x2160),  # Ethnic Group
    (0x0008, 0x0080),  # Institution Name
    (0x0008, 0x0081),  # Institution Address
    (0x0008, 0x0090),  # Referring Physician's Name
    (0x0008, 0x1050),  # Performing Physician's Name
]

def anonymize_mri_file(input_path: str, output_path: str, pseudo_id: str = "ANON_MR_ROUTED"):
    try:
        # Load the DICOM file
        ds = pydicom.dcmread(input_path)
        
        # Verify it is an MRI Modality instance
        if ds.get("Modality", "UNKNOWN") != "MR":
            print(f"[WARN] Non-MR file skipped: {input_path}")
            return False

        # Safely remove identifying tags
        for tag in TAGS_TO_DELETE:
            if tag in ds:
                del ds[tag]

        # Inject pseudonymized baseline metadata 
        ds.PatientName = pseudo_id
        ds.PatientID = pseudo_id
        
        # Save structural meta element formatting safely
        ds.file_meta.TransferSyntaxUID = ds.file_meta.TransferSyntaxUID
        ds.save_as(output_path, write_like_original=False)
        print(f"[SUCCESS] Anonymized: {os.path.basename(input_path)} -> {output_path}")
        return True

    except Exception as e:
        print(f"[ERROR] Failed processing {input_path}: {str(e)}")
        return False

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python anonymize.py <input_file.dcm> <output_file.dcm> [pseudo_id]")
        sys.exit(1)
        
    pid = sys.argv[3] if len(sys.argv) > 3 else "ANON_MR_ROUTED"
    anonymize_mri_file(sys.argv[1], sys.argv[2], pid)
