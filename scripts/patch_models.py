#!/usr/bin/env python3
"""
patch_models.py — ClawBot openclaw.json model stack updater
Run as: sudo -u clawbot python3 /home/clawbot/.openclaw/scripts/patch_models.py

Last updated: 2026-06-22
Reflects live config on MS-01 (leo-paz-MS-10-Venus)
"""

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

CONFIG_PATH = Path("/home/clawbot/.openclaw/openclaw.json")
BACKUP_PATH = CONFIG_PATH.parent / f"openclaw.json.bak-{datetime.now().strftime('%Y%m%d-%H%M%S')}"

# ── Load ──────────────────────────────────────────────────────────────────────
with open(CONFIG_PATH, "r", encoding="utf-8") as f:
    cfg = json.load(f)

# ── Backup ────────────────────────────────────────────────────────────────────
shutil.copy2(CONFIG_PATH, BACKUP_PATH)
print(f"✅ Backup written: {BACKUP_PATH}")

defaults = cfg["agents"]["defaults"]

# ── 1. Primary model ──────────────────────────────────────────────────────────
defaults["model"]["primary"] = "openai/gpt-5.5"
print("✅ Primary model set: openai/gpt-5.5")

# ── 2. Fallback chain ─────────────────────────────────────────────────────────
# gpt-5.5 removed from fallbacks (was duplicate of primary — bug in prior config)
# claude-cli removed (OAuth expires ~6h, breaks cron)
# Order: mini → local reasoning → local fast → local deep reasoning → local coding → adv coding
defaults["model"]["fallbacks"] = [
    "openai/gpt-5.4-mini",
    "openrouter/moonshotai/kimi-k2.6",
    "openrouter/google/gemini-2.5-flash",
    "ollama/qwen3:14b",
    "ollama/gemma4:e4b",
    "ollama/deepseek-r1:14b",
    "ollama/qwen2.5-coder:14b",
    "ollama/devstral:24b",
    "openrouter/auto",
]
print("✅ Fallback chain updated")

# ── 3. Models block — rebuild clean ───────────────────────────────────────────
# Removed dead entries: claude-opus-4-6, claude-opus-4-5, claude-sonnet-4-5
# Kept anthropic/* (not claude-cli/*) — these use the anthropic provider, not CLI OAuth
defaults["models"] = {
    "openai/gpt-5.5":                     {"alias": "standard", "agentRuntime": {"id": "codex"}},
    "openai/gpt-5.4-mini":                {"alias": "mini", "agentRuntime": {"id": "codex"}},
    "openai/chat-latest":                 {"alias": "instant", "agentRuntime": {"id": "codex"}},
    "openrouter/moonshotai/kimi-k2.6":    {"alias": "kimi"},
    "openrouter/google/gemini-2.5-flash": {"alias": "gemini-flash"},
    "openrouter/auto":                    {"alias": "auto"},
    "ollama/qwen3:14b":                   {"alias": "local-reasoning"},
    "ollama/gemma4:e4b":                  {"alias": "local-fast"},
    "ollama/gemma4:12b":                  {"alias": "local-ingest"},
    "ollama/deepseek-r1:14b":             {"alias": "local-reasoning-deep"},
    "ollama/qwen2.5-coder:14b":           {"alias": "local-coding"},
    "ollama/devstral:24b":                {"alias": "adv-coding"},
    "ollama/nomic-embed-text":            {"alias": "embed"},
}
print("✅ Models block rebuilt (removed 3 dead entries)")

# ── 4. Ollama provider — preserve api and baseUrl ────────────────────────────
# OpenClaw upgrades sometimes reset api to "openai-responses" — enforce "ollama"
if "models" not in cfg:
    cfg["models"] = {}
if "providers" not in cfg["models"]:
    cfg["models"]["providers"] = {}
if "ollama" not in cfg["models"]["providers"]:
    cfg["models"]["providers"]["ollama"] = {}

cfg["models"]["providers"]["ollama"]["api"] = "ollama"
cfg["models"]["providers"]["ollama"]["baseUrl"] = "http://127.0.0.1:11434"
print("✅ Ollama provider: api=ollama, baseUrl=http://127.0.0.1:11434")

# ── 5. thinkingDefault ────────────────────────────────────────────────────────
defaults["thinkingDefault"] = "low"
print("✅ thinkingDefault: low")

# ── 6. Update meta timestamp ──────────────────────────────────────────────────
cfg["meta"]["lastTouchedAt"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")
print("✅ Meta timestamp updated")

# ── Write ─────────────────────────────────────────────────────────────────────
with open(CONFIG_PATH, "w", encoding="utf-8") as f:
    json.dump(cfg, f, indent=2, ensure_ascii=False)
    f.write("\n")

print(f"✅ Written: {CONFIG_PATH}")

print("\nAlias summary:")
for model, v in defaults["models"].items():
    alias = v.get("alias", "(no alias)")
    print(f"  {alias:25s} → {model}")

print("\nFallback chain:")
print(f"  #0 (primary): {defaults['model']['primary']}")
for i, m in enumerate(defaults["model"]["fallbacks"], 1):
    print(f"  #{i}: {m}")

print("\nDone. Restart openclaw.service to apply.")
print("  sudo systemctl restart openclaw.service")
