"""Steam library discovery must work for KSP installed outside the default C: library."""

from astra import config


def _make_steam(root, libraries):
    (root / "steamapps").mkdir(parents=True)
    lines = ['"libraryfolders"', "{", '\t"0"']
    lines += ['\t{', '\t\t"path"', '\t\t"%s"' % str(root).replace("\\", "\\\\"), '\t}']
    for index, library in enumerate(libraries, 1):
        lines += ['\t"%d"' % index, '\t{', '\t\t"path"', '\t\t"%s"' % str(library).replace("\\", "\\\\"), '\t}']
    lines += ["}"]
    (root / "steamapps" / "libraryfolders.vdf").write_text("\n".join(lines), encoding="utf-8")
    for library in libraries:
        install = library / "steamapps" / "common" / "Kerbal Space Program"
        install.mkdir(parents=True)
        (install / "KSP_x64.exe").write_bytes(b"")


def test_finds_ksp_in_an_extra_steam_library(tmp_path, monkeypatch):
    steam = tmp_path / "Steam"
    extra = tmp_path / "SteamLibrary"
    _make_steam(steam, [extra])
    monkeypatch.setenv("PROGRAMFILES(X86)", str(tmp_path))
    monkeypatch.delenv("ASTRA_KSP_DIR", raising=False)

    expected = extra / "steamapps" / "common" / "Kerbal Space Program"
    assert config._steam_ksp_dirs() == [expected]
    assert config._ksp_dir() == expected


def test_explicit_environment_path_wins(tmp_path, monkeypatch):
    chosen = tmp_path / "custom KSP"
    monkeypatch.setenv("ASTRA_KSP_DIR", str(chosen))
    monkeypatch.setenv("PROGRAMFILES(X86)", str(tmp_path))
    assert config._ksp_dir() == chosen
