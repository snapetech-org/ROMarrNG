#!/usr/bin/env python3
"""Compatibility entry point for the W485-W504 portable bundle verifier."""
from pathlib import Path
import runpy
runpy.run_path(str(Path(__file__).resolve().parents[1] / "verify_window_bundle.py"), run_name="__main__")
