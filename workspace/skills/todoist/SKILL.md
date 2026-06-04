---
name: todoist
description: Manage Todoist tasks, Today list, projects, due dates, and task triage. Use when the user asks about Todoist, tasks, planning, reordering work, or productivity.
metadata:
  openclaw:
    primaryEnv: TODOIST_API_KEY
---

# Todoist

Use Todoist whenever the user wants to review, add, complete, move, reschedule, search, or reorganize tasks.

## API version

All direct API calls use **`/api/v1/`**. The old `/rest/v2/` and `/sync/v9/` endpoints return HTTP 410 Gone — never use them.

## Execution path

Use `exec` and run the Todoist CLI through `npx` so a global install is not required.

Base command:

    npx -y todoist-ts-cli@^0.2.0

## Read commands

    npx -y todoist-ts-cli@^0.2.0 today
    npx -y todoist-ts-cli@^0.2.0 tasks
    npx -y todoist-ts-cli@^0.2.0 tasks --all
    npx -y todoist-ts-cli@^0.2.0 tasks --json
    npx -y todoist-ts-cli@^0.2.0 tasks -p "Work"
    npx -y todoist-ts-cli@^0.2.0 tasks -f "p1"
    npx -y todoist-ts-cli@^0.2.0 search "keyword"
    npx -y todoist-ts-cli@^0.2.0 projects
    npx -y todoist-ts-cli@^0.2.0 labels

## Completed tasks

The CLI has no `completed` command. Use the REST API v1 directly — this is the only permitted exception to the no-raw-API rule.

    # Completed tasks — up to 50, most recent first
    curl -s "https://api.todoist.com/api/v1/tasks/completed?limit=50" \
      -H "Authorization: Bearer $TODOIST_API_KEY"

    # Completed today only
    curl -s "https://api.todoist.com/api/v1/tasks/completed?limit=50" \
      -H "Authorization: Bearer $TODOIST_API_KEY" \
      | jq --arg d "$(date +%Y-%m-%d)" \
        '.items[] | select(.completed_at | startswith($d)) | {content, completed_at, task_id}'

    # Completed this week
    curl -s "https://api.todoist.com/api/v1/tasks/completed?limit=50&since=$(date -d 'last monday' +%Y-%m-%d)T00:00:00Z" \
      -H "Authorization: Bearer $TODOIST_API_KEY" \
      | jq '.items[] | {content, completed_at, task_id}'

Response schema:
- `items[]` — array of completed tasks
- `content` — task name
- `task_id` — use for deep link: `https://app.todoist.com/app/task/{task_id}`
- `completed_at` — ISO timestamp

## Active tasks via API (when CLI is insufficient)

    # All active tasks
    curl -s "https://api.todoist.com/api/v1/tasks?limit=200" \
      -H "Authorization: Bearer $TODOIST_API_KEY"

    # Overdue tasks
    curl -s "https://api.todoist.com/api/v1/tasks?filter=overdue&limit=100" \
      -H "Authorization: Bearer $TODOIST_API_KEY"

Response schema (active tasks):
- `results[]` — array of tasks
- `id` — task ID, use for deep link: `https://app.todoist.com/app/task/{id}`
- `content` — task name
- `due.date` — due date (YYYY-MM-DD or datetime)
- `priority` — 4=p1, 3=p2, 2=p3, 1=p4
- `checked` — true if completed (filter these out for active tasks)

## Write commands

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

## Operating rules

- **HARD RULE: Never use `/rest/v2/` or `/sync/v9/` endpoints — both return 410 Gone.**
- **HARD RULE: Never write raw fetch/HTTP calls to the Todoist API directly. Always use the todoist-ts-cli via npx. Exception: completed tasks and bulk active task reads — the CLI cannot do these.**
- If the user wants a planning or triage pass, start by reading the relevant tasks first.
- For bulk reorganizing, propose the new structure briefly, then apply it.
- Prefer collapsing finished or mostly-finished projects into one closeout task instead of keeping a whole project on Today.
- Confirm before destructive bulk deletes.
- Use natural language due dates exactly as the user says unless a clearer date is needed.
- If auth fails, say the Todoist token path is still broken and note that this runtime has historically used `TODOIST_API_KEY` as the working path.
- When invoking the CLI, map the key into the token env: `TODOIST_API_TOKEN="$TODOIST_API_KEY" npx ...`
- Task deep links: `https://app.todoist.com/app/task/{task_id}`

## Today-list triage default

When the user says Today has too much on it:
1. Read Today and overdue tasks.
2. Separate into:
   - must do today
   - should do this week
   - later / backlog
3. Keep Today tight, usually 3 to 5 real tasks.
4. Convert broad projects into one concrete next action when possible.