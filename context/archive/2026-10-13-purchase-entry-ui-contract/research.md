---
date: 2026-10-13T20:06:53+02:00
researcher: GitHub Copilot
git_commit: 272cc86c807dfbdca2fc013587de2b919985afe7
branch: develop
repository: warranties-10xdev
topic: "Design-system audit of the purchase-entry view"
tags: [research, codebase, frontend, astro, ui-contract]
status: complete
last_updated: 2026-10-13
last_updated_by: GitHub Copilot
last_updated_note: "Rechecked active change scope; no findings superseded."
---

# Research: Purchase entry page design-system contract

- **Date**: 2026-10-13T20:06:53+02:00
- **Researcher**: GitHub Copilot
- **Git Commit**: 272cc86c807dfbdca2fc013587de2b919985afe7
- **Branch**: develop
- **Repository**: warranties-10xdev

## Research Question

For `purchase-entry-ui-contract`, what design-system gaps, reusable-component boundaries, current interaction states, and repository constraints should inform planning for the purchase-entry view?

## Summary

On this checkout, the purchase-entry page renders and supports both manual and PDF-assisted entry, but its visual contract is page-local. The inspected `frontend/src` tree contains `lib` and `pages`; searches for a components directory and standalone CSS files returned no matches. The page declares 10 custom properties and has 36 `var()` references in its inline stylesheet. A run of the UI skill's candidate expression against the full page returned 41 hits: one theme-color metadata value, eight color values in `:root`, and 32 other candidate values/functions in the view.

The evidence supports a small, plain-CSS contract rather than adopting a component-library dependency: move role-named values into a shared token source and extract only the controls needed by this view. Preserve the existing manual/PDF behavior. Reusable-component boundaries and token names remain planning decisions. Navigation to a future purchases list is deferred because the inspected frontend currently contains no list view.

## Detailed Findings

### Tokens and styling

