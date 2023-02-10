from komodo.shebang import fixup_python_shebangs


def test_fixup_python_shebangs(tmp_path):
    # Setup a bin-directory where there is something to fix
    prefix = tmp_path / "prefix"
    bindir = prefix / "release/root/bin"
    bindir.mkdir(parents=True)
    (bindir / "bad_shebang").write_text(
        "#!/wildly/wrong/path/to\xe7\x8e\xa9/python\n", encoding="utf-8"
    )

    # Add noise to the directory that the code should tolerate:
    (bindir / "__pycache__").mkdir()
    (bindir / "binary_executable").write_bytes(bytes([1, 10, 100]))

    # Run the shebang fixer:
    fixup_python_shebangs(prefix, "release")

    # Verify that the shebang got fixed:
    expected_fixed_shebang = f"#!{bindir / 'python'}\n"
    assert (bindir / "bad_shebang").read_text(
        encoding="utf-8"
    ) == expected_fixed_shebang
