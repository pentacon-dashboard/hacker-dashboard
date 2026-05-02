import { test, expect } from "@playwright/test";
import { mockBaseApis } from "./fixtures/api";

test("legacy /watchlist route redirects to the customer book main page", async ({
  page,
}) => {
  await mockBaseApis(page);
  await page.goto("/watchlist");

  await expect(page).toHaveURL(/\/$/);
  await expect(page.getByTestId("dashboard-home")).toBeVisible({
    timeout: 10_000,
  });
});
