---
starter_id: fastapi
package_manager: uv
project_name: warranties-10xdev
hints:
  language_family: multi
  team_size: solo
  deployment_target: self-host
  ci_provider: github-actions
  ci_default_flow: manual-promotion
  bootstrapper_confidence: first-class
  path_taken: custom
  quality_override: false
  self_check_answers:
    typed: true
    from_official_starter: false
    conventions: false
    docs_current: false
    can_judge_agent: true
  has_auth: false
  has_payments: false
  has_realtime: false
  has_ai: false
  has_background_jobs: true
---

## Why this stack

FastAPI is the registered Python API starter and passes the four agent-friendly gates; its card prescribes uv, self-host deployment, and first-class bootstrapper support. This hand-off scaffolds only the Python backend. The requested Astro/TypeScript frontend and cross-service integration remain manual, so the combined architecture is best-effort. PDF storage and OCR need an explicit implementation, and reminders were selected for the MVP even though the current PRD excludes them; reconcile that scope before bootstrapping.
