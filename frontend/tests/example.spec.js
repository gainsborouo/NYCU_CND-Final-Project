// @ts-check
import { test, expect } from '@playwright/test';

test('has title', async ({ page }) => {
  await page.goto('http://localhost:5173');

  // Expect a title "to contain" a substring.
  await expect(page).toHaveTitle('Document Center');
});

test('displays Document Center heading', async ({ page }) => {
  await page.goto('http://localhost:5173');
  
  // Check if the main heading exists
  const heading = page.locator('h1:has-text("Document Center")');
  await expect(heading).toBeVisible();
});

test('displays tagline', async ({ page }) => {
  await page.goto('http://localhost:5173');
  
  // Check if the tagline text exists
  const tagline = page.locator('p:has-text("A collaborative platform")');
  await expect(tagline).toBeVisible();
});

test('has Get Started button', async ({ page }) => {
  await page.goto('http://localhost:5173');
  
  // Check if the Get Started button exists
  const button = page.getByRole('link', { name: 'Get Started' });
  await expect(button).toBeVisible();
  
  // Check if it points to the login page
  await expect(button).toHaveAttribute('href', '/login');
});