- The `:root` block in [new.astro](../../../frontend/src/pages/purchases/new.astro#L344) defines 10 custom properties: eight colors and two font stacks. A local source scan counted 36 `var()` references in this page. These values have no consumer outside the view in the inspected `frontend/src` tree.
- The scan of the current full page file returned 41 candidates. Nine are the `theme-color` value at line 17 and eight color definitions in `:root`; the remaining 32 are candidate values/functions in the inline rules, including panel, field, feedback, and focus styling at [line 384](../../../frontend/src/pages/purchases/new.astro#L384), [line 428](../../../frontend/src/pages/purchases/new.astro#L428), and [line 441](../../../frontend/src/pages/purchases/new.astro#L441). These are scan candidates, not a claim that every hit needs tokenization.
- Token names mix roles (`--ink`, `--muted`, `--line`, `--paper`) with color descriptions (`--forest`, `--forest-dark`, `--coral`). Literal values also remain outside `:root`; consequently a palette or contrast change must account for both custom properties and those declarations.
- The styling is plain CSS in the Astro page. `frontend/package.json` declares Astro and TypeScript, with `dev`, `build`, and `preview` scripts; it does not declare a UI component library or frontend test script ([package.json](../../../frontend/package.json#L1)).

### Components and interaction states

- The inspected page renders three button treatments: mode buttons, PDF preview, and purchase save ([new.astro](../../../frontend/src/pages/purchases/new.astro#L37), [line 67](../../../frontend/src/pages/purchases/new.astro#L67), [line 120](../../../frontend/src/pages/purchases/new.astro#L120)). Their styles are separate selectors in the same file. No reusable button or field component was found in the inspected `frontend/src` tree.
- The mode buttons use `aria-pressed`; switching modes hides the upload panel and changes the layout class. The same form remains in use for both modes ([new.astro](../../../frontend/src/pages/purchases/new.astro#L212)). The archived S-02 plan requires retaining manual entry without a PDF and the PDF preview/edit/save flow ([plan.md](../../archive/2026-10-11-add-purchase-manually/plan.md#L101)).
- During PDF preview, the handler disables the preview control, sets `aria-busy`, applies `.is-pending`, and updates a live status message; it also exposes success and error messages ([new.astro](../../../frontend/src/pages/purchases/new.astro#L248), [line 266](../../../frontend/src/pages/purchases/new.astro#L266), [line 269](../../../frontend/src/pages/purchases/new.astro#L269)). During save, the handler disables save via `isSaving` and writes a pending status message; the inspected handler does not add a save-specific pending class ([line 284](../../../frontend/src/pages/purchases/new.astro#L284), [line 288](../../../frontend/src/pages/purchases/new.astro#L288)).
- Form controls receive a green border and translucent box-shadow on `:focus`; the file also sets `outline: none` on inputs/selects and declares a global coral `:focus-visible` outline ([new.astro](../../../frontend/src/pages/purchases/new.astro#L428), [line 429](../../../frontend/src/pages/purchases/new.astro#L429), [line 441](../../../frontend/src/pages/purchases/new.astro#L441)). The interaction review should compare keyboard focus across fields and buttons rather than assume these two treatments are equivalent.
- Preview/save messages use `role="status"` and `aria-live="polite"`; OCR warnings have field-associated elements ([new.astro](../../../frontend/src/pages/purchases/new.astro#L77), [line 92](../../../frontend/src/pages/purchases/new.astro#L92), [line 126](../../../frontend/src/pages/purchases/new.astro#L126)). The current state handling therefore has useful semantics to preserve when styling or extracting components.

### Navigation and scope

- The brand link targets `/purchases/new`, and the adjacent “Mój profil” label is a non-link in the inspected markup ([new.astro](../../../frontend/src/pages/purchases/new.astro#L27), [line 28](../../../frontend/src/pages/purchases/new.astro#L28)). A search of `frontend/src` found one page file, `purchases/new.astro`; the inspected view has no in-app link to a purchases overview.
- The active roadmap lists purchase search (S-03) as proposed and the expiring-warranties dashboard (S-06) as blocked; those future views may determine the eventual shared navigation contract ([roadmap.md](../../foundation/roadmap.md#L47), [line 50](../../foundation/roadmap.md#L50)). Adding a list/dashboard is outside this one-view audit and should remain deferred.

### Tooling and project rules

- In the inspected `frontend/package.json`, the scripts are `dev`, `build`, and `preview`; searches under `frontend/` found no matching frontend test files or Playwright/Vitest/Jest/Cypress configuration files. No repository-owned screenshot gate was found in that scope. The integrated browser was used to confirm the default PDF mode renders at `/purchases/new`; that visual check did not exercise all seven states.
- The inspected `.github/copilot-instructions.md` directs rendered-view UI work to `/10x-ui`, but does not identify a project token file, component directory, or screenshot artifact location ([copilot-instructions.md](../../../.github/copilot-instructions.md#L14)). The existing UI skill defines the 7-state matrix and screenshot gate ([SKILL.md](../../../.github/skills/10x-ui/SKILL.md#L176), [line 199](../../../.github/skills/10x-ui/SKILL.md#L199)); a project-specific rule and gate location remain to be planned.

## Code References

- [frontend/src/pages/purchases/new.astro](../../../frontend/src/pages/purchases/new.astro#L344) — page-local tokens, view markup, interaction logic, and inline styles.
- [frontend/src/lib/api.ts](../../../frontend/src/lib/api.ts#L1) — typed preview and saved-purchase contracts consumed by the view.
- [frontend/package.json](../../../frontend/package.json#L1) — current frontend scripts and dependencies.
- [context/foundation/roadmap.md](../../foundation/roadmap.md#L47) — S-03 proposed; [S-06 at line 50](../../foundation/roadmap.md#L50) is blocked.
- [context/archive/2026-10-11-add-purchase-manually/plan.md](../../archive/2026-10-11-add-purchase-manually/plan.md#L101) — existing manual/PDF flow contract.

## Architecture Insights

The view currently owns its markup, DOM-based state, and CSS while importing only the API helpers/types. The existing feature boundary is useful: the UI can adopt shared tokens and local Astro/CSS primitives without changing the purchase API contract. The current package evidence does not justify adding a design-system dependency. A planning pass should decide which few primitives merit extraction and how to name semantic roles; it should not expand this visual change into a new purchases-list view.

## Historical Context (from prior changes)

The archived S-02 plan's cited UI contract defines the two entry modes, required fields, and saved warranty result; that functional contract is still present in the current page and should be preserved ([plan.md](../../archive/2026-10-11-add-purchase-manually/plan.md#L101)). That passage specifies workflow behavior, not shared token or component locations. The current roadmap leaves S-03 proposed and S-06 blocked ([roadmap.md](../../foundation/roadmap.md#L47), [line 50](../../foundation/roadmap.md#L50)), so the missing purchases overview is a separate scope decision rather than a requirement to add navigation in this view.

## Related Research

No related research artifact was found in the active `purchase-entry-ui-contract` folder at research start. This report is the first research artifact for that change.

## Open Questions

- Should the page-local values become a shared `frontend/src/styles/` token source, and which names should describe roles rather than colors?
- Which controls should become reusable Astro/CSS components for this view, versus remain view-specific?
- Should the existing `01 / 02` footer indicator remain when no second step is represented in the inspected frontend?
- Where should the project-specific UI rule and visual gate live? Frontend test/screenshot infrastructure was not found in the inspected `frontend/` scope, and the UI skill's kitchen-sink page is one documented option.

## Follow-up (2026-10-13)

- **Scope check:** The current `change.md` still targets `frontend/src/pages/purchases/new.astro` and its page-local `:root` token source; no new question or scope change was present.
- **Disposition:** No previous finding was superseded. The existing open decisions remain for `/10x-plan`.
- **Validation:** The current worktree shows no frontend source files modified. No build or test was run because this follow-up introduced no implementation change or new behavior question.
