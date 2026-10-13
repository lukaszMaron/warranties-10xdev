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

## 10xDevs AI Toolkit - Module 2, Lesson 5

Scale the single-change cycle into parallel work with **worktrees, goal-directed delegation, and multi-session orchestration**:

```
worktree per change -> /goal or your AI coding assistant in headless mode -> PR -> review -> merge
```

The lesson focus is safe throughput: isolated contexts, choosing the right execution mode, and capping parallelism at review capacity.

### Task Router - Where to start

| Skill | Use it when |
| --- | --- |
| **Code isolation** | |
| `git worktree add` | You need a separate working directory for a parallel change. One change per worktree, one fresh agent context per worktree. |
| **Complex changes** | |
| `/10x-implement <change-id> phase <n>` | The change has multiple phases, needs manual gates, or benefits from interactive decision-making during execution. |
| **Simple changes** | |
| `/goal` | You have a clear, bounded task and want goal-directed delegation. The agent works autonomously toward the stated goal with a stop condition. |
| your AI coding assistant in headless mode | You want headless execution for a well-defined task. The Ralph Wiggum loop (run, check, retry) is the universal autonomous pattern. |
| **Multi-session orchestration** | |
| Superset / Conductor / Antigravity / VS Code Agent View | You are running multiple agent sessions in parallel and need visibility, coordination, or session management across them. |

### Parallel work rules

- One change per worktree or isolated workspace. One fresh agent context per change.
- Choose interactive `/10x-implement` for complex changes, `/goal` or your AI coding assistant in headless mode for simple ones.
- Parallelism is capped by review capacity. More agents without review means more unreviewed code, not higher throughput.
- The quality pain from faster shipping is intentional — it bridges into Module 3 testing gates.

### Lesson boundaries

- Do not reteach interactive `/10x-implement` or `/10x-impl-review`; those are Lessons 2 and 3.
- Do not introduce testing strategy here. The quality pain is the motivation for Module 3.
- Worktrees are a mechanism for isolation, not the topic of a full git tutorial.

### Paths used by this lesson

- `context/changes/<change-id>/` - active change folder
- `context/changes/<change-id>/plan.md` - implementation input for any execution mode

Skills must not write to `context/archive/`. Archived changes are immutable; if a resolved target path starts with `context/archive/`, abort with: "This change is archived. Open a new change with `/10x-new` instead."

<!-- END @przeprogramowani/10x-cli -->

## Purchase-entry UI contract

Use `frontend/src/styles/tokens.css` for semantic design tokens and check `frontend/src/components/ui/` before creating controls. Add missing controls there as local Astro components, and use semantic tokens instead of literal colors or arbitrary values. Review interaction states at `frontend/src/pages/purchases/new-states.astro`.
