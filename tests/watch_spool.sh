#!/bin/bash
# ==============================================================================
# Revolutionary Technology Company - MRI Pipeline Automation Daemon with Metrics Hooks
# Monitors incoming spool volumes, runs processing pipelines, and writes metrics.json.
# ==============================================================================

WATCH_DIR="/workspace/incoming_dicom"
PROCESSED_DIR="/workspace/processed_output"
PIPELINE_SCRIPT="/workspace/pipeline/pipelines/reconstruct_mri_multicore.py"
METRICS_SCRIPT="/workspace/pipeline/pipelines/track_metrics.py"
SETTLE_TIME_SECONDS=5
LOG_FILE="/var/log/mri_pipeline_daemon.log"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] 🚀 Starting Auditable MRI Pipeline Watch Daemon..." | tee -a "$LOG_FILE"

mkdir -p "$WATCH_DIR" "$PROCESSED_DIR"

while true; do
    if [ "$(ls -A "$WATCH_DIR" 2>/dev/null)" ]; then
        INITIAL_SIZE=$(du -sb "$WATCH_DIR" | awk '{print $1}')
        sleep "$SETTLE_TIME_SECONDS"
        CURRENT_SIZE=$(du -sb "$WATCH_DIR" | awk '{print $1}')
        
        if [ "$INITIAL_SIZE" -eq "$CURRENT_SIZE" ] && [ "$CURRENT_SIZE" -gt 0 ]; then
            # Count the files precisely before sending to the processing array
            TOTAL_FILES=$(ls -1 "$WATCH_DIR" | wc -l)
            
            echo "[$(date '+%Y-%m-%d %H:%M:%S')] ✅ Volume stabilized. Processing $TOTAL_FILES files..." >> "$LOG_FILE"
            
            # Start tracking the high-precision processing duration
            START_TIME=$(date +%s.%N)
            
            python3 "$PIPELINE_SCRIPT" "$WATCH_DIR" "$PROCESSED_DIR" >> "$LOG_FILE" 2>&1
            EXIT_CODE=$?
            
            END_TIME=$(date +%s.%N)
            RUN_DURATION=$(echo "$END_TIME - $START_TIME" | bc 2>/dev/null || awk "BEGIN {print $END_TIME - $START_TIME}")

            if [ $EXIT_CODE -eq 0 ]; then
                rm -rf "$WATCH_DIR"/*
                # Log success matrix metrics
                python3 "$METRICS_SCRIPT" "SUCCESS" "$TOTAL_FILES" "$RUN_DURATION"
                echo "[$(date '+%Y-%m-%d %H:%M:%S')] 🎉 Pipeline processing logged into metrics.json" >> "$LOG_FILE"
            else
                echo "[$(date '+%Y-%m-%d %H:%M:%S')] ❌ Pipeline failed. Redirecting to error array." >> "$LOG_FILE"
                mkdir -p "/workspace/error_spool"
                mv "$WATCH_DIR"/* "/workspace/error_spool/"
                
                # Log failure metrics matrix
                python3 "$METRICS_SCRIPT" "FAILURE" "$TOTAL_FILES" "$RUN_DURATION" "Pipeline processing error: Exit code $EXIT_CODE"
            fi
        fi
    fi
    sleep 3
done
