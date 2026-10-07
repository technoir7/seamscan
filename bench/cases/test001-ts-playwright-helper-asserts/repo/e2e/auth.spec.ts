import { expect, type Page, test } from "@playwright/test";

async function signIn(page: Page, email: string, password: string) {
  await page.goto("/login");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill(password);
  await page.getByRole("button", { name: "Sign in" }).click();
}

const landsOnDashboard = async (page: Page) => {
  await expect(page).toHaveURL(/\/dashboard$/);
  await expect(page.getByRole("heading", { name: "Your projects" })).toBeVisible();
};

class LoginPage {
  constructor(private readonly page: Page) {}

  async seesError(message: string) {
    await expect(this.page.getByRole("alert")).toHaveText(message);
  }
}

test("member signs in", async ({ page }) => {
  await signIn(page, "ada@example.com", "correct-horse-battery");
  await landsOnDashboard(page);
});

test("wrong password shows an error", async ({ page }) => {
  await signIn(page, "ada@example.com", "nope");
  await new LoginPage(page).seesError("Invalid email or password");
});
