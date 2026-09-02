"""User config for claudlet: remap which creature motion shows for which
Claude Code activity.

File (JSON, all keys optional), at ``$XDG_CONFIG_HOME/claudlet/config.json``
(default ``~/.config/claudlet/config.json``)::

    {
      "palettes":   { "codex": "shiny_violet", "claude": "default" },
      "tools":      { "Bash": "work_search", "Grep": "sing", "*": "work_computer" },
      "events":     { "prompt": "thinking", "celebrate": "juggle" },
      "raw_events": { "PostToolUse": "celebrate", "SubagentStop": "wave" }
    }

- ``tools``  — tool name -> state. ``"*"`` is the fallback for unmapped tools;
  ``mcp__*`` tools default to ``work_web`` unless named explicitly.
- ``events`` — event slot -> state. Slots: start, prompt, done, celebrate,
  error, permission, idle_prompt (see state_engine.DEFAULT_EVENT_STATES).
- ``raw_events`` — raw hook event name -> state, for any event the engine does
  not already handle via a slot (PostToolUse, SubagentStop, PreCompact, and any
  future event). Knowing the event name the hook pushes is enough to map it.

Values must be one of state_engine.MAPPABLE_STATES; anything else (or a bad
file) is ignored, so a typo degrades to the built-in defaults rather than
breaking the pet. Pure except for the single file read in load_config.
"""
import os
import json

from claudlet.core import dock as dockgeom
from claudlet.core.state_engine import MAPPABLE_STATES, DEFAULT_EVENT_STATES


# 도크(고정 배치) 기본값. enabled=True가 기본 — 펫이 모니터 코너에 붙어 서고,
# 여러 마리는 dock.py가 옆으로 나란히 세운다. 배회하던 예전 동작은
# {"dock": {"enabled": false}} 또는 우클릭 메뉴의 "배회"로 돌아온다.
DEFAULT_DOCK = {"enabled": True, "anchor": dockgeom.DEFAULT_ANCHOR,
                "gap": dockgeom.DEFAULT_GAP, "screen": "primary",
                "offset": {"x": 0.0, "y": 0.0}}

SHINY_PALETTES = ("shiny_teal", "shiny_violet")
SHINY_CHANCE = 0.02
_PALETTE_NAMES = ("auto", "default") + SHINY_PALETTES
AGENT_NAMES = ("claude", "codex")


def config_path():
    base = os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config")
    return os.path.join(base, "claudlet", "config.json")


def default_dock():
    """DEFAULT_DOCK의 깊은 사본 — 호출자가 offset을 제자리 수정해도 안전하게."""
    d = dict(DEFAULT_DOCK)
    d["offset"] = dict(DEFAULT_DOCK["offset"])
    return d


def _clean_dock(v):
    """dock 섹션 검증. 다른 키와 같은 규칙: 이상한 값은 조용히 기본값으로 떨군다."""
    d = default_dock()
    if not isinstance(v, dict):
        return d
    if isinstance(v.get("enabled"), bool):
        d["enabled"] = v["enabled"]
    if v.get("anchor") in dockgeom.ANCHORS:
        d["anchor"] = v["anchor"]
    try:
        d["gap"] = max(0, int(v["gap"]))
    except (KeyError, TypeError, ValueError):
        pass
    scr = v.get("screen")
    # bool은 int의 하위형이라 isinstance만으로는 screen=true가 0번 모니터로 통과한다
    if scr == "primary" or (isinstance(scr, int) and not isinstance(scr, bool)
                            and scr >= 0):
        d["screen"] = scr
    off = v.get("offset")
    if isinstance(off, dict):
        try:
            d["offset"] = {"x": float(off.get("x", 0.0)),
                           "y": float(off.get("y", 0.0))}
        except (TypeError, ValueError):
            pass
    return d


def _clean(raw):
    """Validate a parsed config dict -> {tool_states, event_states}. Pure."""
    tools = {}
    for key, val in (raw.get("tools") or {}).items():
        if isinstance(key, str) and val in MAPPABLE_STATES:
            tools[key] = val
    events = {}
    for key, val in (raw.get("events") or {}).items():
        if key in DEFAULT_EVENT_STATES and val in MAPPABLE_STATES:
            events[key] = val
    raw_events = {}
    for key, val in (raw.get("raw_events") or {}).items():
        if isinstance(key, str) and val in MAPPABLE_STATES:
            raw_events[key] = val
    lang = raw.get("lang")
    if lang not in ("ko", "en", "auto"):
        lang = "auto"

    palette = raw.get("palette")
    if palette not in _PALETTE_NAMES:
        palette = "auto"
    palettes = {}
    if isinstance(raw.get("palettes"), dict):
        for agent, value in raw["palettes"].items():
            if agent in AGENT_NAMES and value in _PALETTE_NAMES:
                palettes[agent] = value

    def _rect(v):
        if not isinstance(v, dict):
            return None
        try:
            x, y, w, h = float(v["x"]), float(v["y"]), float(v["w"]), float(v["h"])
        except (KeyError, TypeError, ValueError):
            return None
        if w <= 0 or h <= 0:
            return None
        return {"x": x, "y": y, "w": w, "h": h}

    roam_area = _rect(raw.get("roam_area"))
    if not isinstance(raw.get("no_go"), list):
        no_go = []
    else:
        no_go = [r for r in (_rect(z) for z in raw.get("no_go")) if r]

    return {"tool_states": tools, "event_states": events,
            "raw_events": raw_events, "lang": lang,
            "roam_area": roam_area, "no_go": no_go, "palette": palette,
            "palettes": palettes,
            "dock": _clean_dock(raw.get("dock"))}


