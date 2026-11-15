# Parallel AI — Technical Pitch & Demo Notes

## The project in three sentences

Parallel AI lets developers compare two AI-generated implementations of the same change before deciding what to ship. Nosana runs the model inference, and Daytona provides separate environments to execute, test, and preview each implementation. Our React dashboard brings together live previews, captured checks, screenshots, and code differences so the developer can choose a version and download its patch.

## Three-minute talk track

### 0:00–0:30 — The problem

“When an AI gives you a working implementation, you still have a decision to make: is this the implementation you actually want? Another approach might have a clearer interface or handle your requirements differently. Trying those alternatives manually means repeating the setup, execution, and review process.

We built Parallel AI to make that comparison easier.”

### 0:30–1:00 — What we built

“You provide an existing application and a change request. We start two independent coding sessions from the exact same source version, run their implementations separately, and bring the results into one comparison screen.

You can open the live applications, inspect their checks and code changes, and choose the version you want to keep. The developer makes the final decision.”

### 1:00–1:40 — How the technology works

“Nosana supplies the model inference. In this demo, both independent sessions use Qwen3.8-27B; these are two attempts with the same model, rather than two different models.

Daytona supplies a separate sandbox for each attempt. Our Python coordinator transfers the same Git snapshot into both sandboxes, requests the code changes, and runs our Playwright browser checks independently of the model's claims.

After verification, we start a web server inside each successful sandbox and create an expiring, port-specific signed preview URL. The React interface shows those links alongside screenshots, diffs, and captured results.”

### 1:40–2:30 — Demonstrate the result

“Here is our original Day Planner. The shared request was to add task-title search and All, Open, and Done filters, while preserving the existing scheduling and task-management features.

These are the two generated implementations. Both passed all 13 browser checks after the bounded repair process. I can open each live preview and compare the experience directly.

The checks include whether filtering changes the schedule—it should only change what you see, not when your tasks start. We also test task creation, completion, persistence, and mobile layout.

When I choose a version, the coordinator checks that its patch applies to a clean copy of the original and reproduces the verified source before offering the download.”

### 2:30–3:00 — Why it matters and what comes next

“The contribution is the coordination and review workflow: independent implementations, real execution evidence, and recoverable changes in one place.

Our working prototype supports a standalone HTML application. Next, we want to extend the editing and verification workflow to multi-file applications and add GitHub pull-request export.

The goal is simple: explore alternatives, inspect the evidence, and choose what ships.”

## Architecture: explain this diagram

```text
                     Developer
               application + change request
                         |
              React comparison dashboard
                         |
               Local Python coordinator
                  /               \
      Independent session A   Independent session B
               |                      |
        Nosana inference       Nosana inference
        Qwen3.8-27B            Qwen3.8-27B
               |                      |
        Daytona sandbox A      Daytona sandbox B
        same starting SHA      same starting SHA
        write HTML             write HTML
        browser checks         browser checks
        bounded repair         bounded repair
        preview server         preview server
                  \               /
           Saved source, patches, logs, screenshots
                         |
           Human comparison and selection
                         |
           Clean patch-application verification
                         |
                Download selected patch
```

**The model proposes the implementation. The coordinator executes and verifies it. The person chooses what to keep.**

## Partner technologies and their actual roles

- **Nosana:** OpenAI-compatible hosted inference. We discover available models through its catalog and call its chat-completions endpoint. No dedicated GPU deployment is required for this integration.
- **Qwen3.8-27B:** The model used by both independent sessions in the demonstrated run. The coordinator requests non-thinking mode for Qwen to reduce generation latency.
- **Daytona:** Separate sandbox filesystems, command execution, browser-test execution, managed preview-server sessions, signed preview URLs, and resource deletion.
- **Python:** Coordinator, provider adapters, configuration loading, run records, and a local HTTP API built with the standard library.
- **React + Vite:** The comparison interface and frontend build. The Python server serves the built frontend.
- **Playwright + Chromium:** Browser-based regression and acceptance checks, plus desktop/mobile screenshots. They run inside Daytona for real generated candidates.
- **Git:** Exact starting commits, transferable baseline bundles, code differences, and patch reconstruction.

