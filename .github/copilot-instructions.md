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

## 10xDevs AI Toolkit - Module 2, Lesson 3

Review AI-generated code before merge with the **implementation review chain**:

```
/10x-implement -> /10x-impl-review -> triage -> (/10x-lesson | fix | skip | disagree)
```

`/10x-impl-review` is the lesson focus. Review is a quality gate, not an instruction to fix every finding.

### Task Router - Where to start

| Skill | Use it when |
| --- | --- |
| **Code review (lesson focus)** | |
| `/10x-impl-review <change-id>` | You have implemented code and want a structured review before merge. The skill checks plan adherence, scope discipline, safety and quality, architecture, pattern consistency, and success criteria, then presents findings for triage. |
| **Recurring lesson outcome** | |
| `/10x-lesson` | A finding reveals a recurring project rule or agent failure pattern. Record it in `context/foundation/lessons.md` instead of treating it as a one-off note. |

### Triage discipline

- Severity says how bad the finding is. Impact says how much the decision matters now.
- Valid outcomes: fix now, fix differently, skip, accept as risk, record as recurring rule (`/10x-lesson`), disagree.
- Fix critical findings. Do not burn hours on low-impact observations just because the agent found them.
- Conscious skipping of low-impact findings is a valid review outcome, not negligence.
- If you disagree with a finding, record why. Wrong agent reasoning is also signal.

### Review boundaries

- This lesson reviews implemented code. It does not create the plan, execute new phases, or teach CI review.
- Testing strategy and quality gates are introduced in Module 3.
- Do not use `/10x-contract` as a triage outcome in this lesson.

### Paths used by this lesson

- `context/changes/<change-id>/plan.md` - expected implementation contract
- `context/changes/<change-id>/reviews/` - review output
- `context/foundation/lessons.md` - recurring lessons

Skills must not write to `context/archive/`. Archived changes are immutable; if a resolved target path starts with `context/archive/`, abort with: "This change is archived. Open a new change with `/10x-new` instead."

<!-- END @przeprogramowani/10x-cli -->
