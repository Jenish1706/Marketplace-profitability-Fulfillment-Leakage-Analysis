# pipeline/logger.py
# Structured Pipeline Run Logger for Marketplace Diagnostic Data Pipeline

import os
import json
import time
from datetime import datetime

class PipelineLogger:
    def __init__(self, log_dir="logs", run_id=None):
        self.log_dir = log_dir
        os.makedirs(self.log_dir, exist_ok=True)
        self.run_id = run_id or datetime.now().strftime("%Y-%m-%d_%H%M%S")
        self.start_time = datetime.now()
        self.start_timestamp = time.time()
        self.end_time = None
        self.duration_seconds = None
        self.status = "PENDING"
        self.stages = []
        self.ingestion_records = []
        self.validation_records = []
        self.errors = []
        self.snapshot = {}

    def print_banner(self, title):
        print("\n" + "=" * 64)
        print(f" {title.upper()}")
        print("=" * 64)

    def log_stage_start(self, stage_name):
        print(f"\n>>> [STAGE START] {stage_name}")

    def log_stage_end(self, stage_name, status="PASS", duration=None, details=None):
        duration_str = f" ({duration:.2f}s)" if duration is not None else ""
        print(f">>> [STAGE {status}] {stage_name}{duration_str}")
        self.stages.append({
            "stage_name": stage_name,
            "status": status,
            "duration_seconds": round(duration, 3) if duration is not None else None,
            "details": details or {}
        })

    def log_ingestion(self, table_name, filename, row_count, status="PASS", duration=None):
        duration_str = f" in {duration:.2f}s" if duration is not None else ""
        print(f"  -> Ingested {table_name:<32} {row_count:>8,} rows  [{status}]{duration_str}")
        self.ingestion_records.append({
            "table_name": table_name,
            "filename": filename,
            "row_count": row_count,
            "status": status,
            "duration_seconds": round(duration, 3) if duration is not None else None
        })

    def log_validation(self, check_name, status="PASS", message=None):
        msg_str = f" - {message}" if message else ""
        print(f"  -> Validation: {check_name:<40} [{status}]{msg_str}")
        self.validation_records.append({
            "check_name": check_name,
            "status": status,
            "message": message
        })

    def log_error(self, stage_name, error_message):
        print(f"\n[ERROR] Stage '{stage_name}' failed: {error_message}")
        self.errors.append({
            "stage_name": stage_name,
            "error_message": str(error_message),
            "timestamp": datetime.now().isoformat()
        })
        self.status = "FAILED"

    def record_snapshot(self, snapshot_dict):
        self.snapshot = snapshot_dict

    def finalize(self, status="SUCCESS"):
        self.status = status
        self.end_time = datetime.now()
        self.duration_seconds = round(time.time() - self.start_timestamp, 2)
        
        # Human-readable summary
        self.print_banner("PIPELINE EXECUTION SUMMARY")
        print(f"Run ID:        {self.run_id}")
        print(f"Status:        {self.status}")
        print(f"Started:       {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Finished:      {self.end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Duration:      {self.duration_seconds} seconds")
        print("\nStage Breakdown:")
        for s in self.stages:
            dur = f"{s['duration_seconds']}s" if s['duration_seconds'] is not None else "N/A"
            print(f"  - {s['stage_name']:<38} {s['status']:<6} ({dur})")

        if self.snapshot:
            print("\nAnalytical Reconciliation Snapshot:")
            for k, v in self.snapshot.items():
                if isinstance(v, float):
                    if "recovery" in k.lower() or "exposure" in k.lower() or "gmv" in k.lower() or (("freight" in k.lower() or "price" in k.lower()) and "pct" not in k.lower()):
                        val_str = f"R$ {v:,.2f}"
                    elif "pct" in k.lower() or "rate" in k.lower():
                        val_str = f"{v:.2f}%"
                    else:
                        val_str = f"{v:.2f}"
                elif isinstance(v, int):
                    val_str = f"{v:,}"
                else:
                    val_str = str(v)
                print(f"  - {k:<28} : {val_str:>16}")

        print("=" * 64)

        # Write machine-readable JSON log
        log_payload = {
            "run_id": self.run_id,
            "status": self.status,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat(),
            "duration_seconds": self.duration_seconds,
            "stages": self.stages,
            "ingestion": self.ingestion_records,
            "validation": self.validation_records,
            "errors": self.errors,
            "snapshot": self.snapshot
        }
        json_path = os.path.join(self.log_dir, f"run_{self.run_id}.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(log_payload, f, indent=2)
        print(f"Machine-readable pipeline log written to: {json_path}")
