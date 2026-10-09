import re

from playwright.sync_api import Page, expect


def _verify_dashboard(page: Page):
    expect(page.get_by_role("heading", name="Dashboard")).to_be_visible()


def test_title(page: Page):
    page.goto("http://localhost:3000/")
    expect(page).to_have_title(re.compile("Acme"))


def test_member_signs_in(page: Page):
    page.goto("http://localhost:3000/login")
    page.get_by_label("Email").fill("ada@example.com")
    page.get_by_label("Password").fill("hunter2")
    page.get_by_role("button", name="Sign in").click()
    _verify_dashboard(page)
