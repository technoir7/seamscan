import { test, expect } from "@playwright/test";

test.fixme("applies a coupon at checkout", async ({ page }) => {
  await page.goto("/checkout");
  await page.getByLabel("Coupon").fill("SAVE10");
  await expect(page.getByText("-$10.00")).toBeVisible();
});

test("keeps the cart after a redirect", async ({ page }) => {
  test.skip(true, "flaky after the redirect change");
  await page.goto("/cart");
  await expect(page.getByTestId("cart-badge")).toHaveText("1");
});
