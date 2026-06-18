import sys
import json
import io
import contextlib
import argparse

sys.path.insert(0, "/home/clawbot/.openclaw/scripts")
import approval_store

# Only write-like actions require an authenticated operator. Reads
# (list pending, show) work without --actor.
WRITE_PERMISSION_MAP = {
    "approve": "approval:approve",
    "reject": "approval:reject",
    "reroute": "approval:edit",
    "archive": "approval:edit",
}

NOT_AUTHORIZED = "Not authorized. This command requires operator permissions."
UNKNOWN_COMMAND = "Unknown command. Try: list pending, approve <id>, reject <id>, show <id>"


def _silent_call(fn, *args, **kwargs):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        return fn(*args, **kwargs)


def parse_command(raw):
    cmd = (raw or "").strip()
    parts = cmd.split()
    if not parts:
        return ("unknown", {})
    lower = [p.lower() for p in parts]

    if lower[0] == "list" and len(lower) >= 2 and lower[1] == "pending":
        type_filter = parts[2].lower() if len(parts) > 2 else None
        return ("list_pending", {"type_filter": type_filter})

    if lower[0] == "show" and len(parts) >= 2:
        return ("show", {"id": parts[1]})

    if lower[0] == "approve" and len(parts) >= 2:
        return ("approve", {"id": parts[1]})

    if lower[0] == "reject" and len(parts) >= 2:
        id_ = parts[1]
        reason = " ".join(parts[2:]) if len(parts) > 2 else None
        return ("reject", {"id": id_, "reason": reason})

    if lower[0] == "reroute" and len(parts) >= 2:
        return ("reroute", {"id": parts[1]})

    if lower[0] == "archive" and len(parts) >= 2:
        return ("archive", {"id": parts[1]})

    return ("unknown", {})


def cmd_list_pending(type_filter=None):
    rows = approval_store.list_pending(type_filter=type_filter)
    if not rows:
        return "No pending approvals."

    groups = {}
    order = []
    for r in rows:
        d = r.get("domain") or "general"
        if d not in groups:
            groups[d] = []
            order.append(d)
        groups[d].append(r)

    lines = [f"Pending decisions ({len(rows)}):", ""]
    for d in order:
        lines.append(f"[{d}]")
        for it in groups[d]:
            lines.append(
                f"  {it['id']} — {it['title']} ({it['risk_level']} risk) "
                f"— recommended: {it['recommended_action']}"
            )
        lines.append("")
    lines.append("Commands: approve <id> | reject <id> | show <id>")
    return "\n".join(lines)


def cmd_show(id_):
    item = approval_store.get_approval(id_)
    if item is None:
        return f"Approval not found: {id_}"
    return approval_store.format_decision_detail(item)


def _require_action_allowed(item, action):
    allowed = item.get("allowed_actions_json") or list(approval_store.DEFAULT_ALLOWED_ACTIONS)
    if action not in allowed:
        raise ValueError(
            f"Action '{action}' is not allowed for {item['id']}. "
            f"Allowed actions: {', '.join(allowed)}"
        )


def cmd_approve(id_, actor_str):
    item = approval_store.get_approval(id_)
    if item is None:
        raise ValueError(f"Approval '{id_}' not found")
    _require_action_allowed(item, "approve")
    _silent_call(approval_store.approve, id_, actor_str)
    return f"✓ {id_} approved."


def cmd_reject(id_, actor_str, reason):
    item = approval_store.get_approval(id_)
    if item is None:
        raise ValueError(f"Approval '{id_}' not found")
    _require_action_allowed(item, "reject")
    _silent_call(approval_store.reject, id_, actor_str, reason)
    return f"✓ {id_} rejected."


def cmd_unimplemented_action(id_, action):
    item = approval_store.get_approval(id_)
    if item is None:
        raise ValueError(f"Approval '{id_}' not found")
    _require_action_allowed(item, action)
    return "Action stored but executor not implemented yet."


def handle_command(actor_str, command_str):
    action, args = parse_command(command_str)

    if action == "unknown":
        return UNKNOWN_COMMAND

    required_permission = WRITE_PERMISSION_MAP.get(action)
    if required_permission:
        try:
            approval_store.authenticate(actor_str, required_permission=required_permission)
        except PermissionError:
            return NOT_AUTHORIZED

    try:
        if action == "list_pending":
            return cmd_list_pending(args.get("type_filter"))
        if action == "show":
            return cmd_show(args["id"])
        if action == "approve":
            return cmd_approve(args["id"], actor_str)
        if action == "reject":
            return cmd_reject(args["id"], actor_str, args.get("reason"))
        if action in ("reroute", "archive"):
            return cmd_unimplemented_action(args["id"], action)
    except PermissionError:
        return NOT_AUTHORIZED
    except ValueError as e:
        return str(e)

    return UNKNOWN_COMMAND


def main():
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--actor")
    parser.add_argument("--command")
    args, _ = parser.parse_known_args()

    if args.command:
        actor_str = args.actor
        command_str = args.command
    else:
        raw = sys.stdin.read()
        if not raw.strip():
            print("Invalid input: command is required.")
            return
        try:
            data = json.loads(raw)
        except (TypeError, ValueError):
            print("Invalid input: expected JSON with 'actor' and 'command' on stdin.")
            return
        actor_str = data.get("actor")
        command_str = data.get("command")

    if not command_str:
        print("Invalid input: command is required.")
        return

    print(handle_command(actor_str, command_str))


if __name__ == "__main__":
    main()
