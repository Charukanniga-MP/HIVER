"""
Final Evaluation Runner Script for SpotifyCares AI Support System.
Executes src.final_evaluator to generate data/final_evaluation.json, data/final_evaluation_summary.json, and data/final_failure_analysis.json.
"""

import sys
from src.final_evaluator import run_final_evaluation

if __name__ == "__main__":
    try:
        run_final_evaluation()
    except Exception as e:
        print(f"[ERROR]: Final evaluation execution failed: {e}", file=sys.stderr)
        sys.exit(1)
