"""
CLI Entry point to run full evaluation harness for SpotifyCares AI Agent.
Reproduces independent evaluation benchmark v2 metrics.
"""

import sys
import os
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.evaluator import run_evaluation_v2

if __name__ == "__main__":
    t0 = time.time()
    results = run_evaluation_v2()
    t1 = time.time()

    print(f"\n[REPRODUCIBILITY CHECK]: Evaluation completed successfully in {t1-t0:.2f} seconds.")
    print("Results exported to: d:\\Hiver\\data\\evaluation_summary_v2.json")
