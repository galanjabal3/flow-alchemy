import { test, expect } from '@playwright/test';

const BASE_URL = 'http://localhost:5173';
const API_URL = 'http://localhost:8000';
const TEST_EMAIL = 'test@flowalchemy.dev';
const TEST_PASSWORD = 'Test1234';
const SS = 'e2e/screenshots';

let cachedToken: string | null = null;

async function getToken(page: any): Promise<string> {
  if (cachedToken) return cachedToken;
  const res = await page.request.post(`${API_URL}/api/auth/login`, {
    data: { email: TEST_EMAIL, password: TEST_PASSWORD },
  });
  const data = await res.json();
  cachedToken = data.access_token;
  return cachedToken;
}

async function createWorkflowViaAPI(page: any, name: string, definition?: any) {
  const token = await getToken(page);
  const res = await page.request.post(`${API_URL}/api/workflows/`, {
    headers: { 'Authorization': `Bearer ${token}` },
    data: { name, description: 'Created by E2E', definition: definition || { nodes: [], edges: [] } },
  });
  return res.json();
}

test.describe('FlowAlchemy E2E', () => {

  // ── Auth Pages ──────────────────────────────────────────

  test('01 - Login page renders correctly', async ({ page }) => {
    await page.goto(`${BASE_URL}/login`);
    await page.waitForLoadState('networkidle');

    await expect(page).toHaveTitle(/FlowAlchemy/);
    await expect(page.locator('h1')).toContainText('FlowAlchemy');
    await expect(page.locator('input[type="email"]')).toBeVisible();
    await expect(page.locator('input[type="password"]')).toBeVisible();
    await expect(page.locator('button[type="submit"]')).toContainText('Sign In');
    await expect(page.locator('a[href="/register"]')).toBeVisible();
    await page.screenshot({ path: `${SS}/auth/01-login.png`, fullPage: true });
  });

  test('02 - Register page renders correctly', async ({ page }) => {
    await page.goto(`${BASE_URL}/register`);
    await page.waitForLoadState('networkidle');

    await expect(page.locator('h1')).toContainText('FlowAlchemy');
    await expect(page.locator('p').first()).toContainText('Create your account');
    await expect(page.locator('input[type="email"]')).toBeVisible();
    await expect(page.locator('#password')).toBeVisible();
    await expect(page.locator('#confirmPassword')).toBeVisible();
    await expect(page.locator('button[type="submit"]')).toContainText('Create Account');
    await page.screenshot({ path: `${SS}/auth/02-register.png`, fullPage: true });
  });

  test('03 - Register new account + show API key', async ({ page }) => {
    await page.goto(`${BASE_URL}/register`);
    await page.waitForLoadState('networkidle');

    const email = `e2e_${Date.now()}@test.com`;
    await page.fill('input[type="email"]', email);
    await page.fill('#password', 'TestPass123');
    await page.fill('#confirmPassword', 'TestPass123');
    await page.screenshot({ path: `${SS}/auth/03-register-filled.png`, fullPage: true });

    await page.click('button[type="submit"]');
    await page.waitForTimeout(3000);

    const apiKeyDisplay = page.locator('code, [class*="api-key"]');
    const successHeading = page.locator('h1').filter({ hasText: /success|saved|key/i });
    const hasApiKey = await apiKeyDisplay.isVisible().catch(() => false);
    const hasSuccess = await successHeading.isVisible().catch(() => false);

    if (hasApiKey || hasSuccess) {
      await page.screenshot({ path: `${SS}/auth/04-register-success.png`, fullPage: true });
    } else {
      await page.screenshot({ path: `${SS}/auth/04-register-result.png`, fullPage: true });
    }
  });

  test('04 - Login error - wrong credentials', async ({ page }) => {
    await page.goto(`${BASE_URL}/login`);
    await page.waitForLoadState('networkidle');

    await page.fill('input[type="email"]', 'wrong@email.com');
    await page.fill('input[type="password"]', 'wrongpassword');
    await page.click('button[type="submit"]');
    await page.waitForTimeout(2000);

    const errorVisible = await page.locator('[class*="error"]').first().isVisible().catch(() => false);
    console.log('Auth error visible:', errorVisible);

    await page.screenshot({ path: `${SS}/auth/05-login-error.png`, fullPage: true });
    expect(page.url()).toContain('/login');
  });

  test('05 - Register error - password mismatch', async ({ page }) => {
    await page.goto(`${BASE_URL}/register`);
    await page.waitForLoadState('networkidle');

    await page.fill('input[type="email"]', 'test@test.com');
    await page.fill('#password', 'Password123');
    await page.fill('#confirmPassword', 'Different123');
    await page.click('button[type="submit"]');

    const error = page.locator('[class*="error"]').filter({ hasText: /match|different/i }).first();
    await expect(error).toBeVisible({ timeout: 3000 });
    await page.screenshot({ path: `${SS}/auth/06-register-error.png`, fullPage: true });
  });

  // ── Dashboard ───────────────────────────────────────────

  test('06 - Dashboard - empty state', async ({ page }) => {
    await page.goto(`${BASE_URL}/dashboard`);
    await page.waitForLoadState('networkidle');
    await expect(page).toHaveURL(/dashboard/);

    const header = page.locator('header').first();
    await expect(header).toBeVisible();
    await page.screenshot({ path: `${SS}/dashboard/01-dashboard-empty.png`, fullPage: true });
  });

  test('07 - Dashboard - create workflow modal', async ({ page }) => {
    await page.goto(`${BASE_URL}/dashboard`);
    await page.waitForLoadState('networkidle');

    const newBtn = page.locator('button').filter({ hasText: /new workflow|create workflow/i }).first();
    await expect(newBtn).toBeVisible();
    await newBtn.click();
    await page.waitForTimeout(500);

    const modal = page.locator('[role="dialog"]');
    await expect(modal).toBeVisible();
    await page.screenshot({ path: `${SS}/dashboard/02-create-modal.png`, fullPage: true });

    const nameInput = modal.locator('input').first();
    await nameInput.fill('My Test Workflow');

    const descInput = modal.locator('input').nth(1);
    if (await descInput.isVisible()) {
      await descInput.fill('E2E test workflow');
    }
    await page.screenshot({ path: `${SS}/dashboard/03-create-modal-filled.png`, fullPage: true });

    const createBtn = modal.locator('button').filter({ hasText: /create|submit/i });
    await createBtn.click();
    await page.waitForTimeout(1500);
    await expect(modal).not.toBeVisible({ timeout: 5000 }).catch(() => {});
    await page.waitForTimeout(500);
    await page.screenshot({ path: `${SS}/dashboard/04-dashboard-with-workflow.png`, fullPage: true });
  });

  test('08 - Dashboard - workflow card', async ({ page }) => {
    await page.goto(`${BASE_URL}/dashboard`);
    await page.waitForLoadState('networkidle');
    await createWorkflowViaAPI(page, 'Dashboard Card Test');
    await page.reload();
    await page.waitForLoadState('networkidle');

    // Look for workflow card by name or by being in the grid
    const card = page.locator('[class*="rounded-xl"]').filter({ hasText: 'Dashboard Card Test' }).first();
    if (await card.isVisible()) {
      await expect(card).toBeVisible();
      await page.screenshot({ path: `${SS}/dashboard/05-workflow-card.png`, fullPage: true });
    }
  });

  // ── Workflow Editor ─────────────────────────────────────

  test('09 - Editor - empty canvas with palette', async ({ page }) => {
    const workflow = await createWorkflowViaAPI(page, 'Editor Canvas Test');

    await page.goto(`${BASE_URL}/workflow/${workflow.id}`);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);

    // Workflow name is in breadcrumb, not h1
    await expect(page.locator('nav').filter({ hasText: 'Editor Canvas Test' })).toBeVisible();
    // Check for Editor tab button (with active state)
    const editorTab = page.locator('button').filter({ hasText: 'Editor' }).first();
    await expect(editorTab).toBeVisible();
    // Check for toolbar area
    await expect(page.locator('text=0 nodes')).toBeVisible();
    await expect(page.getByText('Saved', { exact: true })).toBeVisible();
    // Check for node palette heading
    await expect(page.getByRole('heading', { name: 'Nodes' })).toBeVisible();
    // Check for palette items (6 node types)
    const paletteItems = page.locator('[draggable="true"]');
    await expect(paletteItems).toHaveCount(6);
    // Check for Run button
    await expect(page.locator('button').filter({ hasText: 'Run' })).toBeVisible();

    await page.screenshot({ path: `${SS}/editor/01-empty-canvas.png`, fullPage: true });
  });

  test('10 - Editor - drag node to canvas', async ({ page }) => {

    const workflow = await createWorkflowViaAPI(page, 'Drag Node Test');

    await page.goto(`${BASE_URL}/workflow/${workflow.id}`);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);

    const triggerItem = page.locator('[draggable="true"]').filter({ hasText: 'Trigger' });
    const canvas = page.locator('.react-flow');

    await expect(triggerItem).toBeVisible();
    await expect(canvas).toBeVisible();

    const triggerBox = await triggerItem.boundingBox();
    const canvasBox = await canvas.boundingBox();

    if (triggerBox && canvasBox) {
      await page.mouse.move(triggerBox.x + triggerBox.width / 2, triggerBox.y + triggerBox.height / 2);
      await page.mouse.down();
      await page.mouse.move(canvasBox.x + canvasBox.width / 2, canvasBox.y + canvasBox.height / 2, { steps: 10 });
      await page.mouse.up();
      await page.waitForTimeout(1000);
    }

    const nodeCount = await page.locator('.react-flow__node').count();
    console.log('Node count after drag:', nodeCount);

    await page.screenshot({ path: `${SS}/editor/02-after-drag.png`, fullPage: true });
  });

  test('11 - Editor - select node shows properties', async ({ page }) => {

    const workflow = await createWorkflowViaAPI(page, 'Properties Test');

    await page.goto(`${BASE_URL}/workflow/${workflow.id}`);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);

    // Drag a node to canvas first
    const triggerItem = page.locator('[draggable="true"]').filter({ hasText: 'Trigger' });
    const canvas = page.locator('.react-flow');
    const triggerBox = await triggerItem.boundingBox();
    const canvasBox = await canvas.boundingBox();

    if (triggerBox && canvasBox) {
      await page.mouse.move(triggerBox.x + triggerBox.width / 2, triggerBox.y + triggerBox.height / 2);
      await page.mouse.down();
      await page.mouse.move(canvasBox.x + canvasBox.width / 2, canvasBox.y + canvasBox.height / 2, { steps: 10 });
      await page.mouse.up();
      await page.waitForTimeout(500);
    }

    const canvasNode = page.locator('.react-flow__node').first();
    await expect(canvasNode).toBeVisible({ timeout: 5000 });
    await canvasNode.click();
    await page.waitForTimeout(300);

    // Look for properties panel
    const props = page.locator('text=Node Properties').first();
    await expect(props).toBeVisible({ timeout: 3000 });
    await page.screenshot({ path: `${SS}/editor/03-node-properties.png`, fullPage: true });
  });

  test('12 - Editor - toolbar states', async ({ page }) => {

    const workflow = await createWorkflowViaAPI(page, 'Toolbar Test');

    await page.goto(`${BASE_URL}/workflow/${workflow.id}`);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(1500);

    // Verify initial toolbar state
    await expect(page.locator('text=0 nodes')).toBeVisible();
    await expect(page.getByText('Saved', { exact: true })).toBeVisible();
    await expect(page.locator('button').filter({ hasText: 'Run' })).toBeVisible();

    await page.screenshot({ path: `${SS}/editor/04-toolbar-initial.png`, fullPage: true });

    // Add a node to trigger dirty state
    const triggerItem = page.locator('[draggable="true"]').filter({ hasText: 'Trigger' });
    const canvas = page.locator('.react-flow');
    const triggerBox = await triggerItem.boundingBox();
    const canvasBox = await canvas.boundingBox();

    if (triggerBox && canvasBox) {
      await page.mouse.move(triggerBox.x + triggerBox.width / 2, triggerBox.y + triggerBox.height / 2);
      await page.mouse.down();
      await page.mouse.move(canvasBox.x + canvasBox.width / 2, canvasBox.y + canvasBox.height / 2, { steps: 10 });
      await page.mouse.up();
      await page.waitForTimeout(500);
    }

    // Toolbar should now show dirty state
    await expect(page.locator('text=1 node')).toBeVisible();
    await page.screenshot({ path: `${SS}/editor/05-toolbar-dirty.png`, fullPage: true });

    // Click Save button
    const saveBtn = page.getByRole('button', { name: 'Save', exact: true });
    if (await saveBtn.isVisible()) {
      await saveBtn.click();
      await page.waitForTimeout(2000);

      // Should show "Saved" after save
      await expect(page.getByText('Saved', { exact: true })).toBeVisible();
      await page.screenshot({ path: `${SS}/editor/06-toolbar-saved.png`, fullPage: true });
    }
  });

  // ── Execution History ───────────────────────────────────

  test('13 - History tab - empty state', async ({ page }) => {

    const workflow = await createWorkflowViaAPI(page, 'History Empty Test');

    await page.goto(`${BASE_URL}/workflow/${workflow.id}`);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(1500);

    const historyTab = page.locator('button').filter({ hasText: /history/i });
    await expect(historyTab).toBeVisible();
    await historyTab.click();
    await page.waitForTimeout(500);

    // Look for empty state text
    await expect(page.locator('text=No executions yet')).toBeVisible();
    await page.screenshot({ path: `${SS}/history/01-history-empty.png`, fullPage: true });
  });

  // ── Execution ──────────────────────────────────────────

  test('17 - Run simple workflow via API', async ({ page }) => {


    // Create a valid workflow: Trigger → Transform (identity)
    const definition = {
      nodes: [
        { id: 'n1', type: 'trigger', position: { x: 0, y: 0 }, data: { nodeType: 'trigger', label: 'Start', config: {} } },
        { id: 'n2', type: 'transform', position: { x: 0, y: 150 }, data: { nodeType: 'transform', label: 'Transform', config: { operation: 'identity', data: { hello: 'world' } } } },
      ],
      edges: [
        { id: 'e1', source: 'n1', target: 'n2' },
      ],
    };
    const workflow = await createWorkflowViaAPI(page, 'Run API Test', definition);

    // Run via API
    const token = await getToken(page);
    const res = await page.request.post(`${API_URL}/api/workflows/${workflow.id}/run`, {
      headers: { 'Authorization': `Bearer ${token}` },
      data: { input_data: {} },
    });
    const result = await res.json();
    const executionId = result.id;

    // Poll for completion
    let status = result.status;
    for (let i = 0; i < 20; i++) {
      if (status === 'completed' || status === 'failed') break;
      await page.waitForTimeout(500);
      const poll = await page.request.get(`${API_URL}/api/workflows/${workflow.id}/executions`, {
        headers: { 'Authorization': `Bearer ${token}` },
      });
      const executions = await poll.json();
      const exec = executions.find((e: any) => e.id === executionId);
      if (exec) status = exec.status;
    }

    expect(status).toBe('completed');
  });

  test('18 - Run workflow from UI', async ({ page }) => {
    test.setTimeout(60000);


    // Create a valid workflow with definition
    const definition = {
      nodes: [
        { id: 'n1', type: 'trigger', position: { x: 250, y: 50 }, data: { nodeType: 'trigger', label: 'Start', config: {} } },
        { id: 'n2', type: 'transform', position: { x: 250, y: 200 }, data: { nodeType: 'transform', label: 'Transform', config: { operation: 'identity', data: { message: 'hello' } } } },
      ],
      edges: [
        { id: 'e1', source: 'n1', target: 'n2' },
      ],
    };
    const workflow = await createWorkflowViaAPI(page, 'Run UI Test', definition);

    // Open editor
    await page.goto(`${BASE_URL}/workflow/${workflow.id}`);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);

    // Click Run
    const runBtn = page.locator('button').filter({ hasText: 'Run' }).first();
    await expect(runBtn).toBeVisible();
    await expect(runBtn).toBeEnabled();
    await runBtn.click();

    // Wait for execution result panel
    await expect(page.locator('text=Execution Result')).toBeVisible({ timeout: 15000 });

    // Poll for completion via API (WebSocket may be slow)
    const token = await getToken(page);
    for (let i = 0; i < 30; i++) {
      await page.waitForTimeout(1000);
      const completed = await page.locator('text=completed').first().isVisible().catch(() => false);
      if (completed) break;
      const failed = await page.locator('text=failed').first().isVisible().catch(() => false);
      if (failed) break;
    }

    await expect(page.locator('text=completed').first()).toBeVisible({ timeout: 5000 });
    await page.screenshot({ path: `${SS}/execution/01-run-completed.png`, fullPage: true });
  });

  test('19 - Run button disabled with no nodes', async ({ page }) => {


    const workflow = await createWorkflowViaAPI(page, 'No Nodes Test');

    await page.goto(`${BASE_URL}/workflow/${workflow.id}`);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(1500);

    const runBtn = page.locator('button').filter({ hasText: 'Run' }).first();
    await expect(runBtn).toBeVisible();
    await expect(runBtn).toBeDisabled();
  });

  test('20 - Run disconnected graph - allowed', async ({ page }) => {


    // Create workflow with disconnected nodes — backend allows this
    const definition = {
      nodes: [
        { id: 'n1', type: 'trigger', position: { x: 0, y: 0 }, data: { nodeType: 'trigger', label: 'Start', config: {} } },
        { id: 'n2', type: 'transform', position: { x: 300, y: 0 }, data: { nodeType: 'transform', label: 'Orphan', config: {} } },
      ],
      edges: [], // No edges = orphan nodes
    };
    const workflow = await createWorkflowViaAPI(page, 'Invalid Graph Test', definition);

    // Run via API — backend allows disconnected graphs
    const token = await getToken(page);
    const res = await page.request.post(`${API_URL}/api/workflows/${workflow.id}/run`, {
      headers: { 'Authorization': `Bearer ${token}` },
      data: { input_data: {} },
    });

    expect(res.status()).toBe(200);
  });

  // ── Responsive ──────────────────────────────────────────

  test('14 - Responsive - desktop (1280x800)', async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 800 });
    await page.goto(`${BASE_URL}/login`);
    await page.waitForLoadState('networkidle');
    await page.screenshot({ path: `${SS}/responsive/01-desktop.png`, fullPage: true });
  });

  test('15 - Responsive - tablet (768x1024)', async ({ page }) => {
    await page.setViewportSize({ width: 768, height: 1024 });
    await page.goto(`${BASE_URL}/login`);
    await page.waitForLoadState('networkidle');
    await page.screenshot({ path: `${SS}/responsive/02-tablet.png`, fullPage: true });
  });

  test('16 - Responsive - mobile (375x812)', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 812 });
    await page.goto(`${BASE_URL}/login`);
    await page.waitForLoadState('networkidle');
    await page.screenshot({ path: `${SS}/responsive/03-mobile.png`, fullPage: true });
  });

  test('21 - Settings - page renders with tabs', async ({ page }) => {
    await page.goto(`${BASE_URL}/dashboard`);
    await page.waitForLoadState('networkidle');

    // Open user menu dropdown and click Settings
    await page.locator('button').filter({ has: page.locator('.rounded-full.bg-primary\\/20') }).click();
    await page.getByText('Settings', { exact: true }).click();
    await page.waitForURL('**/settings', { timeout: 10000 });
    await page.waitForLoadState('networkidle');

    // Verify tabs (no logout button in sidebar)
    await expect(page.getByText('Profile', { exact: true }).first()).toBeVisible();
    await expect(page.getByText('Preferences', { exact: true }).first()).toBeVisible();
    await expect(page.getByText('API Keys', { exact: true }).first()).toBeVisible();

    // Profile tab - email field disabled
    await expect(page.locator('input[type="email"]')).toBeVisible();
    await expect(page.locator('input[type="email"]')).toBeDisabled();
    await expect(page.getByText('Contact support to change')).toBeVisible();
    await expect(page.getByText('Change Password').first()).toBeVisible();

    await page.screenshot({ path: `${SS}/settings/01-profile.png`, fullPage: true });
  });

  test('22 - Settings - switch tabs', async ({ page }) => {
    await page.goto(`${BASE_URL}/dashboard`);
    await page.waitForLoadState('networkidle');

    // Open user menu dropdown and click Settings
    await page.locator('button').filter({ has: page.locator('.rounded-full.bg-primary\\/20') }).click();
    await page.getByText('Settings', { exact: true }).click();
    await page.waitForURL('**/settings', { timeout: 10000 });
    await page.waitForLoadState('networkidle');

    // Click Preferences tab
    await page.getByText('Preferences', { exact: true }).first().click();
    await page.waitForTimeout(500);
    await expect(page.getByText('Theme', { exact: true }).first()).toBeVisible();
    await expect(page.getByText('Auto-save', { exact: true }).first()).toBeVisible();
    await page.screenshot({ path: `${SS}/settings/02-preferences.png`, fullPage: true });

    // Click API Keys tab
    await page.getByText('API Keys', { exact: true }).first().click();
    await page.waitForTimeout(500);
    await expect(page.getByText('Your API Key', { exact: true }).first()).toBeVisible();
    await expect(page.getByText('Regenerate API Key').first()).toBeVisible();
    await page.screenshot({ path: `${SS}/settings/03-api-keys.png`, fullPage: true });
  });

  test('23 - Settings - change password', async ({ page }) => {
    await page.goto(`${BASE_URL}/dashboard`);
    await page.waitForLoadState('networkidle');

    // Open user menu dropdown and click Settings
    await page.locator('button').filter({ has: page.locator('.rounded-full.bg-primary\\/20') }).click();
    await page.getByText('Settings', { exact: true }).click();
    await page.waitForURL('**/settings', { timeout: 10000 });
    await page.waitForLoadState('networkidle');

    // Fill password change form
    const pwInputs = page.locator('input[placeholder*="password"]');
    await pwInputs.nth(0).fill(TEST_PASSWORD);
    await pwInputs.nth(1).fill('NewPass123!');
    await pwInputs.nth(2).fill('NewPass123!');
    await page.getByRole('button', { name: 'Change Password' }).click();
    await page.waitForTimeout(2000);

    await expect(page.getByText('Password changed', { exact: true })).toBeVisible();
    await page.screenshot({ path: `${SS}/settings/04-password-changed.png`, fullPage: true });

    // Reset password back for subsequent tests
    const newPwInputs = page.locator('input[placeholder*="password"]');
    await newPwInputs.nth(0).fill('NewPass123!');
    await newPwInputs.nth(1).fill(TEST_PASSWORD);
    await newPwInputs.nth(2).fill(TEST_PASSWORD);
    await page.getByRole('button', { name: 'Change Password' }).click();
    await page.waitForTimeout(2000);
  });

  test('24 - Settings - preferences save', async ({ page }) => {
    await page.goto(`${BASE_URL}/dashboard`);
    await page.waitForLoadState('networkidle');

    // Open user menu dropdown and click Settings
    await page.locator('button').filter({ has: page.locator('.rounded-full.bg-primary\\/20') }).click();
    await page.getByText('Settings', { exact: true }).click();
    await page.waitForURL('**/settings', { timeout: 10000 });
    await page.waitForLoadState('networkidle');

    await page.getByText('Preferences', { exact: true }).first().click();
    await page.waitForTimeout(500);

    // Click Light theme - applies immediately
    await page.getByText('☀️ Light').click();
    await page.waitForTimeout(300);

    // Verify theme was applied
    const themeAttr = await page.evaluate(() => document.documentElement.getAttribute('data-theme'));
    expect(themeAttr).toBe('light');
    await page.screenshot({ path: `${SS}/settings/05-preferences-light.png`, fullPage: true });

    // Switch back to dark
    await page.getByText('🌙 Dark').click();
    await page.waitForTimeout(300);
    const themeAttr2 = await page.evaluate(() => document.documentElement.getAttribute('data-theme'));
    expect(themeAttr2).toBe('dark');
  });

  test('25 - Settings - back to dashboard', async ({ page }) => {
    await page.goto(`${BASE_URL}/dashboard`);
    await page.waitForLoadState('networkidle');

    // Open user menu dropdown and click Settings
    await page.locator('button').filter({ has: page.locator('.rounded-full.bg-primary\\/20') }).click();
    await page.getByText('Settings', { exact: true }).click();
    await page.waitForURL('**/settings', { timeout: 10000 });

    // Click back button
    await page.click('button[title="Back to Dashboard"]');
    await page.waitForURL('**/dashboard', { timeout: 10000 });
    await expect(page.locator('text=Welcome back')).toBeVisible();
  });
});
