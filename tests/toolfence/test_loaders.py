from agentci.toolfence.loaders import discover_files


def test_discover_files_expands_a_directory_argument(tmp_path):
    (tmp_path / "a.yaml").write_text("name: a", encoding="utf-8")
    (tmp_path / "b.json").write_text("{}", encoding="utf-8")
    (tmp_path / "c.yml").write_text("name: c", encoding="utf-8")
    (tmp_path / "ignore.txt").write_text("x", encoding="utf-8")

    result = discover_files((str(tmp_path),))
    names = sorted(p.name for p in result)

    # the directory must expand to its fixture files, not be added as-is
    assert names == ["a.yaml", "b.json", "c.yml"]


def test_discover_files_still_handles_explicit_files_and_globs(tmp_path):
    (tmp_path / "x.yaml").write_text("name: x", encoding="utf-8")
    (tmp_path / "y.yaml").write_text("name: y", encoding="utf-8")

    explicit = discover_files((str(tmp_path / "x.yaml"),))
    assert [p.name for p in explicit] == ["x.yaml"]

    globbed = discover_files((str(tmp_path / "*.yaml"),))
    assert sorted(p.name for p in globbed) == ["x.yaml", "y.yaml"]
