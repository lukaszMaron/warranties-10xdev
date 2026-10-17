import { existsSync, mkdtempSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { defineConfig, devices } from '@playwright/test';

const frontendDir = dirname(fileURLToPath(import.meta.url));
const repositoryRoot = resolve(frontendDir, '..');
const envFile = resolve(frontendDir, '.env.local');

if (existsSync(envFile)) process.loadEnvFile(envFile);

const PORT = Number(process.env.E2E_PORT ?? 4321);
if (!Number.isInteger(PORT) || PORT < 1 || PORT > 65_535) {
  throw new Error('E2E_PORT must be an integer between 1 and 65535.');
}

const API_PORT = 8000;
const baseURL = `http://localhost:${PORT}`;
const profileDirectory = process.env.E2E_PROFILE_DIR
  ?? mkdtempSync(join(tmpdir(), 'warranties-10xdev-e2e-'));
process.env.E2E_PROFILE_DIR = profileDirectory;

export default defineConfig({
  metadata: {
    e2eProfileDirectory: profileDirectory,
  },
  testDir: './tests/e2e',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: 'html',
  globalTeardown: './tests/e2e/global-teardown.ts',
  use: {
    baseURL,
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
  webServer: [
    {
      command: `npm run build && npm run preview -- --port ${PORT}`,
      cwd: frontendDir,
      url: `${baseURL}/purchases/new`,
      reuseExistingServer: !process.env.CI,
      timeout: 180_000,
      env: {
        ASTRO_PREVIEW_BACKGROUND: '1',
        API_ORIGIN: `http://127.0.0.1:${API_PORT}`,
        PUBLIC_API_BASE_URL: '',
      },
    },
    {
      command: `uv run uvicorn warranties_10xdev.api:app --host 127.0.0.1 --port ${API_PORT}`,
      cwd: repositoryRoot,
      url: `http://127.0.0.1:${API_PORT}/openapi.json`,
      reuseExistingServer: false,
      timeout: 180_000,
      env: {
        WARRANTIES_DATA_DIR: profileDirectory,
      },
    },
  ],
});
