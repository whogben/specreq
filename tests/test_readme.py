"""Ensure README.md links are absolute (work on PyPI, not just GitHub)."""

import re
from pathlib import Path

README = Path(__file__).resolve().parent.parent / "README.md"

# Matches [text](url) — captures the url part
MD_LINK_RE = re.compile(r"\[(?:[^\]\\]|\\.)*\]\(([^)]+)\)")


def test_readme_links_are_absolute():
    """All links in README.md must use absolute URLs (http/https)."""
    if not README.exists():
        pytest.skip("README.md not found")  # noqa: F821

    text = README.read_text()
    links = MD_LINK_RE.findall(text)
    if not links:
        # No links to validate
        return

    relative = [url for url in links if not url.startswith(("http://", "https://"))]
    assert not relative, (
        f"README.md has {len(relative)} relative link(s); "
        f"use absolute URLs so they work on PyPI:\n"
        + "\n".join(f"  - {r}" for r in relative)
    )
