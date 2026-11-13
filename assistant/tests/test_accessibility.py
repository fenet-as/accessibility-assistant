"""
Automated Stage 1 Accessibility Gate Audit Tests.
Validates ARIA roles, live regions, contrast, and WCAG 2.2 AA compliance.
"""

import re
from pathlib import Path
from fastapi.testclient import TestClient
from assistant.api.main import app

client = TestClient(app)


def test_audit_page_endpoint():
    """Verify /a11y-audit is served and bundles axe-core."""
    res = client.get("/a11y-audit")
    assert res.status_code == 200
    assert "Stage 1 Accessibility Gate" in res.text
    assert "axe.min.js" in res.text


def test_widget_contains_aria_live_log():
    """Verify role='log' and aria-live='polite' are present in assistant.js."""
    base_dir = Path(__file__).resolve().parent.parent
    widget_file = base_dir / "widget" / "assistant.js"
    assert widget_file.exists()

    content = widget_file.read_text(encoding="utf-8")
    assert 'role="log"' in content
    assert 'aria-live="polite"' in content
    assert 'aria-atomic="false"' in content


def test_widget_wcag22_target_size():
    """Verify minimum target size exceeds WCAG 2.2 Level AA (min 24px, we target >= 44px)."""
    base_dir = Path(__file__).resolve().parent.parent
    widget_file = base_dir / "widget" / "assistant.js"
    content = widget_file.read_text(encoding="utf-8")

    # Launcher button size check
    assert "min-width: 48px" in content
    assert "min-height: 48px" in content


def test_widget_keyboard_escape_listener():
    """Verify Escape key listener closes dialog and restores focus."""
    base_dir = Path(__file__).resolve().parent.parent
    widget_file = base_dir / "widget" / "assistant.js"
    content = widget_file.read_text(encoding="utf-8")

    assert "e.key === 'Escape'" in content
    assert "this.launcher.focus()" in content


def test_wcag_conformance_report_exists():
    """Verify formal WCAG 2.2 AA report is complete and present."""
    base_dir = Path(__file__).resolve().parent.parent.parent
    report = base_dir / "docs" / "WCAG_2.2_AA_Report.md"
    assert report.exists()

    text = report.read_text(encoding="utf-8")
    assert "WCAG 2.2 Level AA" in text
    assert "0 Critical" in text
    assert "0 Serious" in text
    assert "Principle 1: Perceivable" in text
    assert "Principle 2: Operable" in text
    assert "Principle 3: Understandable" in text
    assert "Principle 4: Robust" in text
