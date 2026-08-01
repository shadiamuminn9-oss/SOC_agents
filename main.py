"""
AutoSOC - CLI entry point.

Usage:
    python main.py --logs sample_logs/auth.log sample_logs/network.log
    python main.py --logs sample_logs/auth.log --watch 300   (re-runs every 300s)
"""

import argparse
import os
import time

from dotenv import load_dotenv

load_dotenv()

from src.crew import run_soc_crew  # noqa: E402  (must come after load_dotenv)


def main():
    parser = argparse.ArgumentParser(description="AutoSOC multi-agent SOC crew")
    parser.add_argument(
        "--logs",
        nargs="+",
        default=["sample_logs/auth.log", "sample_logs/network.log"],
        help="Path(s) to log file(s) to analyze",
    )
    parser.add_argument(
        "--watch",
        type=int,
        default=None,
        help="If set, re-run the crew every N seconds (continuous monitoring mode)",
    )
    args = parser.parse_args()

    if not os.getenv("GEMINI_API_KEY"):
        print("ERROR: GEMINI_API_KEY not set. Copy .env.example to .env and add your key.")
        return

    if args.watch:
        print(f"AutoSOC watch mode: re-running every {args.watch}s. Ctrl+C to stop.")
        while True:
            print("\n" + "=" * 60)
            print(f"Run started at {time.strftime('%Y-%m-%d %H:%M:%S')}")
            print("=" * 60)
            result = run_soc_crew(args.logs)
            print("\nFINAL REPORT:\n")
            print(result)
            time.sleep(args.watch)
    else:
        result = run_soc_crew(args.logs)
        print("\n" + "=" * 60)
        print("FINAL REPORT")
        print("=" * 60)
        print(result)


if __name__ == "__main__":
    main()
