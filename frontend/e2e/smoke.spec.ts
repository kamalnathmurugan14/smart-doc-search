import { expect, test } from "@playwright/test";

test("index sample docs, search, explain, find duplicates", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByText("Nothing is indexed yet")).toBeVisible();

  await page.getByRole("navigation", { name: "Main" }).getByRole("link", { name: "Settings" }).click();
  await page.getByRole("button", { name: "Re-index", exact: true }).click();
  await expect(page.getByRole("status").filter({ hasText: "Indexed" })).toBeVisible({ timeout: 20_000 });

  await page.getByRole("navigation", { name: "Main" }).getByRole("link", { name: "Search" }).click();
  await page.getByRole("searchbox", { name: "Search documents" }).fill("renewal contract");
  await page.getByRole("button", { name: "keyword" }).click();
  await page.getByRole("button", { name: "Search", exact: true }).click();
  const first = page.locator("article").first();
  await expect(first).toContainText("contract.txt");
  await expect(first.locator("mark").first()).toBeVisible();

  await first.getByRole("button", { name: "Explain" }).click();
  await expect(page.getByRole("dialog", { name: "Explain result" })).toContainText("Keyword (BM25)");
  await page.getByRole("button", { name: "Close" }).click();

  await page.getByRole("navigation", { name: "Main" }).getByRole("link", { name: "Duplicates" }).click();
  await expect(page.getByText("Exact duplicates")).toBeVisible();
  await expect(page.getByText("contract_copy.txt")).toBeVisible();

  await page.getByRole("button", { name: "Toggle theme" }).click();
  await expect(page.locator("html")).toHaveAttribute("data-theme", /dark|light/);
});
