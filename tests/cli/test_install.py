import os

from claudlet.cli import install as I


def test_remove_delegates_to_uninstall(monkeypatch):
    # single teardown implementation: `claudlet-install --remove` must route to
    # uninstall.main (passing its argv through, so --purge is honored) rather
    # than keeping a second, divergent removal path.
    seen = []
    monkeypatch.setattr("claudlet.cli.uninstall.main",
                        lambda argv=None: seen.append(argv) or 0)

    rc = I.main(["--remove", "--purge"])

    assert rc == 0
    assert seen == [["--remove", "--purge"]]


def test_install_path_does_not_call_uninstall(monkeypatch):
    # the plain install path must never trigger teardown
    monkeypatch.setattr("claudlet.cli.uninstall.main",
                        lambda argv=None: (_ for _ in ()).throw(
                            AssertionError("uninstall must not run on install")))
    monkeypatch.setattr(I, "_check_deps", lambda: "stubbed")
    monkeypatch.setattr("claudlet.cli.install_hooks.main", lambda argv=None: None)
    monkeypatch.setattr(I, "_link_skill", lambda: (None, None))

    I.main([])          # no exception == install path stayed clear of uninstall


def test_link_skill_targets_claude_and_codex(monkeypatch):
    calls = []
    monkeypatch.setattr(I, "_link_skill_at",
                        lambda directory, link: calls.append((directory, link)) or
                        (link, None))

    linked, note = I._link_skill()

    assert calls == [(I.SKILLS_DIR, I.SKILL_LINK),
                     (I.CODEX_SKILLS_DIR, I.CODEX_SKILL_LINK)]
    assert I.SKILL_LINK in linked and I.CODEX_SKILL_LINK in linked
    assert note is None


def test_link_skill_accepts_junction_pointing_at_skill(monkeypatch, tmp_path):
    # Windows directory junctions are reparse points — os.path.islink() says
    # False for them, so the junction fallback's own output looked like clutter
    # to every later run, which re-warned "isn't a symlink" on each update.
    # Simulate a junction: islink False, samefile matches SKILL_SRC.
    skills_dir = tmp_path / "skills"
    skills_dir.mkdir()
    link = str(skills_dir / "claudlet")
    (tmp_path / "current").mkdir()          # stands in for the junction target
    monkeypatch.setattr(I, "SKILL_SRC", str(tmp_path / "current"))
    monkeypatch.setattr(os.path, "islink", lambda p: False)
    monkeypatch.setattr(os.path, "samefile",
                        lambda a, b: str(a) == link)

    path, note = I._link_skill_at(str(skills_dir), link)

    assert path == link and note is None


def test_link_skill_warns_on_foreign_directory(monkeypatch, tmp_path):
    # a plain directory (e.g. an old manual copy) that does NOT resolve to the
    # packaged skill must still be left alone with a warning
    skills_dir = tmp_path / "skills"
    skills_dir.mkdir()
    link = str(skills_dir / "claudlet")
    os.mkdir(link)
    monkeypatch.setattr(I, "SKILL_SRC", str(tmp_path / "nowhere"))

    path, note = I._link_skill_at(str(skills_dir), link)

    assert path is None and "left as-is" in note
