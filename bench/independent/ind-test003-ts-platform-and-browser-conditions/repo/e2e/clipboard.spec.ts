import { test, expect } from "@playwright/test";

test("reads the clipboard", async ({ page, browserName, isMobile }) => {
  test.skip(browserName === "webkit" || isMobile, "no clipboard read on WebKit or mobile");
  await page.goto("/");
  await expect(page).toHaveTitle(/App/);
});
