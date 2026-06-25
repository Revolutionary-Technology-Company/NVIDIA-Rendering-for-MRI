# 🗺️ Radiology Technologist User Guide: Connecting Scanners to the NVIDIA Node

**Target Audience:** Lead MRI Technologists, PACS Administrators, Clinical Engineers  
**Destination Network Target AET:** `NVIDIA_MRI_PROC`  
**Node Server Port:** `11104`  

This clinical operational guide explains how to register our **NVIDIA RTX 6000 Ada Edge Processing Server** on your scanner consoles and how to push a non-clinical Quality Assurance (QA) test phantom to verify the active pipeline.

---

## 🛑 Important Pre-Flight Rules
* **No Live Patients for Initial Test Rings:** Always verify this network pipeline using a standard ACR (American College of Radiology) water/fluid phantom or a system QA sphere before sending live patient sequences.
* **Network Isolation:** Ensure your scanner console is connected to the hospital's internal imaging VLAN. The node will automatically reject connections originating from public or general hospital staff Wi-Fi.

---

## 🛠️ Step 1: Registering the NVIDIA Node on Scanner Consoles

To send images, the NVIDIA node must be added as a designated "Network Remote Destination" (or Application Entity) on each scanner.

### A. Siemens Consoles (Siemens 3T & Siemens Avanto)
1. At the main Siemens console, navigate to the **Syngo/Service** top menu and select **Local Service**.
2. Open the **Configuration** module and select **DICOM Applications** or **Network Nodes**.
3. Click **Add New Node / Target** and input the following exact parameters:
   * **Application Entity (AE) Title:** `NVIDIA_MRI_PROC`
   * **IP Address:** `[Insert_Your_RTX6000_Server_Internal_IP]`
   * **Port Number:** `11104`
   * **Format Profile:** `Storage Provider` or `Standard DICOM Storage`
4. Click **Save / Apply**.
5. Select the newly created `NVIDIA_MRI_PROC` destination and click **Ping / Echo (C-ECHO)**. 
   * *Verification:* If successful, the console will display a green checkmark or text stating `Verification Successful`.

### B. GE Consoles (GE 1.5T Signa Series)
1. On the GE system display dashboard, navigate to the **Browser** page.
2. Select **Network** from the upper dropdown menu options, then choose **Remote Centers / Destinations**.
3. Select **Add Node / Host** and fill out the following properties:
   * **AE Title:** `NVIDIA_MRI_PROC`
   * **IP Address:** `[Insert_Your_RTX6000_Server_Internal_IP]`
   * **Port:** `11104`
4. Set the transfer syntax parameter field preferences to **Explicit VR Little Endian**.
5. Click **Save** and close the configuration utility window.
6. Push the **Test Connection / Ping** interactive hook to confirm the console handshake completes.

---

## 🧪 Step 2: Executing a Non-Clinical Test Phantom Push

Once the network connection passes the test ping, follow these steps to perform an end-to-end data test:

1. **Position the Phantom:** Set up your standard ACR quality assurance water phantom inside the main head or body coil.
2. **Execute a Quick Sequence:** Run a baseline structural localizer followed by an everyday structural sequence (e.g., an Axial T2 or T1 structural sequence).
3. **Open the Image Browser:** Once reconstruction on the scanner console concludes, open your patient database browser directory.
4. **Select the Series:** Highlight the newly completed phantom series volume.
5. **Send/Archive the Scan:**
   * *Siemens:* Right-click the series title, select **Send To**, and choose `NVIDIA_MRI_PROC`.
   * *GE:* Click the series volume checkbox block, click the **Network Transfer / Archive** icon, and select `NVIDIA_MRI_PROC` from the target machine drop-down registry.
6. Click **Send / Transfer**.

---

## 📈 Step 3: Verifying Results in the Cloud PACS

Our automated edge pipeline handles the compute steps instantly. To confirm your phantom sequence successfully bypassed security and quality gates:

1. Open your standard browser on the hospital intranet and navigate to the live pipeline tracking interface: `http://[YOUR_SERVER_IP]:9920`
2. **Check the Log Status:** Confirm that a new success row entry appeared matching your file batch count.
3. **Open Your Cloud PACS Viewer:** Log into your primary cloud-based hospital imaging archive system.
4. **Search for the Test:** Search for Patient ID `ANON_MR_ROUTED`.
5. **Audit Image Attributes:** Open the series viewer window. 
   * Observe that the series title contains `ISOTROPIC_1MM_RTX6000`.
   * Open the volume slice display window. The image coordinates should show uniform layout grids, and the front face profile elements should be blacked out/zeroed out by the spatial defacing privacy guard.

---

## ❓ Technologist Troubleshooting FAQ

* **Q: The scanner console displays a 'Connection Timed Out' error during C-ECHO.**
  * *A:* The pipeline server may be down or processing a heavy back-logged dataset queue. Check if the intranet web page on port `9920` is responsive, or contact a PACS Administrator to verify the local Docker containers are running.
* **Q: The transfer status says 'Completed' on the scanner, but the files never appear in the Cloud PACS.**
  * *A:* The test sequence likely failed our automated Fast Fourier Transform (FFT) clarity checks (e.g., due to extreme noise or incorrect calibration parameters). When this happens, data is isolated in our internal safety sandbox to keep the cloud workspace pristine. Inform the on-call Clinical Engineer to inspect `/var/log/mri_pipeline_daemon.log`.
