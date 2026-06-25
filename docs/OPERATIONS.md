# 🏥 Clinical Engineering & Imaging IT On-Call Operations Runbook

**System Designation:** NVIDIA RTX 6000 Ada MRI Automated Edge Pipeline  
**Production Host Interface Port:** `9920` (Intranet Dashboard)  
**Edge DICOM Target AET:** `NVIDIA_MRI_PROC` (Port `11104`)  
**SLA Impact Level:** Tier 2 Clinical Infrastructure (Delays impact Cloud PACS availability)

---

## 🚨 Immediate Triage Steps (When an Alert Triggers)

When a Slack/Teams alert or high-priority incident ticket triggers, follow this triage path immediately:

1. **Verify Live Dashboard Status**
   Navigate to `http://[RTX_6000_SERVER_IP]:9920` from any computer on the hospital intranet.
   * Check the **Operational SLA Success Rate**.
   * Identify the timestamp and specific error message of the failing sequence batch.

2. **Access the Primary Host Server Context**
   SSH securely into the physical GPU edge rendering node located in the datacenter pool:
   ```bash
   ssh clinical_admin@[RTX_6000_SERVER_IP]
   ```

3. **Check the Master Daemon System Logs**
   Inspect the live automation queue logging file to identify where the sequence stalled:
   ```bash
   tail -n 100 -f /var/log/mri_pipeline_daemon.log
   ```

---

## 🛠️ Troubleshooting Specific Failure Playbooks

### Playbook A: Fast Fourier Transform (FFT) QA Rejection
* **Symptom:** Slack alert warns: `QA Failure: Image matrix motion limits breached.`
* **Root Cause:** The patient moved significantly inside the Siemens 3T or legacy Avanto bore, or a metallic implant caused massive radiofrequency field distortion.
* **Resolution Protocol:**
  1. The raw un-vetted DICOM study has been safely quarantined in `/workspace/error_spool` to keep the primary data tracks clear.
  2. Locate the patient's ID and contact the on-duty MRI Technologist at the respective scanner console.
  3. Inform them that the edge QA system detected severe geometric motion degradation and request that they rerun the pulse sequence if the patient is still on the table.

### Playbook B: NVIDIA Driver / GPU Core Memory Allocation Crash
* **Symptom:** Daemon logs show: `RuntimeError: CUDA out of memory` or `CUDA driver initialization failed`.
* **Root Cause:** A large, multi-echo 3D volume sequence saturated the 48GB VRAM pool, or the NVIDIA kernel driver lost contact with the host hardware container layer.
* **Resolution Protocol:**
  1. Check the physical state, temperature, and memory consumption metrics of the RTX 6000 Ada hardware:
     ```bash
     nvidia-smi
     ```
  2. If memory utilization is locked at 100% even though no scans are active, clear the GPU compute register caches by restarting the processing worker container:
     ```bash
     docker compose restart nvidia-mri-compute
     ```
  3. Verify the container successfully detects the hardware cores by reviewing the startup log output:
     ```bash
     docker logs rtx6000_mri_worker | grep -i "VRAM Pool"
     ```

### Playbook C: Network Transmission Drop (Cloud PACS Ingestion Fail)
* **Symptom:** Local logs show: `SendToModality failed` or dashboard indicates successful local processing but studies are completely missing from the Cloud PACS viewer.
* **Root Cause:** Hospital wide-area network (WAN) internet connectivity dropped, or the Cloud PACS endpoint changed its target Application Entity (AE) routing credentials.
* **Resolution Protocol:**
  1. Verify the local server node can still ping the outbound secure gateway router tunnel:
     ```bash
     ping pacs.revolutionarytech.cloud
     ```
  2. Test the specific DICOM connectivity loop to the Cloud PACS array using the standard `echoscu` validation utility:
     ```bash
     docker exec -it mri_edge_listener echoscu -aec SECURE_CLOUD_PACS pacs.revolutionarytech.cloud 443
     ```
  3. If the verification ping timing reflects an error status, engage the Hospital Enterprise Networking On-Call Team to verify port `443` outbound firewall exceptions are intact.

---

## 🔄 Disaster Recovery: Complete Pipeline Stack Restart

If the entire pipeline architecture locks up or fails to clear files from the incoming directory cache, perform a complete hard initialization reset of the container network fabric:

```bash
# Navigate to the repository root deployment folder
cd /home/clinical_admin/NVIDIA-REndering-for-MRI/

# Force stop the containers and purge corrupted network interfaces
docker compose down

# Re-initialize the storage volumes and launch the processing stack cleanly
docker compose up -d

# Verify all core infrastructure layers are reporting online status
docker compose ps
```

---

## 📞 Escalation Matrix

If the pipeline cannot be restored to operational standards within **15 minutes** of a hard stack restart, escalate the incident in the following sequence:

| Support Tier | Contact Destination | Responsibility Matrix |
| :--- | :--- | :--- |
| **Tier 1 (Internal)** | On-Call Clinical Engineer / PACS Admin | Local OS triage, hardware power cycles, local router checks. |
| **Tier 2 (Internal)** | Corporate Enterprise Security / Firewall Team | Network routing loops, WAN infrastructure port blocks. |
| **Tier 3 (External)** | NVIDIA Enterprise AI Support Team | CUDA Toolkit conflicts, RTX 6000 Ada core hardware faults. |
