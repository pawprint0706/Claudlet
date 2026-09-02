#!/usr/bin/env python3
"""Register (or remove) claudlet hooks for Claude Code and Codex CLI.

Usage:
    claudlet-install-hooks           # install
    claudlet-install-hooks --remove  # remove

Keeps a single rolling backup (settings.json.bak) and writes atomically.
Idempotent.
"""
import json
import os
import shutil
import sys
import tempfile

SETTINGS = os.path.expanduser("~/.claude/settings.json")
CODEX_HOOKS = os.path.join(
    os.environ.get("CODEX_HOME") or os.path.expanduser("~/.codex"),
    "hooks.json")


def _quote(path):
    # Always quote, even with no spaces: Claude Code runs hook commands
    # through bash even on Windows, and an unquoted "C:\Users\..." loses
    # every backslash there (bash treats "\U", "\g", etc. as escapes of the
    # next literal char). Double quotes keep bash from touching backslashes
    # (its escape rules inside "" only apply to \, $, `, ", newline) while
    # still being valid, unremarkable quoting for cmd.exe and POSIX sh.
    return f'"{path}"'


def _powershell_quote(path):
    """Quote one literal argument for PowerShell's call operator."""
    return "'" + path.replace("'", "''") + "'"


def _hook_command():
    """Command string settings.json invokes per hook event. Prefer the installed
    `claudlet-hook` console script (pipx/pip); else the source checkout's
    bin/claudlet-hook shim (which puts src/ on sys.path); else `python -m
    claudlet.cli.hook`. On Windows, extensionless scripts need the interpreter
    prefixed (cmd.exe ignores "#!"); a real console-script .exe from which()
    runs directly."""
    exe = shutil.which("claudlet-hook")
    if exe:
        return _quote(exe)
    repo_bin = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "bin", "claudlet-hook")
    if os.path.exists(repo_bin):
        if os.name == "nt":
            return f"{_quote(sys.executable)} {_quote(repo_bin)}"
        return _quote(repo_bin)
    return f"{_quote(sys.executable)} -m claudlet.cli.hook"


HOOK_CMD = _hook_command()


def _hook_command_windows():
    """PowerShell-safe command prefix for Codex's Windows override.

    A command that starts with a quoted executable path is valid in the POSIX
    shell Claude Code uses, but PowerShell treats that quoted path as a string
    expression and exits 1 when the event argument follows it.  Codex exposes
    ``commandWindows`` specifically for a Windows override, so invoke the same
    executable through PowerShell's call operator there.
    """
    exe = shutil.which("claudlet-hook")
    if exe:
        return f"& {_powershell_quote(exe)}"
    repo_bin = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "bin", "claudlet-hook")
    if os.path.exists(repo_bin):
        return f"& {_powershell_quote(sys.executable)} {_powershell_quote(repo_bin)}"
    return f"& {_powershell_quote(sys.executable)} -m claudlet.cli.hook"


HOOK_CMD_WINDOWS = _hook_command_windows()

CLAUDE_TOOL_EVENTS = ["PreToolUse", "PostToolUse"]
CLAUDE_PLAIN_EVENTS = ["UserPromptSubmit", "Notification", "Stop", "StopFailure",
                       "SubagentStop", "SessionStart", "SessionEnd"]
CLAUDE_EVENTS = CLAUDE_TOOL_EVENTS + CLAUDE_PLAIN_EVENTS

CODEX_TOOL_EVENTS = ["PreToolUse", "PostToolUse", "PermissionRequest"]
CODEX_PLAIN_EVENTS = ["UserPromptSubmit", "Stop", "SubagentStart",
                      "SubagentStop", "SessionStart", "SessionEnd",
                      "PreCompact", "PostCompact"]
CODEX_EVENTS = CODEX_TOOL_EVENTS + CODEX_PLAIN_EVENTS
ALL_EVENTS = CLAUDE_EVENTS


def load(path=None):
    path = SETTINGS if path is None else path
    if not os.path.exists(path):
        return {}
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        # Corrupt/unreadable settings.json. Returning {} would drop every OTHER
        # setting the user has when we write our hooks back, so bail loudly and
        # leave their file untouched instead.
        raise SystemExit(
            f"claudlet: cannot read {path} ({e}).\n"
            "Fix or move it aside, then re-run the installer.")


def save(s, path=None):
    """Write settings.json atomically, keeping a single rolling backup.

    The old approach renamed the live file to a timestamped .bak and *then*
    wrote the new one: a crash in between left no settings.json at all, and the
    timestamped backups piled up forever. Instead: copy the current file to a
    stable settings.json.bak, write the new content to a temp file in the same
    directory, fsync it, and os.replace() it into place (atomic on the same
    filesystem). The live file is never absent, and only one backup is kept.
    """
    path = SETTINGS if path is None else path
    d = os.path.dirname(path)
    os.makedirs(d, exist_ok=True)
    if os.path.exists(path):
        shutil.copy2(path, f"{path}.bak")   # single rolling backup
    prefix = ".%s." % os.path.basename(path)
    fd, tmp = tempfile.mkstemp(dir=d, prefix=prefix, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(s, f, indent=2, ensure_ascii=False)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    except Exception:
        try:
            os.unlink(tmp)          # don't leave a half-written temp behind
        except OSError:
            pass
        raise


def is_ours(group):
    for h in group.get("hooks", []):
        cmd = h.get("command", "")
        # match the current markers and the pre-rename ones ("claude-pet-hook"/
        # "claude_pet.hook", plus the pre-cli-move "claudlet.hook") so a
        # migration run cleanly drops old entries instead of leaving them
        # alongside the new claudlet ones (double-firing hooks).
        if any(m in cmd for m in ("claudlet-hook", "claudlet.hook", "claudlet.cli.hook",
                                  "claude-pet-hook", "claude_pet.hook")):
            return True
    return False


def configured(s):
    return any(is_ours(group)
               for groups in s.get("hooks", {}).values()
               for group in groups)


def _updated(s, events, tool_events, remove, windows_command=None):
    hooks = s.get("hooks", {})
    for ev in list(hooks):
        hooks[ev] = [g for g in hooks[ev] if not is_ours(g)]
        if not hooks[ev]:
            del hooks[ev]
    for ev in events:
        if not remove:
            cmd = {"type": "command", "command": f"{HOOK_CMD} {ev}"}
            if windows_command:
                cmd["commandWindows"] = f"{windows_command} {ev}"
            group = {"hooks": [cmd]}
            if ev in tool_events:
                group["matcher"] = "*"
            hooks.setdefault(ev, []).append(group)
    if hooks:
        s["hooks"] = hooks
    else:
        s.pop("hooks", None)
    return s


def main(argv=None):
    remove = "--remove" in (sys.argv if argv is None else argv)
    targets = [
        ("Claude Code", SETTINGS, CLAUDE_EVENTS, CLAUDE_TOOL_EVENTS, None),
        ("Codex CLI", CODEX_HOOKS, CODEX_EVENTS, CODEX_TOOL_EVENTS,
         HOOK_CMD_WINDOWS if os.name == "nt" else None),
    ]
    loaded = [(name, path, events, tools, windows, load(path))
              for name, path, events, tools, windows in targets]
    for name, path, events, tools, windows, settings in loaded:
        save(_updated(settings, events, tools, remove, windows), path)
        print(("removed" if remove else "installed"),
              "claudlet hooks for %s:" % name, ", ".join(events))
    print("(restart Claude Code/Codex CLI sessions for changes to take effect)")
    if not remove:
        print("(in Codex CLI, open /hooks, trust claudlet, then restart once more)")


if __name__ == "__main__":
    main()
