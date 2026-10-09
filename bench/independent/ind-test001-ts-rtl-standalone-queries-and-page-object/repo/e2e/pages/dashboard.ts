import { expect, type Page } from "@playwright/test";

export class DashboardPage {
  constructor(private page: Page) {}
  async expectLoaded() {
    await expect(this.page.getByRole("heading", { name: "Dashboard" })).toBeVisible();
  }
}
