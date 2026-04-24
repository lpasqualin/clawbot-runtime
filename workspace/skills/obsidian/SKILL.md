---
name: obsidian
description: Read and write notes in Leo's Obsidian vault at /home/leo-paz/obsidian-vault. Use for project notes, research, briefs, daily notes, and any long-form context storage. Always prefer Obsidian for anything that needs to persist beyond a task.
metadata:
  openclaw:
    primaryEnv: OBSIDIAN_API_KEY
---
# Obsidian Vault

Leo's vault is at /home/leo-paz/obsidian-vault. The local REST API runs at https://localhost:27124.

## Auth
Every request requires:
Authorization: Bearer $OBSIDIAN_API_KEY

TLS is self-signed — always set NODE_TLS_REJECT_UNAUTHORIZED=0 for node, or use curl -sk.

## Vault structure
- 00 - Command/ — master index, priorities, decisions
- 10 - Leo/ — personal context
- 20 - Career & Positioning/ — portfolio, bio, positioning
- 30 - BBS/ — client work, research, strategy
- 40 - Agent OS/ — architecture, specs
- 50 - ClawBot & Agents/ — agent config, memory, ops
- 60 - Farah/ — Farah/Starlight work
- 70 - Assets & Products/ — products, tools

## Endpoints

List all files:
curl -sk https://localhost:27124/vault/ -H "Authorization: Bearer $OBSIDIAN_API_KEY"

Read a file:
curl -sk https://localhost:27124/vault/path/to/file.md -H "Authorization: Bearer $OBSIDIAN_API_KEY"

Write a file (create or overwrite):
curl -sk -X PUT https://localhost:27124/vault/path/to/file.md \
  -H "Authorization: Bearer $OBSIDIAN_API_KEY" \
  -H "Content-Type: text/markdown" \
  --data-binary @/tmp/content.md

Append to a file:
curl -sk -X PATCH https://localhost:27124/vault/path/to/file.md \
  -H "Authorization: Bearer $OBSIDIAN_API_KEY" \
  -H "Content-Type: text/markdown" \
  --data-binary @/tmp/content.md

Delete a file:
curl -sk -X DELETE https://localhost:27124/vault/path/to/file.md \
  -H "Authorization: Bearer $OBSIDIAN_API_KEY"

## Operating rules
- HARD RULE: Never use obsidian-cli binary — it does not exist on this machine. Always use curl against the REST API.
- Always use NODE_TLS_REJECT_UNAUTHORIZED=0 for any node-based requests.
- When writing files, write content to /tmp first, then PUT via curl.
- File paths in the API are relative to the vault root. Example: "30 - BBS/Research/note.md"
- Create parent directories by just writing the file — the API handles it.
- For daily notes, use path: "00 - Command/Daily/YYYY-MM-DD.md"
- Always confirm writes by reading the file back after writing.
