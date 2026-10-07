import { expect, test } from "@playwright/test";

test("adds an item to the cart", async ({ page }) => {
  await page.goto("/products/tee-black");
  await page.getByRole("button", { name: "Add to cart" }).click();
  await expect(page.getByTestId("cart-count")).toHaveText("1");
});

test("applies a coupon at checkout", async ({ page }) => {
  await page.goto("/checkout");
  await page.getByLabel("Coupon").fill("WELCOME10");
  await page.getByRole("button", { name: "Apply" }).click();
  await expect(page.getByTestId("discount")).toHaveText("-$2.50");
});
