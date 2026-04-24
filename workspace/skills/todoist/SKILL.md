---
name: todoist
description: Manage Todoist tasks, Today list, projects, due dates, and task triage. Use when the user asks about Todoist, tasks, planning, reordering work, or productivity.
metadata:
  openclaw:
    primaryEnv: TODOIST_API_KEY
---

# Todoist

Use Todoist whenever the user wants to review, add, complete, move, reschedule, search, or reorganize tasks.

## Execution path

Use `exec` and run the Todoist CLI through `npx` so a global install is not required.

Base command:

```bash
npx -y todoist-ts-cli@^0.2.0
```

## Read commands

```bash
npx -y todoist-ts-cli@^0.2.0 today
npx -y todoist-ts-cli@^0.2.0 tasks
npx -y todoist-ts-cli@^0.2.0 tasks --all
npx -y todoist-ts-cli@^0.2.0 tasks --json
npx -y todoist-ts-cli@^0.2.0 tasks -p "Work"
npx -y todoist-ts-cli@^0.2.0 tasks -f "p1"
npx -y todoist-ts-cli@^0.2.0 search "keyword"
npx -y todoist-ts-cli@^0.2.0 projects
npx -y todoist-ts-cli@^0.2.0 labels
```

## Write commands

```bash
npx -y todoist-ts-cli@^0.2.0 add "Buy groceries"
npx -y todoist-ts-cli@^0.2.0 add "Call dentist" --due "tomorrow"
npx -y todoist-ts-cli@^0.2.0 add "Review PR" --due "today" --priority 1 --project "Work"
npx -y todoist-ts-cli@^0.2.0 add "Triage inbox" --project "Work" --order top
npx -y todoist-ts-cli@^0.2.0 done <id>
npx -y todoist-ts-cli@^0.2.0 reopen <id>
npx -y todoist-ts-cli@^0.2.0 update <id> --due "next week"
npx -y todoist-ts-cli@^0.2.0 move <id> -p "Personal"
npx -y todoist-ts-cli@^0.2.0 delete <id>
npx -y todoist-ts-cli@^0.2.0 comment <task-id> "Note"
```

## Operating rules

- **HARD RULE: Never write raw fetch/HTTP calls to the Todoist API directly. Always use the todoist-ts-cli via npx. The CLI handles API versioning automatically.**
- If the user wants a planning or triage pass, start by reading the relevant tasks first.
- For bulk reorganizing, propose the new structure briefly, then apply it.
- Prefer collapsing finished or mostly-finished projects into one closeout task instead of keeping a whole project on Today.
- Confirm before destructive bulk deletes.
- Use natural language due dates exactly as the user says unless a clearer date is needed.
- If auth fails, say the Todoist token path is still broken and note that this runtime has historically used `TODOIST_API_KEY` as the working path.
- When invoking the CLI, map the key into the token env, for example `TODOIST_API_TOKEN="$TODOIST_API_KEY" npx ...`.

## Today-list triage default

When the user says Today has too much on it:
1. Read Today and overdue tasks.
2. Separate into:
   - must do today
   - should do this week
   - later / backlog
3. Keep Today tight, usually 3 to 5 real tasks.
4. Convert broad projects into one concrete next action when possible.
