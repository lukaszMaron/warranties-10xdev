# Purchase Entry UI Contract Implementation Plan

## Overview

Establish a small, dependency-free visual contract for the existing purchase-entry view: shared semantic tokens, local reusable button and field components, and a state-complete visual gate. Preserve the current palette and the manual/PDF purchase behavior, while removing the unsupported step counter and making the save-in-progress state visible on its action.

## Current State Analysis

- The target is the existing Astro page [new.astro](../../../frontend/src/pages/purchases/new.astro), with its markup, imperative state handling, and inline stylesheet in one file. Its page-local `:root` block declares 10 custom properties; the research scan found 41 candidate literals/functions in the view, including the theme-color metadata value ([research](research.md), [new.astro](../../../frontend/src/pages/purchases/new.astro#L344)).
- The view has separate mode, preview, and save button treatments and no shared UI component directory in the inspected `frontend/src` tree ([new.astro](../../../frontend/src/pages/purchases/new.astro#L37), [line 67](../../../frontend/src/pages/purchases/new.astro#L67), [line 120](../../../frontend/src/pages/purchases/new.astro#L120)).
- Existing handlers rely on element IDs, form names, data attributes, and ARIA state for mode switching, OCR suggestions, preview, and save ([new.astro](../../../frontend/src/pages/purchases/new.astro#L209), [line 248](../../../frontend/src/pages/purchases/new.astro#L248), [line 284](../../../frontend/src/pages/purchases/new.astro#L284)).
- `frontend/package.json` provides Astro, TypeScript, and `dev`/`build`/`preview` scripts; the research found no frontend test runner or repository-owned screenshot gate ([package.json](../../../frontend/package.json#L1), [research](research.md)).
- The prior S-02 contract requires preserving both manual entry without a PDF and PDF preview/edit/save ([archived plan](../../archive/2026-10-11-add-purchase-manually/plan.md#L101)).

## Desired End State

The purchase-entry page consumes semantic color, typography, radius, and spacing values from one shared CSS source and uses local Astro Button and Field components. Its current palette and typography remain intact unless a state/contrast check demonstrates a specific problem, in which case any targeted correction is recorded. Manual and PDF behavior stays unchanged; the footer no longer implies a second step, and saving has an explicit accessible busy treatment.

A small, unlinked state-gallery route uses the same tokens and components to show the UI state matrix. Every state is visible there or explicitly marked N/A with a reason, and desktop/mobile screenshots are retained as review evidence. The repository instructions name the token, component, and gallery locations so later UI work can reuse this contract.

### Key Discoveries:

- The current tokens and literal styling are page-local; no shared token or component source exists in the inspected frontend ([research](research.md), [new.astro](../../../frontend/src/pages/purchases/new.astro#L344)).
- Astro supports importing a local stylesheet from component frontmatter and using reusable `.astro` components ([Astro styling guide](https://docs.astro.build/en/guides/styling/#import-a-local-stylesheet), [Astro component props](https://docs.astro.build/en/basics/astro-components/#component-props)). No additional UI dependency is needed.
- The existing page already has status announcements and preview loading/error handling; its form/API contracts are not part of this change ([new.astro](../../../frontend/src/pages/purchases/new.astro#L77), [line 248](../../../frontend/src/pages/purchases/new.astro#L248), [line 269](../../../frontend/src/pages/purchases/new.astro#L269)).
- The roadmap's manual-entry slice uses Change ID `add-purchase-manually` and is already done; the exact lookup found no item keyed by `purchase-entry-ui-contract`, so this plan leaves roadmap status untouched ([roadmap](../../foundation/roadmap.md#L46)). The future purchase overview remains outside scope.
- The scan of the current full page file returned 41 candidates: one `theme-color` metadata value, eight color definitions in `:root`, and 32 other CSS candidates, including panel, field, feedback, and focus styling at [line 384](../../../frontend/src/pages/purchases/new.astro#L384), [line 428](../../../frontend/src/pages/purchases/new.astro#L428), and [line 441](../../../frontend/src/pages/purchases/new.astro#L441). These are scan candidates, not a claim that every hit needs tokenization.

## What We're NOT Doing

- No product-wide rebrand, new palette, component-library dependency, linter, or screenshot-test dependency.
- No purchase-list/dashboard, navigation model, or other view beyond the state-gallery fixture needed for this view's visual gate.
- No changes to the purchase API, storage, manual/PDF workflow, OCR, warranty calculation, or saved-purchase response.
- No backend tests or persistence migration; this plan changes frontend presentation and repository UI guidance only.

## Implementation Approach

Keep the existing Astro/CSS stack. First centralize the current values in a shared semantic stylesheet and record their raw source values in this change folder. Then add only Button and Field components, preserving the DOM contract used by the page's script. Finish with a state gallery and screenshot evidence, and add a concise UI rule outside the CLI-managed block in `.github/copilot-instructions.md`. Use the existing frontend build as the automated integration check; use the integrated browser for the visual gate without adding dependencies.

## Critical Implementation Details

The page script looks up controls by ID and form name, reads `data-draft-field`/`data-warning-for`, and updates `aria-pressed`, `aria-busy`, and live status elements. Button and Field components must emit those existing attributes and elements in the rendered DOM so the manual and PDF flows continue to work without changing their handlers.

## Phase 1: Shared Semantic Tokens

### Overview

Move the current visual values into a shared stylesheet, normalize token names by role, and retain a source record for the values used. This phase adds no library or runtime dependency.

### Changes Required:

#### 1. Token source and provenance

**Files**: `frontend/src/styles/tokens.css`, `context/changes/purchase-entry-ui-contract/design-tokens.md`, `frontend/src/pages/purchases/new.astro`

**Intent**: Give the target view one readable source for its colors, font stacks, radius, and spacing values, preserving the current look while making future state and component styling consistent.

**Contract**: Define semantic custom properties only for values consumed by this view. Import the stylesheet from the Astro page using a relative ESM import in its frontmatter. Record the raw values and their original `new.astro` `:root`/inline-style source in `design-tokens.md`; place a concise source note adjacent to the token block. Do not introduce a second palette or add a package.

### Success Criteria:

#### Automated Verification:

- `npm --prefix frontend run build` completes with the shared stylesheet imported.
- `frontend/src/styles/tokens.css` defines the agreed semantic color, typography, radius, and spacing tokens; `design-tokens.md` records the inherited values and their original source.

#### Manual Verification:

- Compare the token-backed page with the current rendered view and confirm the existing palette and typography are retained; document any targeted contrast correction and its reason.

**Implementation Note**: After this phase's automated checks, pause for human confirmation of the token mapping before proceeding.

## Phase 2: Reusable Controls and Purchase View

### Overview

Create the agreed local Button and Field components, move the purchase-entry page onto them and the shared tokens, and apply the confirmed footer and save-loading decisions without changing purchase behavior.

### Changes Required:

#### 1. Local Button and Field components

**Files**: `frontend/src/components/ui/Button.astro`, `frontend/src/components/ui/Field.astro`

**Intent**: Replace repeated button styling and field-label structure with small, importable Astro components suited to the controls already present on this page.

**Contract**: Button variants cover the mode controls, PDF preview, and save actions and pass through the existing native attributes, including `type`, `id`, `disabled`, `aria-pressed`, and `aria-busy`. Field supports a label, required/optional indication, a control slot, and the existing OCR warning/help target. Keep the PDF drop target as view-specific markup.

#### 2. Refactor the existing entry view

**File**: `frontend/src/pages/purchases/new.astro`

**Intent**: Apply shared tokens and components while preserving the established two-mode form and its result, warning, and status behavior. Remove the unsupported `01 / 02` footer count while retaining the privacy statement; show a stable inline busy affordance on the save button during submission and retain the existing live status message.

**Contract**: Preserve all IDs, form field names, `data-draft-field`, `data-warning-for`, `aria-pressed`, `aria-live`, and preview `aria-busy` values used by the current script. Keep manual save file-optional and keep PDF selection, preview, editable suggestions, and explicit save on the current route. Replace view-local color/style literals with semantic tokens; do not change API requests or response handling.

### Success Criteria:

#### Automated Verification:

- `npm --prefix frontend run build` completes with the imported Astro components and refactored view.
- Re-run the hardcoded-value candidate scan on `new.astro`; it reports only the documented `theme-color` metadata candidate, with view styling supplied by shared tokens.

#### Manual Verification:

- In manual mode, save without a PDF and confirm the effective date/status result still appears; in PDF mode, preview a document, edit a suggested value, save, and confirm the corrected result remains.
- Keyboard navigation exposes a visible focus treatment on each interactive control; disabled and busy controls remain readable, and the save busy affordance does not shift the button layout.
- Capture the refactored view at desktop and one mobile width and compare it with the prior screenshot; investigate unintended palette, spacing, or layout changes.

**Implementation Note**: After this phase's automated checks and browser review, pause for human confirmation before proceeding.

## Phase 3: Seven-State Visual Gate and UI Guard

### Overview

Add a small state-gallery route for review, capture desktop/mobile evidence, and document the shared token/component contract for future agents. The gallery is a QA fixture, not an additional user workflow, and makes no purchase API calls.

### Changes Required:

#### 1. State gallery and screenshot evidence

**Files**: `frontend/src/pages/purchases/new-states.astro`, `context/changes/purchase-entry-ui-contract/screenshots/`

**Intent**: Make the UI skill's required interaction matrix reviewable without introducing a test framework or calling the live purchase API.

**Contract**: Import the shared Button/Field components and token stylesheet; state fixtures must not copy their CSS. Render representative purchase-entry regions together in these states: default, hover, focus-visible, disabled, error, and loading. Mark empty as N/A with the reason that this entry view creates a purchase and does not list saved purchases; do not present a blank frame as an empty-list state. Keep the gallery unlinked from the product flow, make no purchase API calls, and store desktop and one mobile screenshot in the change folder.

#### 2. Project UI rule

**File**: `.github/copilot-instructions.md`

**Intent**: Keep subsequent UI work on the same local contract instead of reintroducing page-specific literals and duplicate controls.

**Contract**: Add a short purchase-entry UI block outside the `<!-- BEGIN @przeprogramowani/10x-cli -->` / `<!-- END @przeprogramowani/10x-cli -->` region. Name `frontend/src/styles/tokens.css`, `frontend/src/components/ui/`, and the state-gallery route. Tell future agents to check that component directory before creating controls, add missing controls as local Astro components, and use semantic tokens rather than literal colors/arbitrary values. Do not edit the CLI-managed block. No linter is added because none is configured in the inspected repository.

### Success Criteria:

#### Automated Verification:

- `npm --prefix frontend run build` completes with the state-gallery route.
- Re-run the same hardcoded-value candidate scan on `new.astro`; the baseline was 41 candidates, including one theme-color metadata value and 40 styling candidates. The view has no remaining inline color values/functions; the metadata value is documented as the one remaining candidate.
- `git diff --check` reports no whitespace errors in the changed files.

#### Manual Verification:

- The gallery shows default, hover, focus-visible, disabled, error, and loading states; the empty state is explicitly marked N/A with its reason. All controls have accessible names, and error/loading states remain understandable without color alone.
- Capture the gallery at desktop and one mobile width, inspect for clipping/overlap, and retain both screenshots under the change folder.
- Confirm the UI rule is outside the CLI-managed block and accurately names the token source, component directory, and gallery route.

**Implementation Note**: After the screenshots, automated checks, and UI-rule review, pause for human confirmation before declaring the visual change ready for implementation review.

## Testing Strategy

### Unit Tests:

- No frontend unit-test runner exists in the inspected repository, and this change adds no new domain logic. Do not add a test dependency for this UI contract.

### Integration Tests:

- Use `npm --prefix frontend run build` to verify Astro page/component/style integration.
- Exercise the existing manual and PDF flows in the browser; no API or backend changes are planned.

### Manual Testing Steps:

1. Open `/purchases/new`, confirm the refactored default view, switch between manual and PDF modes, and verify the footer no longer presents a nonexistent second step.
2. Save a manual purchase without a PDF and confirm the result; then preview a PDF, edit one suggested value, save, and confirm the corrected value and result remain.
3. Exercise disabled, preview/save loading, success, and error feedback, plus keyboard focus on each control.
4. Open the state-gallery route, verify all required state samples and the empty N/A reason, then capture desktop and mobile screenshots.

## Performance Considerations

The plan adds no UI library, runtime package, API call, or data operation. The new local components and token stylesheet are build-time Astro/CSS structure; the save busy indicator reuses the existing submission state.

## Migration Notes

No data or API migration is required. Existing purchase records and PDF handling are outside the scope of this frontend-only change.

## References

- Active scope and decisions: [change.md](change.md)
- Codebase audit and source-backed findings: [research.md](research.md)
- Prior manual/PDF behavior contract: [archived S-02 plan](../../archive/2026-10-11-add-purchase-manually/plan.md#L101)
- Existing purchase view: [new.astro](../../../frontend/src/pages/purchases/new.astro)
- Astro local stylesheet import guidance: https://docs.astro.build/en/guides/styling/#import-a-local-stylesheet
- Astro component props guidance: https://docs.astro.build/en/basics/astro-components/#component-props

## Progress

> Convention: `- [ ]` pending, `- [x]` done. Append ` — <commit sha>` when a step lands. Do not rename step titles. See `references/progress-format.md`.

### Phase 1: Shared Semantic Tokens

#### Automated

- [x] 1.1 `npm --prefix frontend run build` completes with the shared stylesheet imported. — e533b9b
- [x] 1.2 `tokens.css` contains the agreed semantic color, typography, radius, and spacing tokens, and `design-tokens.md` records inherited values and their source. — e533b9b

#### Manual

- [x] 1.3 Confirm the token-backed view retains the current palette and typography, documenting any contrast-driven correction. — e533b9b

### Phase 2: Reusable Controls and Purchase View

#### Automated

- [x] 2.1 `npm --prefix frontend run build` completes with the Astro components and refactored view. — 16511a0
- [x] 2.2 The post-refactor candidate scan on `new.astro` reports only the documented `theme-color` metadata candidate. — 16511a0

#### Manual

- [x] 2.3 Confirm manual no-PDF save and PDF preview/edit/save behavior still work in the browser. — 16511a0
- [x] 2.4 Confirm focus, disabled, and save-busy states are accessible, readable, and layout-stable. — 16511a0
- [x] 2.5 Capture the refactored view at desktop and one mobile width and compare it with the prior screenshot. — 16511a0

### Phase 3: Seven-State Visual Gate and UI Guard

#### Automated

- [x] 3.1 `npm --prefix frontend run build` completes with the state-gallery route.
- [x] 3.2 The hardcoded-value scan reports only the documented theme-color metadata candidate, and `git diff --check` is clean.

#### Manual

- [ ] 3.3 Confirm all seven matrix states are shown or marked N/A with a reason, and all controls have accessible names with error/loading states not conveyed by color alone.
- [ ] 3.4 Capture and inspect desktop and mobile gallery screenshots, and verify the UI rule is outside the CLI-managed block and names the current token/component/gallery paths.
