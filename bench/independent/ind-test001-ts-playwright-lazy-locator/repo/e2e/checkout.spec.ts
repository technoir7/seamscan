import { test, expect } from "@playwright/test";

test("shows the cart badge", async ({ page }) => {
  await page.goto("/shop");
  await expect(page.getByTestId("cart-badge")).toHaveText("0");
});

test("guest can pay with a test card", async ({ page }) => {
  await page.goto("/checkout");
  await page.getByLabel("Card number").fill("4242 4242 4242 4242");
  await page.getByRole("button", { name: "Pay now" }).click();
  page.getByText("Order confirmed");
});
