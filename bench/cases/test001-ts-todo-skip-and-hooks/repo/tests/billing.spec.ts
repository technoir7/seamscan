import { expect, test } from "@playwright/test";

test.describe("billing", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/settings/billing");
  });

  test.afterEach(async ({ page }) => {
    await page.context().clearCookies();
  });

  test.todo("downgrades at the end of the period");

  test("shows the current plan", async ({ page }) => {
    await test.step("open the plan card", async () => {
      await page.getByRole("button", { name: "Plan details" }).click();
    });
    await expect(page.getByText("Pro · monthly")).toBeVisible();
  });
});
