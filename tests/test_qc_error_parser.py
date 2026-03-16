from core.parsers.qc_error_parser import parse_diagnostics


def test_parse_fteqcc_error():
    output = "weapons.qc:42: error: type mismatch for +"
    diags = parse_diagnostics(output)
    assert len(diags) == 1
    assert diags[0].file_path == "weapons.qc"
    assert diags[0].line == 42
    assert diags[0].column is None
    assert diags[0].severity == "error"
    assert diags[0].message == "type mismatch for +"


def test_parse_gmqcc_error_with_column():
    output = "defs.qc:10:5: error: undeclared identifier 'foo'"
    diags = parse_diagnostics(output)
    assert len(diags) == 1
    assert diags[0].file_path == "defs.qc"
    assert diags[0].line == 10
    assert diags[0].column == 5
    assert diags[0].severity == "error"


def test_parse_warning():
    output = "world.qc:99: warning: unused variable 'tmp'"
    diags = parse_diagnostics(output)
    assert len(diags) == 1
    assert diags[0].severity == "warning"


def test_parse_multiple_diagnostics():
    output = (
        "defs.qc:1: error: missing semicolon\n"
        "fight.qc:50: warning: unreachable code\n"
        "some unrelated output line\n"
        "world.qc:200:3: error: too few arguments\n"
    )
    diags = parse_diagnostics(output)
    assert len(diags) == 3
    assert diags[0].file_path == "defs.qc"
    assert diags[1].severity == "warning"
    assert diags[2].column == 3


def test_parse_fallback_qc_path():
    output = "subs.qc:15: unknown value 'MOVETYPE_FLY'"
    diags = parse_diagnostics(output)
    assert len(diags) == 1
    assert diags[0].file_path == "subs.qc"
    assert diags[0].severity == "error"


def test_ignores_non_diagnostic_lines():
    output = (
        "compiling progs.dat...\n"
        "3 warnings, 0 errors\n"
        "done.\n"
    )
    diags = parse_diagnostics(output)
    assert len(diags) == 0


def test_empty_input():
    assert parse_diagnostics("") == []
