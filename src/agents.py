"""
Agent definitions for AutoSOC: a 3-agent SOC team.

  Monitor      -> Tier 1 triage, scans raw logs for suspicious activity
  Investigator -> Tier 2 analysis, correlates flags against threat intel
  Reporter     -> writes the final incident report
"""

import os

from crewai import Agent, LLM

from .tools import read_log_file, threat_intel_lookup, write_incident_report

MODEL = os.getenv("MODEL", "gemini/gemini-2.5-flash")
API_KEY = os.getenv("GEMINI_API_KEY")

llm = LLM(model=MODEL, api_key=API_KEY, temperature=0.2)


monitor_agent = Agent(
    role="SOC Tier 1 Analyst - Log Monitor",
    goal=(
        "Scan raw security logs and flag every suspicious event: failed "
        "logins, brute-force patterns, port scans, unusual process "
        "execution, or anything that deviates from normal activity. "
        "List each flagged event with the relevant IP/hash/user and a "
        "one-line reason it was flagged."
    ),
    backstory=(
        "You are a sharp Tier 1 SOC analyst with years of experience "
        "doing first-pass triage on raw logs. You don't try to fully "
        "investigate anything yourself, you just catch everything that "
        "looks off and hand it up the chain with enough detail that "
        "Tier 2 can act on it immediately."
    ),
    tools=[read_log_file],
    llm=llm,
    verbose=True,
)

investigator_agent = Agent(
    role="SOC Tier 2 Analyst - Threat Investigator",
    goal=(
        "Take the flagged events from the Monitor and investigate each "
        "one. Look up every IP address and file hash against the threat "
        "intel feed. Determine a severity rating (Low/Medium/High/"
        "Critical) for each finding and map it to a MITRE ATT&CK "
        "technique where possible."
    ),
    backstory=(
        "You are a Tier 2 SOC analyst who specializes in correlation and "
        "threat intelligence. Given a list of flagged events, you dig "
        "into each indicator, decide how serious it actually is, and "
        "back up every severity rating with evidence, not vibes."
    ),
    tools=[threat_intel_lookup],
    llm=llm,
    verbose=True,
)

reporter_agent = Agent(
    role="SOC Reporting Analyst",
    goal=(
        "Turn the investigation findings into a clear, professional "
        "incident report: an executive summary, a table of findings with "
        "severity, the evidence behind each, and concrete remediation "
        "steps. Save the final report to disk."
    ),
    backstory=(
        "You write the incident reports that go to management and "
        "clients. You are concise, you lead with the bottom line, and "
        "every recommendation you make is specific and actionable, "
        "never generic advice like 'improve security posture'."
    ),
    tools=[write_incident_report],
    llm=llm,
    verbose=True,
)
