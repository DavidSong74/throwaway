# Starter decisions

## Day Planner adaptation

- Live account validation returned v2 `FEATURE_NOT_ENABLED`; support the standard
  API through the pinned SDK's `v0-sdk` extra. Fall back only on this explicit
  response, never on authentication errors or ambiguous provisioning timeouts.
- Read known provider settings from ignored `.env` without shell execution; exported
  values take precedence. Credentials are never copied into the candidate sandbox.

- Support one standalone `.html` file as well as the Python calculator prototype.
- Snapshot the local HTML in a separate explicit Git repository and upload an
  exact-commit bundle, avoiding a public GitHub prerequisite.
- Use coordinator-owned browser checks outside the candidate repository. Verify
  baseline regressions before inference, then new controls and existing behavior.
- Export HTML, reports, desktop/mobile screenshots, and patches before cleanup.
  No persistent cloud preview or automatic winner promotion is implemented.

- Scope: Daytona + Nosana parallel development only. Earlier tourism research is
  unrelated to this project.
- Python coordinator follows the supplied playbook's first-run implementation.
  Framework adoption and the multi-file agent loop follow evidence from one live run.
- Default workflow requires no account setup: deterministic offline fixtures make
  the verification and artifact pipeline inspectable immediately.
- Cloud code uses hosted Nosana inference, not a new rented GPU deployment. Model
  names come from the live catalog rather than a fabricated default.
- The source guides reference multiple SDK generations. The current Daytona v2
  docs specify `daytona==2.0.0a12`; pin this instead of mixing v0/v2 calls.
- No new database or shared backend is needed for this local CLI stage. Run records
  are local JSON files; provider secrets stay in the coordinator environment.
- No global winner score. Independent verification establishes eligibility, and a
  person decides whether the implementation is appropriate.
- Never automatically push or merge generated code. Preserve reviewable artifacts
  before removing execution environments.
