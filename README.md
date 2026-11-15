# Parallel AI Development — Tournament Starter & Hackathon MVP Guide

## Demo app — ready

Open **http://127.0.0.1:8787/?run=20261115T074027Z-8525f744** for the current two-candidate comparison.
Both generated Day Planner candidates passed all 13 browser checks. Both hosted previews returned HTTP 200 and both exported patches reconstructed their verified source on clean checkouts.

Start/restart locally with `.venv/bin/python -m tournament.server`. The React build is served by that coordinator; rebuild with `cd ui && npm run build` after frontend changes. Provider keys are read from ignored `.env` on the server.

Use **Open live preview**, **Diff**, **Checks**, then **Select & download patch**. Selection verifies clean patch application and freezes the chosen source hash. **Clean up sandboxes** deletes hosted resources while keeping artifacts. A 15-minute expiry also limits the review window. Do not restart the server during an active generation run.

---

## Day Planner runner — available now

The Python runner supports your standalone `examples/day_planner/Day Planner.html`.
It creates an exact local snapshot, compares two HTML implementations in Daytona,
and exports pages, patches, browser reports, and screenshots. The original page
stays unchanged. No public repository is needed for this workflow.

```bash
python3 -m tournament prepare-day-planner
python3 -m tournament plan task.day-planner.local.json
python3 -m tournament run task.day-planner.local.json --live
```

Install `.[cloud]` and export your provider keys/model ID before the live command.
See [Day Planner setup and review](docs/DAY_PLANNER.md) for prerequisites and outputs.
Hosted previews and the TypeScript comparison UI described below remain future work.

Compare independent implementations of the **same change** before selecting one.
Nosana supplies inference; Daytona isolates code execution; the coordinator captures verification, patches, and cleanup outcomes. Selection remains manual.

**Demo promise:** “Try two implementations before choosing what to ship.”

---

## Part 1: Python Tournament Starter (Current Repo)

### Start here — no keys, no credits

From this folder, using Python 3.10 or later:

```bash
python3 -m unittest discover -s tests -v
python3 -m tournament demo
```

The demo uses two **fixed local fixtures, not AI models**. One implementation passes, one deliberately fails. Its exit code is **1 by design**, because one candidate fails. It exercises actual Git clones, independent test execution, patch export, and cleanup. Check `results/<run-id>/summary.json` and the candidate folders for source, diffs, logs, and results. No application code supplied by a real model runs on your machine; local execution is only for these known fixtures.

### First live run

