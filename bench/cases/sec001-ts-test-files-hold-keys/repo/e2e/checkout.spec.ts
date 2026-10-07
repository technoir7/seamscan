import { test, expect } from "@playwright/test";

const LIVE_KEY_THAT_MUST_NOT_LEAK = "{{FAKE_STRIPE_LIVE}}";

test("checkout page never renders the secret key", async ({ page }) => {
  await page.goto("/checkout");
  await expect(page.locator("body")).not.toContainText(LIVE_KEY_THAT_MUST_NOT_LEAK);
});
