import { test } from "@playwright/test";

test.describe("billing", () => {
  test.fixme("applies a coupon", async ({ page }) => {
    await page.goto("/billing");
  });

  test("visits the page", async ({ page }) => {
    await test.step("open billing", async () => {
      await page.goto("/billing");
    });
    await test.step("see invoices", async () => {
      await page.getByRole("link", { name: "Invoices" }).waitFor();
    });
  });
});
