import { expect, test } from "@playwright/test";

test("uploaded avatar appears in the header", async ({ page }) => {
  await page.goto("/settings/profile");
  await page.getByLabel("Avatar").setInputFiles("e2e/fixtures/avatar.png");
  await expect
    .poll(async () => (await page.request.get("/api/me")).json())
    .toMatchObject({ avatarUrl: expect.stringContaining("avatars/") });
});

test("profile page layout", async ({ page }) => {
  await page.goto("/settings/profile");
  await expect.soft(page.getByRole("heading", { name: "Profile" })).toBeVisible();
  await expect(page).toHaveScreenshot("profile.png");
});

test("redirects to login when signed out", async ({ browser }) => {
  const context = await browser.newContext({ storageState: undefined });
  const page = await context.newPage();
  await page.goto("/settings/profile");
  await page.waitForURL("**/login?next=%2Fsettings%2Fprofile");
});
