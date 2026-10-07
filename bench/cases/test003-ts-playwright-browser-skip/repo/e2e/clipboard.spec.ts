import { expect, test } from "@playwright/test";

test.describe("clipboard", () => {
  test.skip(({ browserName }) => browserName !== "chromium", "clipboard permissions are Chromium-only");

  test("copies the invite link", async ({ page }) => {
    await page.goto("/team");
    await page.getByRole("button", { name: "Copy invite link" }).click();
    await expect(page.getByText("Link copied")).toBeVisible();
  });

  test("pastes into the search box", async ({ page, browserName, isMobile }) => {
    test.skip(browserName === "webkit" || isMobile, "no clipboard read on WebKit or mobile");
    await page.goto("/team");
    await page.keyboard.press("ControlOrMeta+V");
    await expect(page.getByRole("searchbox")).not.toBeEmpty();
  });
});
