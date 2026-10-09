import { test } from "@playwright/test";
import { DashboardPage } from "./pages/dashboard";

test("member signs in", async ({ page }) => {
  await page.goto("/login");
  await page.getByLabel("Email").fill("ada@example.com");
  await page.getByRole("button", { name: "Sign in" }).click();
  await page.waitForURL("**/dashboard");
});

test("dashboard loads after sign in", async ({ page }) => {
  await page.goto("/dashboard");
  await new DashboardPage(page).expectLoaded();
});
