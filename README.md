# AutoSOC — Autonomous SOC Agent Team

A 3-agent SOC analyst team built with **CrewAI** and an LLM backend. Feed it logs, it triages, investigates, and writes the incident report — the way a real Tier 1 → Tier 2 → reporting workflow runs in a SOC.

**🔴 Live demo:** [soc-agents.onrender.com](https://soc-agents.onrender.com)
> Hosted on Render's free tier — the first request after a period of inactivity can take 30–60 seconds to wake up.

## What This Does

Point AutoSOC at a set of log files (SSH auth logs, firewall logs, etc.) and it runs a three-agent pipeline that mimics a real SOC workflow:

1. **Monitor** reads the raw logs and flags anything suspicious — failed logins, port scans, unusual connections.
2. **Investigator** takes every flagged indicator, checks it against a threat intel feed, and assigns a severity rating and a MITRE ATT&CK technique.
3. **Reporter** writes it all up as a clean, structured incident report and saves it to disk.

The whole run streams live to a browser dashboard, so you can watch each agent think, call its tools, and hand off to the next one — nothing on the dashboard is faked or replayed.

### Example Output

Given the included sample logs, a run produces a report like this:

> **Executive Summary**
> Multiple malicious activities, including brute-force attacks and active scanning, were detected targeting our systems. A critical incident involved a successful root account login from a known brute-force botnet node (185.220.101.47), indicating a severe compromise. Other activities include SSH scanning from a Tor exit node and brute-force attempts from an unknown IP.

| Indicator | Activity | Severity | MITRE Technique |
|---|---|---|---|
| 185.220.101.47 | Successful login for user root after brute-force attempts | Critical | T1078 - Valid Accounts |
| 185.220.101.47 | Port scan detected | High | T1595 - Active Scanning |
| 45.155.205.233 | Multiple failed SSH login attempts for invalid users (SSH scanning) | Medium | T1110 - Brute Force |
| 45.155.205.233 | Repeated SYN packets to port 22 (targeted scan/brute-force) | Medium | T1595 - Active Scanning |
| 198.51.100.22 | Multiple failed SSH login attempts for user root (brute-force) | Medium | T1110 - Brute Force |

...followed by numbered, specific remediation steps (disable the compromised account, block the malicious IPs at the firewall, enforce MFA, harden SSH config, etc.) — not generic advice, but steps tied directly to what was found.

---

## Table of Contents

- [What This Does](#what-this-does)
- [Architecture](#architecture)
- [Live Dashboard](#live-dashboard)
- [Setup](#setup-local-or-vps)
- [Running It](#running-it)
- [Deploying on Render](#deploying-on-render)
- [Deploying on a VPS](#deploying-on-a-vps-without-touching-your-other-projects)
- [Customizing the Demo](#customizing-the-demo)
- [Troubleshooting](#troubleshooting)
- [Why This Is a Good Portfolio Piece](#why-this-is-a-good-portfolio-piece)

---

## Architecture

```
sample_logs/*.log
       │
       ▼
[Monitor Agent]        Tier 1: reads raw logs, flags anything suspicious
       │
       ▼
[Investigator Agent]   Tier 2: checks each flagged indicator against a
       │                threat intel feed, assigns severity + MITRE ATT&CK
       ▼
[Reporter Agent]       Writes the final markdown incident report,
                        saves it to reports/
```

All three agents run through CrewAI's LLM wrapper. The threat intel feed (`data/threat_feed.json`) is a small local JSON file standing in for a real source like AbuseIPDB or VirusTotal — swap it out for a real API call in `src/tools.py` (`threat_intel_lookup`) whenever you want to make this live instead of demo-data.

---

## Live Dashboard

The `web/` folder contains a FastAPI backend + live dashboard (`web/static/index.html`) that streams each agent's status, tool calls, and findings to the browser in real time over Server-Sent Events — nothing on it is simulated.

**Try it live:** [soc-agents.onrender.com](https://soc-agents.onrender.com)

To run it locally, see [Running It](#running-it) below.

---

## Setup (local or VPS)

```bash
cd autosoc-crew
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
nano .env   # paste in your API key
```

---

## Running It

### CLI mode

```bash
# one-shot run against the included sample logs
python main.py

# point it at your own logs
python main.py --logs /var/log/auth.log /var/log/syslog

# continuous monitoring mode, re-runs every 5 minutes
python main.py --watch 300
```

Each run prints the full incident report to the terminal and also saves a timestamped copy to `reports/`.

### Dashboard mode

```bash
python -m uvicorn web.app:app --reload --port 8000
```

Then open `http://localhost:8000` in your browser.

---

## Deploying on Render

This repo is set up to deploy directly to [Render](https://render.com) as a web service.

1. Push the repo to GitHub.
2. On Render: **New +** → **Web Service** → connect your GitHub repo.
3. Configure:

   | Setting | Value |
   |---|---|
   | Build Command | `pip install -r requirements.txt` |
   | Start Command | `uvicorn web.app:app --host 0.0.0.0 --port $PORT` |

4. Add an environment variable for your API key (e.g. `GEMINI_API_KEY` or `GROQ_API_KEY`, matching whichever provider `src/agents.py` is configured for).
5. Pin your Python version with a `.python-version` file in the repo root (Render's deprecated `runtime.txt` is ignored):

   ```
   3.13.7
   ```

6. Deploy. Free tier instances spin down after inactivity, so the first request after idle time will be slow to respond — this is expected.

---

## Deploying on a VPS (without touching your other projects)

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

# (optional) keep the dashboard running in the background
nohup python -m uvicorn web.app:app --host 0.0.0.0 --port 8000 > autosoc.log 2>&1 &
```

The venv keeps all dependencies isolated from whatever else is on the box, so it won't conflict with other projects.

---

## Customizing the Demo

- `sample_logs/auth.log` and `sample_logs/network.log` are synthetic but realistic: SSH brute-force from a flagged IP, a port scan, and a C2-style outbound callback. The IPs in those logs are deliberately seeded into `data/threat_feed.json` so the Investigator agent gets real "hits" during the demo.
- Add more indicators to `data/threat_feed.json` and more log lines to `sample_logs/` to make the demo richer.
- `src/agents.py` has each agent's role/goal/backstory if you want to tune their behavior or add a 4th agent (e.g. a Responder agent that drafts containment actions).

---

## Troubleshooting

**`python web/app.py` runs and exits immediately with no output**
This file defines a FastAPI `app` object but doesn't start a server on its own. Launch it with uvicorn instead:
```bash
python -m uvicorn web.app:app --reload --port 8000
```

**`localhost:8000` refuses to connect**
Nothing is listening on that port yet — the uvicorn command above needs to be running in an active terminal first.

**API errors / connection or quota issues**
Free-tier LLM APIs enforce rate limits that vary by model and change over time. If you're hitting them:
- Check your provider's live dashboard for current limits (e.g. [Google AI Studio](https://aistudio.google.com/rate-limit) for Gemini).
- Try a lighter/faster model variant, which typically has higher free-tier request limits than larger models.
- Consider switching providers — the model and key are both read from environment variables in `src/agents.py`, so swapping providers (e.g. to Groq) is a small, contained change.

**Render build fails with a Python version / dependency resolution error**
Render's `runtime.txt` support is deprecated. Use a `.python-version` file in the repo root instead (see [Deploying on Render](#deploying-on-render)), or set the `PYTHON_VERSION` environment variable directly in the Render dashboard.

---

## Why This Is a Good Portfolio Piece

It demonstrates log analysis, threat intel correlation, MITRE ATT&CK mapping, multi-agent orchestration, and automated reporting — all of which map directly onto what a SOC Tier 1/2 analyst actually does day to day. Pairs well with TryHackMe SOC Level 1 material on your resume.
