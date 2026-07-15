# AutoSOC - Autonomous SOC Agent Team

A 3-agent SOC analyst team built with CrewAI and Gemini. Feed it logs,
it triages, investigates, and writes the incident report, the way a
real Tier 1 -> Tier 2 -> reporting workflow runs in a SOC.

## Architecture

```
sample_logs/*.log
       |
       v
[Monitor Agent]        Tier 1: reads raw logs, flags anything suspicious
       |
       v
[Investigator Agent]   Tier 2: checks each flagged indicator against a
       |                threat intel feed, assigns severity + MITRE ATT&CK
       v
[Reporter Agent]       Writes the final markdown incident report,
                        saves it to reports/
```

All three agents run on Gemini (via CrewAI's LLM wrapper). The threat
intel feed (`data/threat_feed.json`) is a small local JSON file standing
in for a real source like AbuseIPDB or VirusTotal, swap it out for a real
API call in `src/tools.py` (`threat_intel_lookup`) whenever you want to
make this live instead of demo-data.

## Setup (local or VPS)

```bash
cd autosoc-crew
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
nano .env   # paste in your GEMINI_API_KEY
```

## Run it

```bash
# one-shot run against the included sample logs
python main.py

# point it at your own logs
python main.py --logs /var/log/auth.log /var/log/syslog

# continuous monitoring mode, re-runs every 5 minutes
python main.py --watch 300
```

Each run prints the full incident report to the terminal and also saves
a timestamped copy to `reports/`.

## Deploying on your VPS without touching your other projects

```bash
mkdir -p ~/projects/autosoc-crew
# copy/scp the autosoc-crew folder contents into ~/projects/autosoc-crew
cd ~/projects/autosoc-crew
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env && nano .env

# run it once to confirm it works
python main.py

# (optional) keep it running in the background with watch mode
nohup python main.py --watch 300 > autosoc.log 2>&1 &
```

The venv keeps all dependencies isolated from whatever else is on the
box, so it won't conflict with your other half-finished projects.

## Customizing the demo

- `sample_logs/auth.log` and `sample_logs/network.log` are synthetic
  but realistic: SSH brute-force from a flagged IP, a port scan, and a
  C2-style outbound callback. The IPs in those logs are deliberately
  seeded into `data/threat_feed.json` so the Investigator agent gets
  real "hits" during the demo.
- Add more indicators to `data/threat_feed.json` and more log lines to
  `sample_logs/` to make the demo richer.
- `src/agents.py` has each agent's role/goal/backstory if you want to
  tune their behavior or add a 4th agent (e.g. a Responder agent that
  drafts containment actions).

## Why this is a good portfolio piece

It demonstrates: log analysis, threat intel correlation, MITRE ATT&CK
mapping, multi-agent orchestration, and automated reporting, all of
which map directly onto what a SOC Tier 1/2 analyst actually does day
to day. Pairs well with TryHackMe SOC Level 1 material on your resume.
# Soc_agents_system
# Soc_agents_system
