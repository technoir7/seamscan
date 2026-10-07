from playwright.sync_api import Page, expect


def test_login_page_title(page: Page):
    page.goto("http://localhost:3000/login")
    expect(page).to_have_title("Sign in")


def test_login_button_visible(page: Page):
    page.goto("http://localhost:3000/login")
    expect(page.get_by_role("button", name="Sign in")).to_be_visible()
