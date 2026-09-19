"""
Phone-width layout checks.

The header carries the brand plus the menu button, the season select and the
theme pill. The select shipped unstyled, so it rendered at the width of its
longest option and pushed the theme pill past the right edge of a 390px
screen. Anything that widens those controls again shows up here as a page
that scrolls sideways.
"""

import pytest
from playwright.sync_api import expect

from src.models.models import Season

pytestmark = [pytest.mark.e2e, pytest.mark.slow]

PHONE = {"width": 390, "height": 844}


@pytest.mark.parametrize("page_file", ["index.html", "games.html", "comparison.html"])
def test_no_horizontal_overflow_on_a_phone(test_db, browser_page, page_file):
    # The select is only as wide as its options, so an empty season list would
    # pass this test no matter how the labels are written.
    test_db.add_all([
        Season(year=2026, current_week=6, is_active=True),
        Season(year=2025, current_week=15, is_active=False),
        Season(year=2024, current_week=15, is_active=False),
    ])
    test_db.commit()

    page, base_url = browser_page
    page.set_viewport_size(PHONE)

    page.goto(f"{base_url}/frontend/{page_file}")
    page.wait_for_selector(".tkr-header")
    page.wait_for_timeout(300)  # season.js fills the select after DOMContentLoaded

    # The ticker tape and the bracket are their own scroll containers; the page
    # itself must not scroll sideways.
    page.evaluate("window.scrollTo(300, 0)")
    assert page.evaluate("window.scrollX") == 0

    pill = page.locator("#theme-toggle")
    expect(pill).to_be_visible()
    assert pill.bounding_box()["x"] + pill.bounding_box()["width"] <= PHONE["width"]
