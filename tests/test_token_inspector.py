from core.token_inspector import TokenInspector


def test_token_inspector_titan():
    # Aman'Thul
    tokens = TokenInspector.get_tokens("TTN_903", "阿曼苏尔")
    assert len(tokens) == 3
    names = [t.name for t in tokens]
    assert "清除异端" in names

    summary = TokenInspector.format_token_summary("TTN_903", "阿曼苏尔")
    assert "清除异端" in summary
    assert "衍生物/技能推演" in summary


def test_token_inspector_empty():
    tokens = TokenInspector.get_tokens("UNKNOWN_ID", "普通小野猪")
    assert tokens == []
    assert TokenInspector.format_token_summary("UNKNOWN_ID", "普通小野猪") == ""
