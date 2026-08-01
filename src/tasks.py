"""
Task definitions for AutoSOC. Three tasks, run sequentially, each one
feeding its output into the next agent as context.
"""

from datetime import datetime

from crewai import Task

from .agents import investigator_agent, monitor_agent, reporter_agent


def build_tasks(log_files: list[str]):
    log_list_str = ", ".join(log_files)
    today = datetime.now().strftime("%Y-%m-%d")

    monitor_task = Task(
        description=(
            f"Read and analyze the following log file(s): {log_list_str}. "
            "Use the Read Log File tool on each one. Flag every suspicious "
            "event you find. For each flagged event, output: the source "
            "IP or username involved, a short description of the activity, "
            "and the log file/line it came from."
        ),
        expected_output=(
            "A numbered list of flagged events, each with the relevant "
            "indicator (IP/user/hash) and a one-line reason for the flag."
        ),
        agent=monitor_agent,
    )

    investigator_task = Task(
        description=(
            "For every flagged event from the Monitor, use the Threat "
            "Intel Lookup tool on the relevant IP address or hash. Based "
            "on the lookup result and the nature of the activity, assign "
            "a severity (Low/Medium/High/Critical) and, where applicable, "
            "a MITRE ATT&CK technique. Do not skip any flagged event."
        ),
        expected_output=(
            "A list of investigated findings, each with: indicator, "
            "threat intel result, severity rating, and MITRE technique "
            "if applicable."
        ),
        agent=investigator_agent,
        context=[monitor_task],
    )

    reporter_task = Task(
        description=(
            "Using the investigation findings, write a complete incident "
            f"report in markdown. Use {today} as the report date, do not "
            "guess or invent a different date. Structure: "
            f"# Incident Report header with the date {today}, "
            "## Executive Summary (2-3 sentences), "
            "## Findings (a markdown table: Indicator | Activity | "
            "Severity | MITRE Technique), "
            "## Recommended Remediation (specific, numbered steps). "
            "Then use the Write Incident Report tool to save it to disk, "
            "and return the full report content as your final answer."
        ),
        expected_output=(
            "The complete markdown incident report, plus confirmation of "
            "the file path it was saved to."
        ),
        agent=reporter_agent,
        context=[investigator_task],
    )

    return [monitor_task, investigator_task, reporter_task]
