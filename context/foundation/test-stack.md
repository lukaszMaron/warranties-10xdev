# Test stack

## E2E

<!-- Written by /10x-e2e-setup. Re-run it to change this section; other skills only read it. -->

- runner: Playwright Test, @playwright/test 1.64.1
- config: frontend/playwright.config.ts
- single-spec command: npx playwright test tests/e2e/seed.spec.ts (from frontend/)
- full-suite command: npx playwright test (from frontend/)
- base URL: http://localhost:4321
- port: 4321 (detected from Astro preview default; detected default 4321, override with E2E_PORT)
- web server command: npm run build && npm run preview -- --port ${PORT} (from frontend/); reuseExistingServer outside CI
- auth setup project: none
- storageState: none
- seed: frontend/tests/e2e/seed.spec.ts — protects #1: PDF import allows correction and preserves corrected values on save
- browser CLI: playwright-cli, command skill at .github/skills/playwright-cli
- updated: 2026-10-17
