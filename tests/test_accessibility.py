"""Stage 1 accessibility gate: static checks on the widget plus the axe-core audit page."""

import pytest

from assistant.config import PACKAGE_DIR, PROJECT_ROOT

WIDGET = PACKAGE_DIR / "widget" / "assistant.js"
WCAG_REPORT = PROJECT_ROOT / "docs" / "WCAG_2.2_AA_Report.md"


@pytest.fixture(scope="module")
def widget_source() -> str:
    return WIDGET.read_text(encoding="utf-8")


def test_audit_page_bundles_axe_core(client):
    res = client.get("/a11y-audit")
    assert res.status_code == 200
    assert "Stage 1 Accessibility Gate" in res.text
    assert "axe.min.js" in res.text


def test_widget_has_polite_live_log(widget_source):
    assert 'role="log"' in widget_source
    assert 'aria-live="polite"' in widget_source
    assert 'aria-atomic="false"' in widget_source


def test_widget_launcher_meets_target_size(widget_source):
    """WCAG 2.2 AA needs 24px; the launcher targets 48px for motor accessibility."""
    assert "min-width: 48px" in widget_source
    assert "min-height: 48px" in widget_source


def test_widget_escape_closes_and_restores_focus(widget_source):
    assert "e.key === 'Escape'" in widget_source
    assert "this.launcher.focus()" in widget_source


def test_widget_label_in_name(widget_source):
    """WCAG 2.5.3: each accessible name contains the visible label."""
    assert 'aria-label="Ask Tutor / ረዳት - AI Learning Assistant"' in widget_source
    assert 'aria-label="English / አማርኛ - Switch language"' in widget_source
    assert 'aria-label="Live Human Help - Request human tutor help"' in widget_source


def test_widget_escalates_through_the_api(widget_source):
    """Human help must go through /api/escalate so tickets are logged and staff can see them."""
    assert "/escalate" in widget_source


def test_wcag_conformance_report_is_complete():
    text = WCAG_REPORT.read_text(encoding="utf-8")
    assert "WCAG 2.2 Level AA" in text
    assert "0 Critical" in text
    assert "0 Serious" in text
    for number, principle in enumerate(("Perceivable", "Operable", "Understandable", "Robust"), start=1):
        assert f"Principle {number}: {principle}" in text
