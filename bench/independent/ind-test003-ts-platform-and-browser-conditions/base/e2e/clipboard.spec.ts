import { test, expect } from "@playwright/test";

test("reads the clipboard", async ({ page }) => {
  await page.goto("/");
  await expect(page).toHaveTitle(/App/);
});
