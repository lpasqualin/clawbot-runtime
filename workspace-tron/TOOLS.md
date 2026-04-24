# TOOLS.md — Tron

This file contains environment-specific infrastructure notes.
Skills define how tools work. This file documents THIS system.

## System Paths

- OpenClaw root: /home/clawbot/.openclaw/
- ClawBot workspace: /home/clawbot/.openclaw/workspace
- Vito workspace: /home/clawbot/.openclaw/workspace-vito
- Oracle workspace: /home/clawbot/.openclaw/workspace-oracle
- Tron workspace: /home/clawbot/.openclaw/workspace-tron

## Important Services

- OpenClaw runs as a systemd service
- Ollama runs locally for embeddings / local models
- PostgreSQL + pgvector installed
- Memory service may run on port 9001 (if enabled)

## Responsibilities

You are responsible for:
- Scripts
- Automations
- Scrapers
- API integrations
- System reliability
- Backups (future)
- Monitoring (future)

Do not modify credentials, system services, or firewall rules without ClawBot approval.