1. Create a disposable public GitHub repository containing the two files in `examples/calculator/` at its root. Commit and push them, then record its full commit SHA. Its baseline has two expected errors because multiply is missing.
2. Copy `examples/task.example.json` to `task.local.json` and supply the real repository URL and SHA. Review the trusted test command before running it.
3. Install the cloud dependency in a virtual environment:

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   python3 -m pip install -e '.[cloud]'
   ```

4. Copy `.env.example` to `.env` and fill in your local values, or export them in your shell. The runner reads `.env` without executing shell commands; existing environment values take precedence. Never put keys in repository URLs or task files. Then inspect the catalog and choose an available model:

   ```bash
   python3 -m tournament models
   python3 -m tournament plan task.local.json
   python3 -m tournament run task.local.json --live
   ```

   By default `NOSANA_MODEL_ID` is reused for each independent attempt. Alternatively pass `--models 'ACTUAL_ID_A,ACTUAL_ID_B'`, one ID per configured candidate.

`plan` makes no network calls. `run --live` provisions paid sandboxes and sends the request and source to Nosana. There are at most 4 candidates and at most 2 repairs per candidate; defaults are 2 candidates and 1 repair. Commands have server-side execution deadlines. These bounds are **not a provider dollar cap**. There is no automatic retry of inference requests and no dedicated GPU deployment management.

### What works in this starter

- Hosted Nosana catalog/completions adapter; strict JSON source response.
- Daytona v2/standard API adapter, pinned to `2.0.0a12` with its `v0-sdk` extra. Automatic fallback occurs only when the account explicitly reports v2 is not enabled.
- One existing Python source file per attempt; no model-controlled shell commands.
- Same immutable SHA, separate sandbox and model history for each attempt.
- Operator-specified tests, bounded repair, tracked-file integrity checks.
- Persisted sandbox IDs, source hashes, usage when returned, diffs, and test logs.
- Cleanup after success and failure, with a separate cleanup status.
- Offline integration test reconstructing a winning patch and rerunning tests.

**Connection smoke tests verified:** the Nosana model catalog authenticated successfully, and Daytona's standard API created a sandbox, executed Python, and confirmed deletion. This account reports that v2 is not enabled. Full candidate-run results are recorded separately under `results/`; a smoke test alone does not establish working generation and browser acceptance.

### Starter boundaries and next milestones

This starter supports the Python calculator and standalone Day Planner HTML with browser checks, exported pages, and screenshots. There are no persistent hosted previews, comparison UI, follow-up revisions, private repo credentials, or automatic PRs yet.

1. Verify one actual model response and one Daytona lifecycle with your account.
2. Run a two-candidate calculator task; inspect logs and apply the preferred patch to a clean clone at the recorded SHA. No branch is pushed by this runner.
3. Add the bounded read/edit/check tool loop and a trusted web-app sample.
4. Add preview lifecycle, comparison UI, selection freezing, and reproducible export.
5. Add recovery reconciliation, quotas, and GitHub PR export.

Tracked-file hashes detect unexpected on-disk changes; they are not a security boundary against malicious code manipulating the runtime. Only use disposable, reviewed public demo repositories with no external credentials. Sandboxes are deleted immediately after artifact export, so live previews are not retained. If deletion cannot be confirmed, use the saved sandbox ID to check/delete the resource in Daytona. A killed coordinator can bypass cleanup; inspect both provider dashboards after interruptions. No hard wall-clock run deadline or automatic stale resource sweeper is implemented yet. Missing verification remains `not_run`.

---

## Part 2: Hackathon MVP Guide (Web App & Comparison UI Plan)

### Goal

Give two independent AI sessions the same web application and change request. Run each implementation in its own Daytona sandbox, compare working previews and build evidence, and download the preferred implementation as a patch.

This is the working implementation plan. The source guides in `docs/` are reference material; their example commands, account claims, and suggested actions are not evidence that setup has been completed.

### Starting state & context

- Daytona and Nosana live access have not been verified in this session.
- The source playbook reports \$100 Daytona and \$10 Nosana credits. Current balances are unverified.
- An InsForge project is identified in the supplied project instructions, but this MVP does not need a shared database or authentication.

### Scope we are committing to

| Include | Defer |
| --- | --- |
| One known, small React/Vite demo app | Arbitrary repositories and monorepos |
| Two candidates from one exact Git commit | Three/four candidates and model rankings |
| One verified Nosana model, separate histories | Multiple GPU deployments |
| One editable UI source file per candidate | General multi-file coding agents |
| One generation and at most one repair per candidate | Open-ended tool loops and continuation |
| Independent build and acceptance checks | Universal quality or security scores |
| Preview links, diff, captured logs | Guaranteed iframe embedding |
| Select and download a patch | GitHub push, PR creation, or automatic merge |
| Explicit cleanup after review | Multi-user accounts and durable job infrastructure |

Use the second guide for the review experience and the first playbook for the bounded generation approach. Both candidates must execute for real. Report failures as failures.

### Demo application and task

Start with a small task dashboard using local fixture data, task creation, and completion toggles. Keep the editable UI in `src/App.tsx`; use existing styles or inline styles so an implementation can remain within that file. Keep dependencies and verification outside the editable surface.

**Shared change request:**

> Improve the task dashboard layout and add case-insensitive title search plus All, Open, and Done filters. Combine search and status filtering. Show a useful empty state. Preserve task creation and completion. Keep controls usable on mobile. Change only src/App.tsx and use existing dependencies.

Required behavior and checks are identical for both candidates. Use separate model requests with the same source context and budget. Differences are possible, not guaranteed; display the actual model used.

#### Acceptance checks

- Search matches task titles without case sensitivity.
- All, Open, and Done return the correct fixture tasks.
- Search and status filters work together.
- No matching tasks produces an empty state.
- Creating and completing tasks still works.
- The production build succeeds after the final edit.
- Controls work at a narrow viewport during browser review.
- Only the allowed source file changes; verification remains unchanged.

Build results are captured execution. Feature behavior needs a shared browser check or recorded manual observation. A successful build alone does not establish that these requirements passed.

### Minimal architecture

Use TypeScript throughout (or bridge with the local coordinator): a React/Vite comparison UI and a small local coordinator. Keep provider calls behind server-side adapters. Do not introduce an agent framework for this deadline.

```text
Comparison UI → local coordinator
                    ├─ Nosana: two independent generation requests
                    ├─ Daytona A: checkout → edit → build → preview
                    └─ Daytona B: checkout → edit → build → preview
                              ↓
                    saved diffs, logs, run metadata
                              ↓
                    human selection → patch download
