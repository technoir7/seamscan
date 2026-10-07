import { expect, test } from "@playwright/test";

test("shows the feed", async ({ page }) => {
  await page.goto("/feed");
  await expect(page.getByRole("feed")).toBeVisible();
});
