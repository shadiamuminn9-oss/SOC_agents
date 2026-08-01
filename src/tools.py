"""
Custom tools for the AutoSOC agent crew.

- read_log_file: pulls raw log lines off disk for the Monitor agent
- threat_intel_lookup: checks an IP or file hash against a local IOC feed
  (stand-in for VirusTotal / AbuseIPDB - swap in a real API later if you want)
- write_incident_report: saves the Reporter agent's final output as a
  timestamped markdown file in reports/
"""

import json
import os
from datetime import datetime

from crewai.tools import tool

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
THREAT_FEED_PATH = os.path.join(BASE_DIR, "data", "threat_feed.json")
REPORTS_DIR = os.path.join(BASE_DIR, "reports")


@tool("Read Log File")
def read_log_file(file_path: str) -> str:
    """Reads a log file from disk and returns its raw contents as text.
    Pass the path to a log file (e.g. sample_logs/auth.log)."""
    if not os.path.isabs(file_path):
        file_path = os.path.join(BASE_DIR, file_path)
    if not os.path.exists(file_path):
        return f"ERROR: log file not found at {file_path}"
    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()
    return content if content.strip() else "ERROR: log file is empty"


@tool("Threat Intel Lookup")
def threat_intel_lookup(indicator: str) -> str:
    """Looks up a single indicator (IP address or file hash) against the
    local threat intelligence feed. Returns match details (threat type,
    confidence, first seen) if found, or a clean-record message if not."""
    indicator = indicator.strip()
    if not os.path.exists(THREAT_FEED_PATH):
        return "ERROR: threat feed not found"

    with open(THREAT_FEED_PATH, "r") as f:
        feed = json.load(f)

    for entry in feed.get("indicators", []):
        if entry["value"].lower() == indicator.lower():
            return (
                f"MATCH FOUND for {indicator}: "
                f"type={entry['type']}, threat={entry['threat']}, "
                f"confidence={entry['confidence']}, "
                f"first_seen={entry['first_seen']}, "
                f"mitre_technique={entry.get('mitre_technique', 'unknown')}"
            )

    return f"No match for {indicator} in threat feed (appears clean)."


@tool("Write Incident Report")
def write_incident_report(content: str) -> str:
    """Writes the final incident report content to a timestamped markdown
    file in the reports/ directory. Returns the path it was saved to."""
    os.makedirs(REPORTS_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = os.path.join(REPORTS_DIR, f"incident_report_{timestamp}.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return f"Report saved to {path}"
