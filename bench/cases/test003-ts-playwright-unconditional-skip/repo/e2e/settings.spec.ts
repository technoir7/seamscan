import { expect, test } from "@playwright/test";

test("changes the display name", async ({ page }) => {
  test.fixme();
  await page.goto("/settings");
  await page.getByLabel("Display name").fill("Ada L.");
  await page.getByRole("button", { name: "Save" }).click();
  await expect(page.getByText("Saved")).toBeVisible();
});

test("deletes the account", async ({ page }) => {
  test.skip(process.env.CI === "true", "times out on CI");
  await page.goto("/settings/danger");
  await page.getByRole("button", { name: "Delete account" }).click();
  await expect(page).toHaveURL("/goodbye");
});
