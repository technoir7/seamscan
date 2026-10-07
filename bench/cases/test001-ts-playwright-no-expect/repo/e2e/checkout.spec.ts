import { expect, test } from "@playwright/test";

test.describe("checkout", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/shop");
  });

  test("guest can pay with a test card", async ({ page }) => {
    await page.getByRole("button", { name: "Add to cart" }).first().click();
    await page.getByRole("link", { name: "Checkout" }).click();
    await page.getByLabel("Email").fill("ada@example.com");
    await page.getByLabel("Card number").fill("4242 4242 4242 4242");
    await page.getByRole("button", { name: "Pay now" }).click();
  });

  test("empty cart shows a hint", async ({ page }) => {
    await page.getByRole("link", { name: "Checkout" }).click();
    await expect(page.getByText("Your cart is empty")).toBeVisible();
  });
});
