# Configuration

[← README](../README.md) · **English** | [한국어](configuration.ko.md)

Remap which animation shows for which Claude Code activity in a JSON config at
`~/.config/claudlet/config.json` (all keys optional).

> **Tip:** run `claudlet-config` (or ask Claude `/claudlet config`) to print the
> exact path, the current effective values, and — importantly — any entries
> that were **silently dropped** because of a typo or unknown slot. `claudlet-config
> init` scaffolds a starter file; `claudlet-config open` opens it in your editor.

Example:

```json
{
  "tools":      { "Bash": "work_search", "Grep": "sing", "*": "work_computer" },
  "events":     { "prompt": "thinking", "celebrate": "juggle" },
  "raw_events": { "PostToolUse": "celebrate", "SubagentStop": "wave" }
}
```

- **`tools`** — tool name → state. `"*"` is the fallback for unmapped tools;
  `mcp__*` tools default to `work_web` unless named explicitly.
- **`events`** — event slot → state. Slots: `start`, `prompt`, `done`, `celebrate`,
  `error`, `permission`, `idle_prompt`.
- **`raw_events`** — raw hook event name → state, for any event without a slot
  (`PostToolUse`, `SubagentStop`, `PreCompact`, …). Knowing the event name the hook
  sends is enough to map it; slotted events keep their built-in behaviour.

Values must be a known state/motion:

```
work_computer  work_search  work_web  work_agent  work_skill
idle  sleeping  thinking  attention  asking  error  celebrate
jump  wave  sing  juggle
```

Anything unknown is ignored, so a typo just falls back to the defaults. Restart the
pet to pick up changes.

## Language

`lang` sets the language of the pet's speech bubbles, tray tooltips, and right-click
menu — `"ko"`, `"en"`, or `"auto"` (default; follows your locale, falling back to
English):

```json
{ "lang": "en" }
```

## Palette

`palette` sets the global palette. `palettes` can override it for the coding
agent that started the pet:

```json
{
  "palette": "auto",
  "palettes": { "codex": "shiny_violet", "claude": "default" }
}
```

Palette values are `auto`, `default`, `shiny_teal`, and `shiny_violet`.
`CLAUDLET_PALETTE` remains the highest-priority one-process override.

## Placement (dock)

By default the pet **stands docked in the bottom-right corner** of your monitor.
Several pets line up **side by side** (right to left) instead of piling on top of
each other, wrapping to another row when one row fills the screen. When a pet
ahead in the row quits, the ones behind shuffle up so the row stays tight.

**Drag it with the mouse to move it.** Dragging one pet moves the whole row (the
spacing is preserved), and the spot is saved to the config so pets started later
appear there too. The right-click menu's **"Reset dock position"** puts the row
back in its corner.

```json
{
  "dock": {
    "enabled": true,
    "anchor": "bottom-right",
    "screen": "primary",
    "gap": 4,
    "offset": { "x": 0, "y": 0 }
  }
}
```

- **`enabled`** — `false` brings back the roaming pet (gravity and window
  perching included). It is the same switch as **"Roam freely"** in the
  right-click menu, and toggling it there is written back here.
- **`anchor`** — `bottom-right` (default) · `bottom-left` · `top-right` ·
  `top-left`. The row grows away from the anchor.
- **`screen`** — `"primary"` (default) or a monitor index (`0`, `1`, …); an
  out-of-range index falls back to the primary. Rather than hunting for the right
  index, it is usually quicker to just **drag the pet onto the monitor you want** —
  that position is remembered.
- **`gap`** — pixels between pets.
- **`offset`** — displacement from the anchor. Dragging writes it for you, so you
  rarely need to set it by hand.

> `roam_area` / `no_go` zones apply **only while roaming**. A docked pet sits
> where you put it, so it is not constrained by them.
