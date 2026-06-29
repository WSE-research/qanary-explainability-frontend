"""Unit tests for util.py — the importable logic of the explanation frontend."""
import util


def test_include_css_concatenates_into_style_tag(tmp_path):
    a = tmp_path / "a.css"
    b = tmp_path / "b.css"
    a.write_text("body{color:red}", encoding="utf-8")
    b.write_text(".x{margin:0}", encoding="utf-8")

    captured = {}

    class _FakeSt:
        def markdown(self, html, unsafe_allow_html=False):
            captured["html"] = html
            captured["unsafe"] = unsafe_allow_html

    util.include_css(_FakeSt(), [str(a), str(b)])
    assert captured["unsafe"] is True
    assert captured["html"].startswith("<style>")
    assert "body{color:red}" in captured["html"]
    assert ".x{margin:0}" in captured["html"]


def test_get_random_element_returns_a_member():
    items = ["a", "b", "c"]
    for _ in range(20):
        assert util.get_random_element(items) in items


def test_feedback_collections_are_non_empty():
    assert len(util.feedback_messages) > 0
    assert len(util.feedback_icons) > 0
    assert all(isinstance(m, str) for m in util.feedback_messages)
