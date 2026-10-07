import { expect, test } from "@playwright/test";
import { db } from "./helpers/db";

test("shows the feed", async ({ page }) => {
  await page.goto("/feed");
  await expect(page.getByRole("feed")).toBeVisible();
});

// it's slow on the first run while Next compiles the route
test("paginates with the next button", async ({ page }) => {
  const second = await db.post.findMany({ skip: 20, take: 20, orderBy: { id: "desc" } });
  await page.goto("/feed");
  await test.step("skip the onboarding tour", async () => {
    await page.getByRole("button", { name: "Skip" }).click();
  });
  await page.getByRole("button", { name: "Next" }).click();
  await expect(page.getByRole("article").first()).toContainText(second[0].title);
});
