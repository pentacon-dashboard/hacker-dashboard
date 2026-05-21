import { test, expect } from "@playwright/test";
import { mockBaseApis } from "./fixtures/api";

test("/watchlist route renders the watchlist workspace", async ({
  page,
}) => {
  await mockBaseApis(page);
  await page.goto("/watchlist");

  await expect(page).toHaveURL(/\/watchlist(?:[?#].*)?$/);
  await expect(page.getByTestId("watchlist-page")).toBeVisible({
    timeout: 10_000,
  });
  await expect(page.getByTestId("watchlist-items-section")).toBeVisible();
});
