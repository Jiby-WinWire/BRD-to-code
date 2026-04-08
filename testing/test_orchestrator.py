import os
import shutil
import json
from pathlib import Path
import pytest

# Set up test paths
TEST_DIR = Path(__file__).parent
SAMPLE_BRD = TEST_DIR / "sample_brd.json"
OUTPUT_DIR = TEST_DIR / "output"

# Import orchestrator main
import sys
sys.path.insert(0, str((TEST_DIR.parent / "src" / "agents").resolve()))
from orchestrator import main as orchestrator_main

def setup_module(module):
    if OUTPUT_DIR.exists():
        shutil.rmtree(OUTPUT_DIR)
    OUTPUT_DIR.mkdir(exist_ok=True)

def test_orchestrator_pipeline():
    # Copy sample BRD to project root as expected by orchestrator
    shutil.copy(SAMPLE_BRD, TEST_DIR.parent / "sample_brd.json")
    try:
        orchestrator_main()
        # Check output files
        out_files = list((TEST_DIR.parent / "output").glob("*.py"))
        assert out_files, "No code files generated."
        # Check for at least one test file
        test_files = [f for f in out_files if "test" in f.name]
        assert test_files, "No test files generated."
        # Optionally, check for validation pass in orchestrator logs
    finally:
        # Clean up
        if (TEST_DIR.parent / "sample_brd.json").exists():
            os.remove(TEST_DIR.parent / "sample_brd.json")
