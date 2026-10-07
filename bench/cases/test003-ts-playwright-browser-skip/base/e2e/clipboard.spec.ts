import { expect, test } from "@playwright/test";

test("copies the invite link", async ({ page }) => {
  await page.goto("/team");
  await page.getByRole("button", { name: "Copy invite link" }).click();
  await expect(page.getByText("Link copied")).toBeVisible();
});