**Useful distinction:** Nosana provides inference and Daytona provides execution. Our code supplies the workflow connecting them; neither service automatically creates this comparison product by itself.

## What happens during one run

1. **Create a baseline.** Copy the standalone HTML input into its own minimal Git repository and record the exact commit SHA. The original file is unchanged.
2. **Transfer identical input.** Package that commit as a Git bundle and clone it inside each candidate's sandbox.
3. **Check the baseline.** Verify existing behavior before asking the model to change anything. This helps distinguish environment/test problems from generated-code failures.
4. **Generate the implementation.** Send the request and source to Nosana. Each candidate has its own conversation history. The model returns a JSON object containing replacement source; it does not choose shell commands or edit paths.
5. **Validate and execute.** Reject malformed responses and incomplete HTML, write only the allowed target file, then run the coordinator-owned browser verifier.
6. **Allow a bounded repair.** If verification fails, return the captured error output to that session for one repair attempt in the default configuration.
7. **Capture evidence.** Save the final source, its SHA-256 hash, patch, check report, screenshots, and attempt logs outside the disposable sandbox. Check that tracked files outside the allowed target did not change.
8. **Provide a hosted preview.** Run a Python HTTP server on port 8080 inside Daytona, check readiness, and obtain a signed preview URL for that port.
9. **Review and select.** The dashboard polls progress every two seconds. Selection requires passing verification and a saved patch.
10. **Reconstruct and export.** Apply the selected patch to a clean checkout at the baseline SHA and compare its source hash with the verified candidate. Record the selection and provide the patch download.
11. **Clean up.** Explicit cleanup removes sandboxes while retaining artifacts. Preview links and review timers use a 15-minute window; the local coordinator also checks for expired review records while running.

## Verified demo evidence

Demonstrated run: `20261115T074027Z-8525f744`.

- Two real Nosana-generated Day Planner implementations, using `qwen/qwen3.8-27b`.
- Both candidates passed **13/13 browser checks** after their repair attempts.
- Both hosted preview URLs returned **HTTP 200** when checked.
- Both patches applied to clean baseline checkouts and reproduced their verified source hashes.
- The React screen rendered two candidate cards at desktop and mobile widths without JavaScript errors in a Chromium test using a captured API snapshot.
- A separate local API fixture tested selection, patch download, repeated selection, the cleanup response, and cross-origin rejection.

These are results from this particular task and run. They are not evidence that every requested change will pass, that the platform is production-ready, or that it universally improves development speed.

### The 13 browser checks

1. Page startup.
2. Task creation and priority ordering.
3. Fixed start times and break settings.
4. Completion, undo, and deletion.
5. Persistence across reload.
6. Invalid day settings.
7. Clear-all confirmation.
8. Mobile layout at 390px width.
9. Case-insensitive title search.
10. Combined search and status filtering.
11. No-matches feedback.
12. Unchanged scheduling when filtering.
13. Filters continuing to work after rerender and reload.

## API details for a technical audience

The local coordinator listens on `127.0.0.1:8787`. The React frontend uses these routes:

- `GET /api/config` — Default task, target, and model name; no provider keys.
- `POST /api/runs` — Snapshot the input and launch two background candidate workers.
- `GET /api/runs` — List recorded runs and current candidate states.
- `GET /api/runs/:id` — Read one run's state, artifacts, and selection.
- `GET /api/runs/:id/candidates/:candidate/artifacts/:name` — Retrieve an allowlisted artifact.
- `POST /api/runs/:id/select` — Verify patch reconstruction, record the selected source hash, and return a download link.
- `POST /api/runs/:id/cleanup` — Delete run sandboxes and record cleanup outcomes.

