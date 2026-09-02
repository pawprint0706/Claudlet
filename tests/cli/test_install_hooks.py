import json
import pytest
from claudlet.cli import install_hooks as ih


def _settings_with_our_hook(path):
    path.write_text(json.dumps({"hooks": {
        "Stop": [{"hooks": [{"type": "command", "command": "claudlet-hook Stop"}]}]
    }}))


def test_main_accepts_argv_remove(tmp_path, monkeypatch):
    # main() must honor an explicit argv (so uninstall can call
    # main(["--remove"])) instead of only ever reading sys.argv — under pytest
    # sys.argv has no "--remove", so a sys.argv-only main would re-INSTALL here.
    settings = tmp_path / "settings.json"
    codex_hooks = tmp_path / "hooks.json"
    _settings_with_our_hook(settings)
    _settings_with_our_hook(codex_hooks)
    monkeypatch.setattr(ih, "SETTINGS", str(settings))
    monkeypatch.setattr(ih, "CODEX_HOOKS", str(codex_hooks))

    ih.main(["--remove"])

    data = json.loads(settings.read_text())
    assert "hooks" not in data          # our only hook group was removed
    assert "hooks" not in json.loads(codex_hooks.read_text())


def test_main_argv_none_defaults_to_sys_argv(tmp_path, monkeypatch):
    # back-compat: no argv -> read sys.argv (install path, no --remove present)
    settings = tmp_path / "settings.json"
    codex_hooks = tmp_path / "hooks.json"
    monkeypatch.setattr(ih, "SETTINGS", str(settings))
    monkeypatch.setattr(ih, "CODEX_HOOKS", str(codex_hooks))
    monkeypatch.setattr(ih.sys, "argv", ["claudlet-install-hooks"])

    ih.main()

    data = json.loads(settings.read_text())
    assert "hooks" in data and "Stop" in data["hooks"]
    codex = json.loads(codex_hooks.read_text())
    assert "PermissionRequest" in codex["hooks"]
    assert "Notification" not in codex["hooks"]


def test_codex_install_preserves_unrelated_hooks(tmp_path, monkeypatch):
    settings = tmp_path / "settings.json"
    codex_hooks = tmp_path / "hooks.json"
    settings.write_text("{}")
    codex_hooks.write_text(json.dumps({"description": "mine", "hooks": {
        "Stop": [{"hooks": [{"type": "command", "command": "other-tool"}]}]
    }}))
    monkeypatch.setattr(ih, "SETTINGS", str(settings))
    monkeypatch.setattr(ih, "CODEX_HOOKS", str(codex_hooks))

    ih.main([])

    data = json.loads(codex_hooks.read_text())
    assert data["description"] == "mine"
    commands = [h["command"] for g in data["hooks"]["Stop"] for h in g["hooks"]]
    assert "other-tool" in commands
    assert sum("claudlet-hook" in command for command in commands) == 1


def test_codex_windows_command_uses_powershell_call_operator():
    data = ih._updated({}, ["PreToolUse"], ["PreToolUse"], False,
                       "& 'C:\\Users\\A User\\claudlet-hook.EXE'")

    handler = data["hooks"]["PreToolUse"][0]["hooks"][0]
    assert handler["commandWindows"] == (
        "& 'C:\\Users\\A User\\claudlet-hook.EXE' PreToolUse")
    # Keep the portable command for non-Windows hosts and config portability.
    assert handler["command"].endswith(" PreToolUse")


def test_remove_cleans_obsolete_claudlet_event(tmp_path):
    settings = {"hooks": {"FutureOldEvent": [{
        "hooks": [{"type": "command", "command": "claudlet-hook FutureOldEvent"}]
    }]}}

    assert ih._updated(settings, ih.CODEX_EVENTS,
                       ih.CODEX_TOOL_EVENTS, True) == {}


def test_loads_all_targets_before_writing_any(tmp_path, monkeypatch):
    settings = tmp_path / "settings.json"
    codex_hooks = tmp_path / "hooks.json"
    settings.write_text(json.dumps({"keep": "original"}))
    codex_hooks.write_text("{ broken")
    monkeypatch.setattr(ih, "SETTINGS", str(settings))
    monkeypatch.setattr(ih, "CODEX_HOOKS", str(codex_hooks))

    with pytest.raises(SystemExit):
        ih.main([])

    assert json.loads(settings.read_text()) == {"keep": "original"}


def test_save_preserves_original_when_write_fails(tmp_path, monkeypatch):
    # If serialization dies mid-save, the live settings.json must still be the
    # ORIGINAL, not gone (the old rename-then-write left nothing behind).
    settings = tmp_path / "settings.json"
    settings.write_text(json.dumps({"keep": "me"}))
    monkeypatch.setattr(ih, "SETTINGS", str(settings))

    class Unserializable:
        pass

    with pytest.raises(TypeError):
        ih.save({"bad": Unserializable()})       # json.dump raises

    assert json.loads(settings.read_text()) == {"keep": "me"}   # intact
    # and no leftover temp file in the directory
    assert not [p for p in tmp_path.iterdir() if p.suffix == ".tmp"]


def test_save_keeps_single_rolling_backup(tmp_path, monkeypatch):
    settings = tmp_path / "settings.json"
    settings.write_text(json.dumps({"v": 1}))
    monkeypatch.setattr(ih, "SETTINGS", str(settings))

    ih.save({"v": 2})
    ih.save({"v": 3})

    baks = [p.name for p in tmp_path.iterdir() if ".bak" in p.name]
    assert baks == ["settings.json.bak"]         # exactly one, not timestamped
    assert json.loads(settings.read_text()) == {"v": 3}
    assert json.loads((tmp_path / "settings.json.bak").read_text()) == {"v": 2}


def test_load_bails_on_corrupt_settings(tmp_path, monkeypatch):
    settings = tmp_path / "settings.json"
    settings.write_text("{ this is not json")
    monkeypatch.setattr(ih, "SETTINGS", str(settings))

    with pytest.raises(SystemExit):
        ih.load()

    # the corrupt file is left untouched for the user to recover
    assert settings.read_text() == "{ this is not json"