```

The coordinator owns credentials, resource lifecycle, source validation, checks, and artifact export. Generated applications receive no provider credentials. No shared database is required; save metadata and artifacts to local files outside the sandboxes.

### Build order: 40-minute target

Times are implementation targets, not guarantees. Measure from the start of implementation.

| Window | Deliverable | Gate |
| --- | --- | --- |
| 0–7 min | Scaffold the known app; verify one Nosana request and one Daytona sandbox | Real model response; baseline app builds; sandbox can execute a command |
| 7–20 min | One complete candidate | Same base SHA checked out; actual generated edit; build log; usable preview; exported patch |
| 20–28 min | Second independent candidate | Separate sandbox and history; same source and task; failure isolation |
| 28–35 min | Comparison UI | Actual statuses, model labels, preview links, diff/log inspection, select and download |
| 35–40 min | Rehearse and fix blockers | Interact with both previews; verify selected patch; clean up after review |

Do not expand parallelism until one candidate works end to end. If provider setup is blocked, expose the actual error and resolve it; do not substitute fake successful output. A recorded run may be shown only when clearly identified.

### Candidate execution contract

1. Save a run ID, exact base SHA, shared task, model ID, and candidate IDs before launching work.
2. Create an isolated sandbox and persist its ID immediately.
3. Load the same demo repository at the exact base SHA. Use a public demo repository or upload a clean, credential-free Git bundle if publishing would delay the demo.
4. Install using the lockfile and the demo app's actual trusted commands.
5. Send the task and bounded source context to Nosana. Request a complete replacement for the one allowed file.
6. Validate the response and write only `src/App.tsx`. The model cannot choose shell commands, paths, packages, or Git operations.
7. Run the trusted build and available acceptance checks. On failure, allow one repair using bounded captured output.
8. Export the final diff, source, logs, and metadata before cleanup. Associate evidence with the final source revision.
9. Start the final app on a fixed port, bind to `0.0.0.0`, poll readiness, and obtain a preview using the installed Daytona SDK's documented permissions.
10. Keep the preview available during review. Freeze the selected revision and serve its already-saved patch.
11. Apply the selected patch to a clean checkout at the base SHA and rerun the build. Record the result.
12. Delete resources after review or the configured review deadline. Record cleanup failures and sandbox IDs for recovery.

Verify the installed Daytona SDK and current official provider documentation before implementing calls. The first playbook's `daytona.v2` syntax and package pin are reference claims, not a verified integration.

### UI and coordinator contract

Keep the repository fixed for this demo. The main input is the change request; display the resolved base SHA.

- `POST /runs`: create a bounded two-candidate run.
- `GET /runs/:id`: poll candidate states and evidence.
- `GET /runs/:id/candidates/:candidateId/artifacts/:name`: retrieve saved diff, logs, or patch.
- `POST /runs/:id/select`: freeze the chosen candidate and return its patch reference.
- `POST /runs/:id/cleanup`: export remaining artifacts and delete sandboxes.

These are our proposed application endpoints. Enforce run/candidate membership and allowlist artifact names rather than accepting arbitrary filesystem paths.

Each candidate card shows:

- Candidate ID and actual model ID.
- State: `queued → provisioning → preparing → generating → verifying → ready`, or `failed` / `cancelled`.
- Separate build, feature-check, preview, export, and cleanup statuses.
- Open-preview link, captured logs, diff, elapsed time, and select/download control.
- A concrete failure message when a stage fails.

Check statuses: `passed`, `failed`, `not_run`, `timed_out`, or `infrastructure_error`. Never convert missing evidence into a pass. Enable selection only when the final artifact is saved and the required checks pass.

Persist at least: run ID, candidate ID, base SHA, task, model ID, sandbox ID, final source hash, timestamps, attempts, token usage when returned, checks and logs, preview expiry, artifact paths, selection, and cleanup result. Label costs as estimates unless reconciled to billing.

### Limits and lifecycle

- Two candidates; one initial generation plus at most one repair each.
- Configure finite model, command, candidate, and review deadlines. Suggested initial candidate deadline: six minutes; review lifetime: fifteen minutes after readiness.
- Set an output-token cap appropriate to the small source file and the actual model. Reject truncated output rather than silently treating it as complete.
- Keep install/build/start commands operator-controlled and run them in the assigned sandbox.
- Store secrets only in ignored server-side environment configuration. Commit placeholders only. Never log keys or upload local environment files.
- Save required artifacts before deleting sandboxes. Use cleanup in failure paths and persist IDs so a restart can reconcile remaining resources.
- Sandbox cleanup and any dedicated Nosana GPU cleanup are separate operations. Verify both when used.
- Limits on attempts and time are not provider-enforced dollar caps.

### Definition of MVP done

- [ ] Two independent Nosana generations run against the same task and exact starting commit.
- [ ] Each candidate has an isolated Daytona workspace.
- [ ] Both successful candidates have interactive previews of their final revisions; failures remain visible.
- [ ] The comparison view shows real captured build results, diffs, and feature-check evidence.
- [ ] A human can select a candidate and download a complete patch.
- [ ] The selected patch applies and builds on a clean base checkout.
- [ ] Artifacts survive sandbox deletion and cleanup results are recorded.
- [ ] The original branch remains unchanged.

### Demo sequence

Show the baseline task dashboard. State the shared change request and base SHA. Launch both candidates and show real progress. Open each preview and exercise search plus filtering. Compare a meaningful tradeoff or failure, inspect the diff/build evidence, select one, and download its patch. Finish by showing saved artifacts and resource cleanup.

### Immediate next step

Scaffold the small demo app and local coordinator, then verify the two provider adapters. Revisit scope only if a concrete integration blocker threatens the end-to-end demo.

---

## References

Original supplied guides are preserved unchanged in `docs/`; their sample code is reference material rather than runtime configuration. Current adapter references:

- [Daytona Python SDK and installation](https://www.daytona.com/docs/python-sdk)
- [Daytona v2 sandbox execution](https://www.daytona.com/docs/python-sdk/sandbox)
- [Nosana hosted inference](https://learn.nosana.com/llm/)


---

## References

Original supplied guides are preserved unchanged in `docs/`; their sample code is reference material rather than runtime configuration. Current adapter references:

- [Daytona Python SDK and installation](https://www.daytona.com/docs/python-sdk)
- [Daytona v2 sandbox execution](https://www.daytona.com/docs/python-sdk/sandbox)
- [Nosana hosted inference](https://learn.nosana.com/llm/)
