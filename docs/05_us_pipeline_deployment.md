# Tutorial 5: Ultrasound (US) Cine-Loop Deconstruction & Spatial Calibration

This guide covers the deployment of the Ultrasound processing track designed to handle moving video clips (Cine-Loops) captured by your **Philips iU22** and portable **Sonosite Bedside Trauma** units.

## 🏗️ Technical Pipeline Workflow

[Philips / Sonosite] ──(Multi-Frame Cine)──> [Local Node Listener]\
│\
(RGB Array Split Loop)\
▼\
[Secure Cloud PACS] <──(Single Frame Series)── [Voxel Calibration Engine]

## 📋 Modality Functional Specifications
Ultrasound dynamic loops (such as cardiac motion paths or RGB color Doppler velocity screens) arrive at the edge node as a single multi-frame DICOM file containing hundreds of overlapping image matrices. 

This pipeline deconstructs the unified matrix block into individual static frames. It then parses the `SequenceOfUltrasoundRegions` structural elements to extract precise physical measurement variables, embedding an audit stamp directly into each output file header.

## 🚀 Setup Steps

### Step 1: Map the Spatial Region Sequence Matrix
Ultrasound systems display distance markers based on localized depth settings. Our script scans the internal parameters to ensure measurements remain consistent inside your Cloud PACS viewer:
* **Tag `(0x0018, 0x6011)`**: `SequenceOfUltrasoundRegions`
* **Sub-Tag `(0x0018, 0x602c)`**: `PhysicalDeltaX` (Physical millimeter dimension per row pixel)
* **Sub-Tag `(0x0018, 0x602e)`**: `PhysicalDeltaY` (Physical millimeter dimension per column pixel)

### Step 2: Deploy Bedside Trauma Nodes
Since your portable Sonosite scanners operate over wireless networks in trauma rooms, ensure your local network router handles packet fragmentation by adjusting the timeout variables inside your edge environment.

### Step 3: Verify the Multi-Frame Split Loop
Execute the verification test profile to ensure multi-frame arrays are split into sequential single instances cleanly:
```bash
python3 -m unittest tests.test_pipeline.TestMultiModalityPipelineE2E.test_us_pipeline_execution
```

---

## 📈 Dashboard Interface Status
Once processed, your ultrasound instances are tagged with `US_FRAME_EXTRACTED_RTX6000` inside their metadata attributes. Running loops update the **Ultrasound Analytics** card component on your port `9920` intranet monitoring dashboard in real-time.
