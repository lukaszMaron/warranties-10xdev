# Workspace Notes

- This checkout combines 10xDevs course/toolkit material with a warranties project starter. See the [README](README.md), [product requirements](10xdevs/context/foundation/prd.md), and [tech-stack hand-off](10xdevs/context/foundation/tech-stack.md).
- The root Python package is starter-only: [its source](src/warranties_10xdev/__init__.py) prints a greeting. Product API routes, persistence, tests, and the Astro frontend are not implemented; treat the PRD as intended behavior, not current functionality.
- Verified run command: `uv run warranties-10xdev`. No project test or lint command is configured.
- Product foundation docs live under `10xdevs/context/foundation/`; root `context/` contains bootstrap artifacts. Use supplied paths literally; do not substitute one context root for the other.
- Root `package.json` is not an Astro app; its `uv` dependency is an npm package, not Astral's Python CLI. Check the current tree before assuming a frontend exists.
- Root `pyproject.toml` means `uv init .` will refuse to initialize again. Extend the existing project rather than rerunning the bootstrapper in this directory.
- Treat `context/changes/bootstrap-verification/verification.md` as a record of one run, not proof of the current tree; inspect the files before inferring whether a scaffold exists.
- The PRD excludes reminders from the MVP while the stack hand-off flags background jobs. Clarify scope before implementing scheduled reminders.

<!-- BEGIN @przeprogramowani/10x-cli -->

## 10xDevs AI Toolkit - Module 3, Lesson 4 (E2E Tests)

**For E2E tests, use the two M3L4 skills in this order:**

1. **`/10x-e2e-setup`** — one-time setup: Playwright config (`webServer`,
   auth `setup` project, `storageState`), a green seed test, and `context/foundation/test-stack.md`.
2. **`/10x-e2e`** — the per-risk loop: risk → explore the running app with
   `playwright-cli` → generate → review against the five anti-patterns →
   re-prompt by name → verify with a deliberate break.

The skills' `references/` carry the full rules, anti-patterns, seed pattern, and
prompt-template.

A few hard rules that hold even before you invoke the skill:

- **Locators:** `getByRole` / `getByLabel` / `getByText` first; `getByTestId`
  only when accessibility attributes are ambiguous. Never CSS selectors, XPath,
  or DOM structure.
- **Never `page.waitForTimeout()`.** Wait for state: `toBeVisible()`,
  `waitForURL()`, `waitForResponse()`.
- **Test independence + cleanup.** Each test runs standalone — its own setup,
  action, assertion, and cleanup; unique ids (timestamp suffix) so parallel runs
  and re-runs don't collide.

Two boundaries to keep straight:

- **DOM (snapshot) is the default.** Vision (`--caps=vision`) is a supplement for
  visual-only risks (layout, z-index, animation); for pixel regression prefer
  deterministic tools (`toHaveScreenshot`, Argos, Lost Pixel). VLM model
  selection/cost is a debugging topic (Lesson 5), not testing.
- **A red test is a signal, not a chore.** A changed selector → update the
  locator in a reviewed diff. A changed business behavior → the test caught a
  bug; never edit the assertion to match it. Fixing failing tests is Lesson 5.

<!-- END @przeprogramowani/10x-cli -->

## Purchase-entry UI contract

Use `frontend/src/styles/tokens.css` for semantic design tokens and check `frontend/src/components/ui/` before creating controls. Add missing controls there as local Astro components, and use semantic tokens instead of literal colors or arbitrary values. Review interaction states at `frontend/src/pages/purchases/new-states.astro`.
