"""
Builds and runs the AutoSOC crew: Monitor -> Investigator -> Reporter,
sequential process.
"""

from crewai import Crew, Process

from .agents import investigator_agent, monitor_agent, reporter_agent
from .tasks import build_tasks


def run_soc_crew(log_files: list[str]) -> str:
    tasks = build_tasks(log_files)

    crew = Crew(
        agents=[monitor_agent, investigator_agent, reporter_agent],
        tasks=tasks,
        process=Process.sequential,
        verbose=True,
    )

    result = crew.kickoff()
    return str(result)
