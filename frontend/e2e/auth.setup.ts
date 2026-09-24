import { test as setup } from '@playwright/test';

const BASE_URL = 'http://localhost:5173';
const API_URL = 'http://localhost:8000';
const TEST_EMAIL = 'test@flowalchemy.dev';
const TEST_PASSWORD = 'Test1234';
const AUTH_FILE = 'e2e/.auth/user.json';

setup('authenticate via API', async ({ page }) => {
  const res = await page.request.post(`${API_URL}/api/auth/login`, {
    data: { email: TEST_EMAIL, password: TEST_PASSWORD },
  });
  const data = await res.json();

  await page.goto(BASE_URL);
  await page.waitForLoadState('networkidle');

  const token = data.access_token;
  await page.evaluate((t: string) => {
    window.localStorage.setItem('access_token', t);
  }, token);

  await page.context().storageState({ path: AUTH_FILE });
});
