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

## 10xDevs AI Toolkit - Module 2, Lesson 4

Prepare for a harder implementation stream with the **research-backed planning chain**:

```
internal research (/10x-research) + external research (exa.ai, Context7) -> /10x-plan -> /10x-implement -> success
```

The lesson focus is distinguishing internal from external research and using evidence to back planning decisions.

### Task Router - Where to start

| Skill | Use it when |
| --- | --- |
| **Internal research (lesson focus)** | |
| `/10x-research <change-id>` | You need evidence from the existing codebase — patterns, conventions, integration points, or existing implementations. Runs parallel sub-agents over the repo and writes structured findings to `research.md`. |
| **External research (lesson focus)** | |
| exa.ai | You need AI-native web search for library comparisons, best practices, or ecosystem context that the codebase cannot answer. |
| Context7 (`resolve-library-id` → `get-library-docs`) | You need live, current documentation for a specific library or framework. Resolves a library ID first, then fetches relevant doc pages. |
| **Framing spare wheel** | |
| `/10x-frame <change-id>` | The plan won't converge, the plan doesn't deliver expected results, or persistent drift keeps breaking the implementation. Use as an escape hatch on a separate problem (demonstrated on Space Explorers example), not as pre-research ritual. |
| **Planning and execution** | |
| `/10x-plan <change-id>` / `/10x-implement <change-id> phase <n>` | Use the same planning and execution chain from Lesson 2, now with upstream research evidence feeding the plan. |

### Research discipline

- Internal research (`/10x-research`) answers "what does our codebase already do?" — patterns, schemas, conventions, integration points.
- External research (exa.ai, Context7) answers "what should we do?" — library capabilities, API docs, ecosystem best practices.
- Combine both as evidence-backed input to `/10x-plan`. A plan without research evidence on a non-trivial stream is a guess.
- Agent-friendly docs (`llms.txt`, markdown-for-agents, `/md` endpoints) are a quality signal for library selection — libraries that publish agent-readable docs integrate faster.

### `/10x-frame` as spare wheel

Three triggers for reaching for `/10x-frame`:
1. The plan won't converge — research keeps opening more questions instead of narrowing to a contract.
2. The plan doesn't deliver — implementation repeatedly fails to meet success criteria.
3. Persistent drift — the implementation keeps diverging from the plan in ways that suggest the problem was mis-framed.

Demonstrated on a Space Explorers example, not the SRS path. It is an escape hatch, not a mandatory step.

### Paths used by this lesson

- `context/changes/<change-id>/research.md` - internal research output
- `context/changes/<change-id>/frame.md` - framing output when needed
- `context/changes/<change-id>/plan.md` - evidence-backed implementation contract
- `context/foundation/lessons.md` - recurring rules and pitfalls

Skills must not write to `context/archive/`. Archived changes are immutable; if a resolved target path starts with `context/archive/`, abort with: "This change is archived. Open a new change with `/10x-new` instead."

<!-- END @przeprogramowani/10x-cli -->

## Purchase-entry UI contract

Use `frontend/src/styles/tokens.css` for semantic design tokens and check `frontend/src/components/ui/` before creating controls. Add missing controls there as local Astro components, and use semantic tokens instead of literal colors or arbitrary values. Review interaction states at `frontend/src/pages/purchases/new-states.astro`.