def _windows_locale():
    """User's UI locale (e.g. "ko-KR") via Win32 — Windows doesn't set the
    POSIX LANG/LC_* vars resolve_lang() otherwise reads, so without this,
    "auto" would default to English on every Windows machine regardless of
    the system's actual language. Delegates to geom/win32.py (the one module
    that owns the guarded, typed ctypes handles) rather than re-opening windll."""
    try:
        from claudlet.platform.geom import win32
        return win32.user_locale()
    except Exception:
        return ""


def resolve_lang(value):
    """Map a config lang to a concrete "ko"/"en". "auto" (or anything odd) reads
    the locale: Korean locale -> ko, otherwise en."""
    if value in ("ko", "en"):
        return value
    loc = (os.environ.get("LC_ALL") or os.environ.get("LC_MESSAGES")
           or os.environ.get("LANG") or "")
    if not loc and os.name == "nt":
        loc = _windows_locale()
    return "ko" if loc.lower().startswith("ko") else "en"


def resolve_palette(config_value, roll, pick=0.0):
    """Map a config palette value to a concrete palette name.

    config_value: "auto" (default) / a known name / anything else.
    roll: 0..1 shiny chance draw (caller passes random()). pick: 0..1 chooses
    among shinies. Pure & deterministic for tests — no randomness inside."""
    if config_value in (None, "auto"):
        if roll < SHINY_CHANCE:
            idx = int(pick * len(SHINY_PALETTES)) % len(SHINY_PALETTES)
            return SHINY_PALETTES[idx]
        return "default"
    if config_value in ("default",) + SHINY_PALETTES:
        return config_value
    return "default"


def detect_agent(environ=None):
    """Return the coding-agent kind represented by an environment, if known."""
    env = os.environ if environ is None else environ
    explicit = env.get("CLAUDLET_AGENT")
    if explicit in AGENT_NAMES:
        return explicit
    if env.get("CODEX_THREAD_ID") or env.get("CODEX_SESSION_ID"):
        return "codex"
    if env.get("CLAUDE_CODE_SESSION_ID"):
        return "claude"
    return None


def palette_for_agent(config, agent):
    """Configured palette for ``agent``, falling back to the global value."""
    return config.get("palettes", {}).get(agent, config.get("palette", "auto"))


def _empty_config():
    return {"tool_states": {}, "event_states": {}, "raw_events": {},
            "lang": "auto", "roam_area": None, "no_go": [], "palette": "auto",
            "palettes": {},
            "dock": default_dock()}


def load_config(path=None):
    """Read + validate the config file. Never raises: a missing/broken file
    yields empty overrides (built-in defaults apply)."""
    path = path or config_path()
    try:
        with open(path, encoding="utf-8") as f:
            raw = json.load(f)
    except (OSError, ValueError):
        return _empty_config()
    if not isinstance(raw, dict):
        return _empty_config()
    return _clean(raw)


def save_dock(updates, path=None):
    """config.json의 `dock` 하위 키만 병합해 저장하고 저장된 dock 섹션을 돌려준다.

    펫이 드래그로 옮겨진 위치를 기억하는 경로라서 read-modify-write다 — 파일을
    통째로 덮어쓰면 사용자가 손으로 적은 tools/events가 날아간다. 파일이 깨져
    있거나 쓸 수 없으면 기본값에 updates만 얹은 값을 돌려주고 조용히 넘어간다:
    위치를 못 기억하는 것이 펫이 죽는 것보다 낫다.
    """
    path = path or config_path()
    try:
        with open(path, encoding="utf-8") as f:
            raw = json.load(f)
        if not isinstance(raw, dict):
            raw = {}
    except (OSError, ValueError):
        raw = {}
    merged = dict(raw.get("dock") or {})
    merged.update(updates)
    raw["dock"] = merged
    cleaned = _clean_dock(merged)
    try:
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        tmp = "%s.%d.tmp" % (path, os.getpid())
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(raw, f, indent=2, ensure_ascii=False)
            f.write("\n")
        os.replace(tmp, path)          # 반쯤 쓰인 config를 다른 펫이 읽지 않도록
    except OSError:
        pass
    return cleaned
