---
name: claudlet
description: Launch or control the claudlet desktop buddy for Claude Code or Codex CLI. Use for /claudlet, $claudlet, attaching or starting the pet, motions, pet configuration, and pet updates.
---

# claudlet — launch the desktop buddy

A frameless roaming pixel creature. By default this **attaches** a pet to the
**current session** (so it reacts to this session's agent activity). Pass
`standalone` for an unattached one.

## How to run a claudlet command

claudlet ships `claudlet-attach`, `claudlet-motion`, `claudlet-config`,
`claudlet-version`, and `claudlet-install`. Invoke these commands directly.
If one is not on `PATH`, use the matching shim under `~/claudlet/bin/`; on
Windows run that shim with Python.

## Routing

Look at the argument the user passed after `/claudlet` or `$claudlet`:

- a **motion name** (`jump`, `wave`, `sing`, `juggle`, `float`, `celebrate`,
  `thinking`, `sleeping`, `error`, `attention`), or `list`, or `stop`/`clear`
  → **Trigger a motion**; do NOT launch a pet.
- `config` (or `설정`; optionally `config open` / `config init`) → **Configure**;
  do NOT launch a pet.
- `update` (or `업데이트`) → **Update** (release channel). `update latest`
  (or `edge` / `develop`) → **Update** to the latest `develop` branch.
- `standalone` → **Standalone**.
- nothing → **Attach** (default).

## Attach (default)

```bash
claudlet-attach
```
`claudlet-attach` finds this session (`CLAUDE_CODE_SESSION_ID`,
`CODEX_THREAD_ID`, or `CODEX_SESSION_ID`; otherwise the newest Claude
transcript), detects the host terminal/IDE
so click-to-focus targets the right window, skips if a pet is already attached
(the same liveness handshake the hook uses — a bare connect can't tell a live
pet from a reused stale port), and launches a detached pet bound to the session.
It prints `attached to session ...` or `already attached ...`.

**Reactions require hooks.** The pet only reacts to this session if the
claudlet hooks are installed (`claudlet-install`) AND this session loaded
them. If hooks were installed *after* this session started, restart the session
(or the pet attaches but stays idle). New sessions auto-attach their own pet via
the SessionStart hook, so `/claudlet`/`$claudlet` is mainly for sessions that predate the
install, or to bring a closed pet back.

## Standalone

An unattached, decorative pet that reacts to no particular session:
```bash
claudlet-attach --standalone
```

## Trigger a motion

```bash
claudlet-motion <arg>    # jump | wave | sing | juggle | float | celebrate | thinking | sleeping | error | attention | stop | list
```
e.g. `claudlet-motion jump`, `claudlet-motion float` (holds until
`claudlet-motion stop`), `claudlet-motion list`. It broadcasts to every running pet and prints how many
reacted; if it says `-> 0 pet(s)`, none is running — offer to attach one with
`/claudlet` or `$claudlet`.

## Configure

The user config remaps **which creature motion shows for which coding-agent
activity**, plus **language**. After a pipx install it's buried
(`~/.config/claudlet/config.json`, or `%USERPROFILE%\.config\claudlet\
config.json` on Windows), so use `claudlet-config` to locate/inspect it — never
guess the path.

```bash
claudlet-config          # show: absolute path, status, current values, IGNORED entries, valid values
claudlet-config init     # create a starter template if none exists
claudlet-config open     # open it in the OS default editor
```

`claudlet-config` prints the resolved absolute path and — crucially — any entries
that are **present in the file but silently dropped** (a typo'd state or unknown
slot) under `ignored:`. When something "doesn't work," check there first.

**Editing on the user's behalf.** When the user asks for a change in natural
language (e.g. "make it jump when I run Bash", "switch it to Korean"):
1. run `claudlet-config` to get the absolute path + current values,
2. read that file (run `claudlet-config init` first if it's missing),
3. edit the JSON **directly with your own Edit/Write tools** using the schema
   below,
4. run `claudlet-config` again and confirm nothing landed under `ignored:`,
5. tell the user to **restart the pet** (right-click → 종료, then invoke the skill)
   for it to apply — config is read at pet startup.

Schema (all keys optional; unknown keys / invalid values are dropped):
```json
{
  "lang": "auto",                        // "ko" | "en" | "auto"
  "palette": "auto",                     // global fallback
  "palettes": { "codex": "shiny_violet", "claude": "default" },
  "tools":      { "Bash": "work_computer", "*": "work_computer" },
  "events":     { "prompt": "thinking", "celebrate": "juggle" },
  "raw_events": { "PostToolUse": "celebrate", "SubagentStop": "wave" },
  "dock": { "enabled": true, "anchor": "bottom-right",
            "screen": "primary", "gap": 4, "offset": {"x": 0, "y": 0} }
}
```
- `palette` / `palettes` — global palette and optional per-agent overrides.
  Values: `auto`, `default`, `shiny_teal`, `shiny_violet`. Agent keys:
  `claude`, `codex`. `CLAUDLET_PALETTE` still overrides both for one process.
- `tools` — tool name → state (`"*"` = fallback for unmapped tools).
- `events` — event slot → state. Slots: `start`, `prompt`, `done`,
  `celebrate`, `error`, `permission`, `idle_prompt`, `asking`, `autopilot`.
- `raw_events` — raw hook event name → state (e.g. `PostToolUse`,
  `SubagentStop`, `PreCompact`).
- `dock` — where the pet stands. Docked is the DEFAULT: it holds a fixed corner
  slot instead of roaming, and several pets line up side by side (right to left,
  wrapping to another row) rather than overlapping. The user can drag a pet to
  move the whole row; the drop point is saved back here as `offset`, so a user
  asking for "another monitor" is usually better served by dragging than by
  guessing a `screen` index. `anchor`: `bottom-right` (default) / `bottom-left` /
  `top-right` / `top-left`. `screen`: `"primary"` or a monitor index.
  `enabled: false` restores the old roaming behaviour — same switch as the
  right-click menu's "자유롭게 돌아다니기" / "Roam freely".
  Note `roam_area` / `no_go` only bind a ROAMING pet; a docked one ignores them.
- Valid states (the `claudlet-config` output also lists these): `work_computer`,
  `work_search`, `work_web`, `work_agent`, `work_skill`, `thinking`,
  `celebrate`, `error`, `attention`, `asking`, `autopilot`, `sleeping`, `idle`,
  `jump`, `wave`, `sing`, `juggle`.

## Update

Two channels: **release** (`/claudlet update`, the latest PyPI release — stable;
`master` holds only released tags) and **latest** (`/claudlet update latest`, the
tip of the `develop` branch — newest, may be rough). Default to release unless
the user asked for `latest`/`edge`/`develop`.

**Do NOT run the update yourself.** It changes the user's environment and must be
followed by a session restart, so hand it to the user to run — and updating is
also the one thing that shouldn't happen silently mid-session. Steps:

1. **Show current vs latest** (this you may run — it's read-only):
   ```bash
   claudlet-version
   ```
2. **Detect install method** to pick the command: a source checkout has
   `$HOME/claudlet/.git`; otherwise it's a pipx/pip install.
3. **Give the user a `!`-prefixed command to run themselves** (so it runs in
   their own shell with output visible), matching method + channel:

   | | release | latest (`develop`) |
   |---|---|---|
   | **pipx** | `! pipx install --force claudlet && claudlet-install` | `! pipx install --force "git+https://github.com/YeeDochi/Claudlet@develop" && claudlet-install` |
   | **source checkout** | `! git -C ~/claudlet pull --ff-only && claudlet-install` | (same — a checkout already tracks its branch) |

   (Use `pipx install --force` for both pipx rows, NOT `pipx upgrade`: `upgrade`
   re-fetches from whatever source the user first installed from, so a user on
   the git/`@develop` install would get develop again even when they pick
   *release*. `install --force claudlet` always pulls the PyPI release, so the
   two channels switch cleanly in both directions. The *latest* channel needs
   `git` on PATH; *release* does not — if git is missing, steer them to release.)

   Give a normal shell command in Codex CLI; use Claude Code's `!` prefix only
   when that host requires it.
4. **Then reload**: the new hooks + pet code only take effect fresh. Tell them to
   close any running pet (right-click → 종료), then restart or resume the agent
   session. Codex users must review changed hooks with `/hooks`, then restart or
   resume once more so `SessionStart` runs. Until then the pet keeps
   running the old code and the current session keeps the old hooks.
5. **What changed**: point them at the release notes so they see what's new —
   <https://github.com/YeeDochi/Claudlet/releases/latest> (`claudlet-install`
   also prints this link, labelled in their language, when it finishes).

If `git pull` fails (local changes / divergence), report it — don't force.

## Notes
- Multiple pets are fine — each is independent. Stop one via right-click → 종료.
- This skill only launches/updates a pet; `claudlet-install` is what edits
  settings/hooks.