Run records and artifacts are stored locally under `results/<run-id>/`. This prototype uses threads and JSON files, not a distributed queue or production database.

## Demo click sequence

1. Open the comparison dashboard: `http://127.0.0.1:8787/?run=20261115T074027Z-8525f744`.
2. Explain the common request and the shared baseline SHA.
3. Open each **Live Preview**. Add a task, search for it, and change the status filter.
4. Return to the dashboard and open **Checks** and **Diff**.
5. Choose a candidate yourself and click **Select & download patch**. Explain the clean-checkout verification.
6. Click **Clean up sandboxes** after showing the previews.

The original page is served separately at `http://127.0.0.1:8001/Day%20Planner.html` while that local server is running. Hosted preview links expire; use a fresh run if the old links are no longer available. If showing a completed run, introduce it as a completed run rather than live generation.

## Likely audience questions

### “Why use two sessions of the same model?”

We are comparing implementation attempts, not claiming to rank different models. Separate histories and workspaces let us inspect alternatives under the same initial requirements. Different models can be added later when the endpoint serves suitable ones. Independent sessions can still make similar mistakes or produce similar code.

### “Is this a full autonomous coding agent?”

Not yet. The current implementation is a bounded single-file generation-and-repair workflow. The coordinator supplies the source, applies the replacement, runs the checks, and optionally returns errors for repair. Multi-file discovery, editing tools, and an extended agent loop are future work.

### “How do you know an implementation works?”

We execute an independent browser suite and retain the observations. A model saying “tests passed” is not accepted as verification. The suite covers our stated demo behaviors; it is not a full security, accessibility, or visual-quality audit.

### “How are candidates isolated?”

Each gets its own Daytona sandbox and Git checkout. The demo uses browser-local data rather than a shared production database. Our provider keys remain in the coordinator environment, not in the generated application. Broader application support will also need isolation of external services and test data.

### “Are the previews public?”

We use port-specific signed Daytona links with an expiry, not unrestricted public sandbox access. Someone with the link can access that preview until it expires, so the URL is an access capability and should only be shared intentionally.

### “Can it automatically merge the winner?”

No. A person selects the candidate and downloads a verified patch. GitHub pull-request export is planned; automatic merging is outside the current demo.

### “Is the more expensive two-candidate workflow worth it?”

That is something to measure. We trade additional generation and sandbox work for a choice between implementations. We have not established a general productivity or cost advantage. The useful metrics would include time to an accepted change, acceptance rate, regressions, review time, and total cost per accepted change, including discarded attempts.

### “What happens if a model or sandbox fails?”

We retain failure states rather than counting missing checks as passed. Requests and commands have time limits, repair attempts are bounded, and cleanup outcomes are recorded. If the local coordinator is killed, recovery is not fully durable: sandbox IDs remain available in run records, and resources should be checked in the provider dashboard.

### “Is this production-ready?”

No. It is a working developer-run prototype. The server binds to localhost and restricts mutating request origins, but it has no multi-user authentication, durable job system, comprehensive quotas, or production hardening. Those are necessary before offering it as a public service.

## Claims to keep precise

- Say **two independent attempts with the same model**, not “two different models.”
- Say **concurrent candidate workflows**, not “guaranteed simultaneous GPU inference.”
- Say **13/13 checks on this demo task**, not “all generated code is correct.”
- Say **isolated sandboxes**, not “one dedicated GPU or VM for every agent.”
- Say **bounded repair**, not “the system keeps trying until it succeeds.”
- Say **local React dashboard and hosted candidate previews**, not “the whole platform is cloud-deployed.”
- Say **verified patch download**, not “automatic GitHub integration.”
- Say **time/token limits**, not “an enforced dollar spending cap.”

## Closing line

“We give developers a way to compare working implementations and their evidence before choosing what to ship.”
