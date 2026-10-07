import { expect, test } from "@playwright/test";

test("new user finishes onboarding", async ({ page }) => {
  await page.goto("/onboarding");
  await page.getByLabel("Team name").fill("Acme");
  await page.getByRole("button", { name: "Continue" }).click();
  await expect(page).toHaveURL("/dashboard");
});

test("invites a teammate during onboarding", async ({ page }) => {
  await page.goto("/onboarding/invite");
  await page.getByLabel("Email").fill("grace@example.com");
  await page.getByRole("button", { name: "Send invite" }).click();
  await expect(page.getByText("Invite sent")).toBeVisible();
});
