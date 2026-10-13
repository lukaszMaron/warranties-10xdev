# Purchase Entry UI Contract — Plan Brief

> Full plan: `context/changes/purchase-entry-ui-contract/plan.md`
> Research: `context/changes/purchase-entry-ui-contract/research.md`

## What & Why

Create a small visual contract for the purchase-entry view so its colors, type, spacing, controls, and interaction states stop drifting in one page-local stylesheet. Preserve the existing manual and PDF workflows while making the UI easier to refine and review consistently.

## Starting Point

The rendered Astro page owns its CSS, DOM state, and markup; it has page-local custom properties plus additional literal values, and there are no shared UI components or frontend screenshot tests in the inspected source tree. The existing page already supports manual entry, PDF preview/edit/save, status announcements, and a warranty result, so the plan changes presentation structure rather than the purchase API.

## Desired End State

The view uses shared semantic CSS tokens and local Button/Field components, keeps its current palette and typography, and gives the save action a visible accessible busy state. A state-gallery route documents all seven UI states, with empty marked N/A because the entry view does not list purchases; desktop/mobile screenshots provide the visual gate.

## Key Decisions Made

| Decision | Choice | Why | Source |
| --- | --- | --- | --- |
| Palette | Preserve current values; adjust only for a demonstrated state/contrast issue | Keeps the existing rendered identity while moving values behind semantic roles | Plan |
| Token coverage | Colors, typography, radius, and spacing used by this view | Centralizes the visual primitives this page already uses | Plan |
| Components | Local Button and Field components; keep PDF drop target view-specific | Covers repeated controls without adding a component-library dependency | Plan |
| Footer | Remove `01 / 02`, retain the privacy note | No second screen exists in the inspected frontend | Research / Plan |
| Save loading | Add stable inline busy treatment and `aria-busy`, retaining the live status message | Makes the in-progress action itself visible and accessible | Plan |
| Visual gate | State-gallery route plus desktop/mobile screenshots; no test dependency | No repository frontend screenshot runner exists | Research / Plan |

## Scope

**In scope:** Shared token/provenance files, Button and Field components, refactor of the existing purchase-entry page, footer correction, save-busy state, seven-state gallery, screenshots, and a project UI rule outside the CLI-managed instructions block.

**Out of scope:** New palette direction or product-wide restyle, component library, lint/test dependency, purchase list/navigation, backend/API changes, and changes to manual/PDF purchase behavior.

## Architecture / Approach

Keep Astro and plain CSS. Import the shared token stylesheet from the page, refactor the current controls into local Astro components without changing their DOM contracts, and compose the state gallery from those shared controls without calling the purchase API. Record token provenance in the change folder and document the paths/rules in `.github/copilot-instructions.md` outside the generated CLI block.

## Phases at a Glance

| Phase | What it delivers | Key risk |
| --- | --- | --- |
| 1. Shared semantic tokens | Role-based values, source-value record, and stylesheet import | Literal values outside the original `:root` block could be missed |
| 2. Reusable controls and purchase view | Button/Field components, token-backed page, corrected footer, save busy state | Refactor could break DOM hooks used by the imperative handlers |
| 3. Seven-state gate and UI guard | State gallery, desktop/mobile screenshots, and durable repo instruction | Gallery may drift from the production view if it duplicates styling |

- **Prerequisites:** The existing Astro frontend and purchase-entry route; no new package or backend work.
- **Estimated effort:** Approximately 2–3 implementation sessions across three phases, including human visual review.

## Open Risks & Assumptions

- The state gallery is unlinked from the product flow but remains a route; review its build output before any future public deployment.
- Existing color values are retained unless a specific state/contrast check shows a problem; any exception should be recorded with its reason and provenance.
- Empty-state N/A is specific to this purchase-entry view; a future purchase-list view will need its own empty-state design.

## Success Criteria (Summary)

- Manual and PDF entry continue to work with the existing fields and result behavior.
- The view uses semantic tokens and the agreed local components; the scan leaves no inline color candidates except the documented theme-color metadata value.
- The seven-state gallery, empty-state rationale, accessible control states, desktop/mobile screenshots, and UI rule are all reviewed.
