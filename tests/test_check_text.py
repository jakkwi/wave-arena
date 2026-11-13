from tools.check_text import scan_text

EM_DASH = chr(0x2014)


def test_flags_long_dash() -> None:
    assert scan_text("a.md", f"x {EM_DASH} y") == ["a.md:1: long dash"]


def test_flags_attribution_trailer() -> None:
    assert scan_text("commit abc", "Fix\n\nCo-Authored-By: Someone <a@example.invalid>") == [
        "commit abc:3: AI attribution"
    ]


def test_mentioning_the_rule_is_fine() -> None:
    assert scan_text("rules.md", "Never add Co-Authored-By trailers.") == []
