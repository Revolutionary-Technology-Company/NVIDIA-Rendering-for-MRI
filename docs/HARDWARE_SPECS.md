# 🖥️ Hardware Specification & Infrastructure Architecture Sheet

**System Blueprint:** Multi-Modality Enterprise Edge Hub (MRI / CT / US)  
**Target Deployment Context:** On-Premise Hospital Datacenter / Radiology Server Closet  
**Baseline GPU Target:** 1x NVIDIA RTX 6000 Ada Generation (48GB VRAM)

---

## 🏎️ Core Hardware Requirements Matrix

When scaling and replicating this processing node to other clinics, use these exact component specifications to guarantee the throughput targets verified in our stress tests:

| Component | Minimum Specification (Outpatient Clinic) | Recommended Specification (Regional Trauma Hub) |
| :--- | :--- | :--- |
| **GPU Accelerator** | 1x NVIDIA RTX 6000 Ada (48GB GDDR6 ECC) | 1x NVIDIA RTX 6000 Ada (Dual-GPU path if scaling CT load) |
| **Host CPU** | AMD EPYC 24-Core or Intel Xeon 16-Core | AMD EPYC 32-Core or Intel Xeon 24-Core (High Base Clock) |
| **System RAM** | 128GB DDR5 ECC Registered | 256GB DDR5 ECC Registered |
| **Storage Architecture** | 1TB NVMe M.2 SSD (Read: >3500 MB/s) | 2TB Enterprise NVMe PCIe Gen 4 (Read/Write: >7000 MB/s) |
| **PCIe Interface Slot** | PCIe Gen 4.0 x16 mechanical & electrical | PCIe Gen 4.0/5.0 x16 (Direct CPU lane connection) |
| **Power Supply (PSU)** | 850W 80+ Gold Certified | 1200W 80+ Platinum Redundant Hot-Swap (Server Chassis) |
| **Network Interface Card**| 1x 1Gbps RJ45 Base-T (Dedicated VLAN) | 2x 10Gbps SFP+ Fiber Link (Separate Ingestion/PACS tracks) |

---

## ⚡ Detailed Component Breakdown & Rationale

### 1. GPU: NVIDIA RTX 6000 Ada Generation
* **VRAM Capacity:** 48GB of dedicated GDDR6 memory is strictly required to accommodate simultaneous, large volumetric datasets (e.g., 500+ slices of high-resolution 512x512 Emergency Dept CT scans alongside 300+ frame Ultrasound Cine-Loops).
* **ECC Memory Activation:** Error Correction Code (ECC) **must remain enabled** via the NVIDIA Control Panel or driver terminal. This prevents random memory bit-flips caused by system environment background radiation, ensuring diagnostic computation data remains error-free.
* **Architecture Note:** Do **not** substitute with consumer-grade hardware (e.g., RTX 4090) due to enterprise cooling limitations, lack of formal hardware vendor virtualization hooks, and absent medical system warranty provisions.

### 2. Host CPU: High Core Count & Multi-Process Bandwidth
* **Multicore Allocation:** Because our pipeline relies on Python's `multiprocessing` library and asynchronous `Pool` arrays (`reconstruct_mri_multicore.py`), a minimum of 16-24 logical cores is required.
* **Task Division:** The CPU acts as the primary traffic controller—simultaneously parsing individual binary DICOM data file headers, verifying spatial orientation vectors, and extracting raw pixel arrays to load into GPU memory registers.

### 3. Storage Layer: NVMe I/O Throughput
* **SLA Bottleneck Mitigation:** Medical scanner arrays write data to disk space rapidly. Traditional mechanical hard drives or entry-level SATA SSDs will cause a bottleneck during heavy clinical workloads. 
* **Write Endurance:** High-endurance enterprise-class NVMe drives ensure that the shared Docker volume containers (`/workspace/incoming_dicom`) can ingest, stage, process, and delete thousands of temporary voxel array files daily without data degradation or cell write-wear failures.

---

## 🎛️ Power, Thermal, & Rack Space Guidelines

When handing off infrastructure deployment requests to your hospital's Datacenter Operations or Facility Management teams, provide these absolute thermal parameters:

* **Form Factor:** 4U Rackmount Server Chassis or Dedicated Enterprise Tower Workstation (e.g., Dell Precision 7960 Rack or equivalent Supermicro deployment blade).
* **Thermal Output:** The NVIDIA RTX 6000 Ada possesses a Total Board Power (TBP) rating of **300 Watts**. Ensure the server rack enclosure maintains continuous chilled airflow (`<22°C` ambient inlet temperature).
* **GPU Power Connectors:** Requires 1x 16-pin PCIe Gen 5.0 (12VHPWR) power cable or dual 8-pin to 16-pin official factory adapters. Do not use unvetted third-party splitters.

---

## 🔒 Network Infrastructure Topography

To protect the server node from unauthorized network lateral movement while maximizing data ingestion speed, enforce the following port configuration rules:

[ HOSPITAL VLANS ] [ EDGE NODE PORTS ]\
┌────────────────┐ ┌─────────────────┐\
│ Radiology VLAN ├─────(DICOM Ingestion)────>│ Port 11104 │ (Orthanc C-STORE)\
└────────────────┘ └─────────────────┘\
┌────────────────┐ ┌─────────────────┐\
│ Biomedical IT ├─────(Dashboard View)─────>│ Port 9920 │ (Nginx Intranet Proxy)\
└────────────────┘ └─────────────────┘\
┌─────────────────┐\
│ Port 443 (Out) │────(TLS Tunnel)───> [ Cloud PACS ]\
└─────────────────┘ [[1](https://docs-cortex.paloaltonetworks.com/r/Cortex-CLOUD/Cortex-Cloud-Runtime-Security-Documentation/XDR-Collector-machine-requirements-and-supported-operating-systems)]

1. **VLAN Segmentation:** The node must sit on an isolated Biomedical / Radiology equipment VLAN.
2. **Dashboard Isolation:** Port `9920` must remain blocked by local firewall definitions to prevent connections originating outside the authorized internal subnet block (`10.0.0.0/8`).
