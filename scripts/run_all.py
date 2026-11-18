"""
Master End-to-End Test and Verification Orchestrator
Project: Marketplace Profitability & Fulfillment Leakage Diagnostic

Orchestrates sequential execution of:
  1. Data Pipeline Execution (pipeline/run_pipeline.py)
  2. Isolated Verification Suite (tests/verify_pipeline.py)
  3. Authoritative Documentation Sync Check (scripts/render_readme_tables.py --check)
  4. Comprehensive Pytest Suite (tests/test_audit_fixes.py & tests/test_pipeline.py)

Exit code 0 on complete pass; non-zero if any step fails.
"""

import os
import sys
import time
import subprocess

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

def print_step_header(step_num, title):
    print("\n" + "=" * 70)
    print(f"[{step_num}/4] {title.upper()}")
    print("=" * 70)

def run_step(step_num, title, cmd):
    print_step_header(step_num, title)
    t0 = time.time()
    print(f"Command: {' '.join(cmd)}")
    proc = subprocess.run(cmd, cwd=PROJECT_ROOT)
    elapsed = time.time() - t0
    if proc.returncode != 0:
        print(f"\n[FAILED] Step {step_num} failed with exit code {proc.returncode} ({elapsed:.2f}s)")
        sys.exit(proc.returncode)
    print(f"[PASSED] Step {step_num} completed successfully ({elapsed:.2f}s)")

def main():
    print("=" * 70)
    print(" STARTING COMPLETE END-TO-END PROJECT VERIFICATION")
    print("=" * 70)
    print(f"Python:       {sys.version.split()[0]}")
    print(f"Interpreter:  {sys.executable}")
    print(f"Project Root: {PROJECT_ROOT}")

    start_all = time.time()

    # Step 1: Run Data Pipeline
    run_step(1, "Executing Data Pipeline (Ingestion -> Fact -> Views)", [sys.executable, os.path.join(PROJECT_ROOT, "pipeline", "run_pipeline.py")])

    # Step 2: Verification Suite
    run_step(2, "Running Pipeline Verification Gate", [sys.executable, os.path.join(PROJECT_ROOT, "tests", "verify_pipeline.py")])

    # Step 3: Documentation Sync Check
    run_step(3, "Checking Documentation Table Synchronization", [sys.executable, os.path.join(PROJECT_ROOT, "scripts", "render_readme_tables.py"), "--check"])

    # Step 4: Pytest Suite
    run_step(4, "Running Full Pytest Test Suite", [sys.executable, "-m", "pytest", "-v"])

    total_time = time.time() - start_all
    print("\n" + "=" * 70)
    print(f" ALL 4 VERIFICATION STAGES PASSED CLEANLY IN {total_time:.2f}s!")
    print("=" * 70)

if __name__ == "__main__":
    main()
