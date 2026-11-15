# TODO: Day Planner → Hosted Previews & React Comparison UI

## Demo status — November 15

- [x] Hosted Daytona preview servers with port-specific signed URLs and a 15-minute review window.
- [x] Local coordinator API: launch, polling, artifact access, selection/download, and cleanup.
- [x] React + Vite comparison UI: run launcher, candidate cards, previews, screenshots, diff/log inspection, selection, cleanup.
- [x] Real run `20261115T074027Z-8525f744`: both candidates passed 13/13 browser checks, both preview URLs returned HTTP 200, and both patches reconstructed the verified source on clean checkouts.
- [x] React desktop/mobile rendering checked in Chromium using a captured API snapshot; no JavaScript errors.
- [x] Selection, patch download, idempotency, cleanup response, and cross-origin rejection tested against a local API fixture.
- [ ] Human demo rehearsal: choose a winner in the UI, download its patch, then click cleanup after review.

**Open the demo:** http://127.0.0.1:8787/?run=20261115T074027Z-8525f744

**Restart the app:** `.venv/bin/python -m tournament.server` (frontend is already built).
**Rebuild the UI:** `cd ui && npm run build`.

Previews are deliberately still running for the demo. They expire 15 minutes after readiness; cleanup is also available in the UI. The earlier implementation instructions below are retained as design context; their descriptions of immediate sandbox deletion/static-only UI reflect the previous version. The server binds to localhost and keys remain server-side.

---

This checklist takes the working **Day Planner** pipeline (`tournament/` + `examples/day_planner/Day Planner.html`) to the full **Hackathon MVP** in `README.md`: **live hosted Daytona previews** and an interactive **React Comparison UI** with patch download and explicit cleanup.

---

## 0. Current Baseline (Already Working)

- [x] `examples/day_planner/Day Planner.html` single-file app + Playwright verification profile (`tournament/verification/day_planner.py`).
- [x] `prepare-day-planner`, `plan`, `run --live`, and static `report` (`review.html`) CLI commands.
- [x] `.venv` with `.[cloud]` (`daytona==2.0.0a12`) installed; `.env` configured and gitignored.
- [x] Offline unit tests passing (`tests/`).

---

## 1. Verify Live Day Planner Smoke Run (Gate 1)

Confirm one real Nosana + Daytona Day Planner run works end to end before adding the web server & React UI:

```bash
source .venv/bin/activate
python3 -m tournament prepare-day-planner
python3 -m tournament plan task.day-planner.local.json
python3 -m tournament run task.day-planner.local.json --live
```

- Check `results/<run-id>/summary.json` and `review.html` for real `proposed_file.html`, `changes.diff`, `checks.json`, `desktop.png`, `mobile.png`, and `cleanup: "confirmed"`.

---

## 2. Add Live Hosted Previews in Daytona (`tournament/runner.py` & `providers.py`)

Currently `runner.py` deletes each sandbox immediately in `finally: workspace.close()`, so `review.html` only has static screenshots and exported HTML. Upgrade the lifecycle for live previews:

1. **Serve the final candidate revision inside each Daytona sandbox:**
   - For `Day Planner.html`: start a lightweight HTTP server (`python3 -m http.server <port> --bind 0.0.0.0`) serving the final directory in the background inside the sandbox.
   - *(Optional if switching target to a React/Vite repo)*: run `npm run build` and `npx vite preview --host 0.0.0.0 --port <port>`.
   - Poll `http://127.0.0.1:<port>` inside the sandbox until HTTP 200 before marking the candidate `ready`.
2. **Capture and persist the Daytona preview URL:**
   - Use `daytona==2.0.0a12`'s documented preview/port-forwarding API on the running sandbox port.
   - Persist `preview_url`, `preview_port`, and `preview_expires_at` in `results/<run-id>/<candidate>/result.json`.
3. **Export artifacts before review & decouple sandbox deletion:**
   - Write `proposed_file.html`, `changes.diff`, `checks.json`, screenshots, and logs to `results/<run-id>/` **as soon as verification finishes** so artifacts survive sandbox deletion.
   - Keep sandboxes alive during the review window (e.g., 15-minute deadline) instead of closing them in `candidate()`'s `finally` block on success.
   - Still close sandboxes immediately on infrastructure failure/cancellation, and expose a separate `cleanup_run(run_id)` function that deletes both sandboxes by `sandbox_id` and records `cleanup: "confirmed" | "needs_attention"`.

---

## 3. Build the Local Coordinator HTTP API

Expose a thin local HTTP server (Python FastAPI/Starlette or Node/TypeScript calling the coordinator) backed by `results/<run-id>/`:

- `POST /runs` — Accept the shared change request (pre-filled with the Day Planner search + All/Open/Done prompt), snapshot the exact baseline (`base_sha` + `baseline.bundle`), and launch 2 independent candidates in background workers.
- `GET /runs/:id` — Return run metadata and per-candidate live status:
  - Lifecycle state: `queued → provisioning → preparing → generating → verifying → ready | failed | cancelled`
  - Separate statuses: `build` / `feature_check` / `preview` / `export` / `cleanup` (`passed`, `failed`, `not_run`, `timed_out`, `infrastructure_error`)
  - `model`, `sandbox_id`, `preview_url`, `elapsed_ms`, `usage`, and concrete `error` message on failure.
- `GET /runs/:id/candidates/:candidateId/artifacts/:name` — Serve allowlisted artifacts only (`changes.diff`, `proposed_file.html`, `checks.json`, `desktop.png`, `mobile.png`, `attempt-1.log`, `attempt-2.log`, `result.json`).
- `POST /runs/:id/select` — Freeze the chosen candidate (enabled only when artifacts are saved and required checks pass), apply `changes.diff` to a clean temp checkout at `base_sha` to verify clean patch application, and return the patch download URL.
- `POST /runs/:id/cleanup` — Export any remaining artifacts, delete both Daytona sandboxes, and return confirmed cleanup statuses.

---

## 4. Build the React Comparison UI (`ui/`)

Scaffold a lightweight React + Vite frontend (`ui/`) connected to the coordinator API:

1. **Run Launcher:**
   - Display the target (`Day Planner.html`) and resolved `base_sha`.
   - Editable change-request textarea + **Launch 2 Candidates** button.
2. **Side-by-Side Candidate Cards (`candidate-1`, `candidate-2`):**
   - Poll `GET /runs/:id` to show live stage transitions, actual `model` ID, and elapsed time.
   - Display separate status badges (`feature_check`, `preview`, `export`, `cleanup`) — never treat missing checks as a pass.
   - **Open Live Preview** button (opens `preview_url` in a new tab).
   - **Screenshots** (`desktop.png`, `mobile.png`), **Diff Viewer** (`changes.diff`), and **Log Viewer** (`attempt-1.log` / `attempt-2.log`).
   - Clear failure banner if a candidate failed or timed out.
3. **Selection, Patch Download & Cleanup:**
   - **Select & Download Patch** button calling `POST /runs/:id/select` and downloading `changes.diff` (plus showing clean-checkout verification result).
   - **Clean Up Sandboxes** button calling `POST /runs/:id/cleanup` and displaying `cleanup: confirmed` for both sandboxes.

---

## 5. End-to-End Demo Rehearsal

- [ ] Launch a live 2-candidate Day Planner run from the React Comparison UI.
- [ ] Open both live Daytona preview URLs in browser tabs and test search (`#search`), status filter (`#status`: All/Open/Done), combined filtering, empty state (`#filter-empty`), task creation, completion toggle, and mobile layout.
- [ ] Inspect diffs, logs, and screenshots side by side in the React UI.
- [ ] Select a winner, download `changes.diff`, and verify clean patch application at `base_sha`.
- [ ] Click **Clean Up Sandboxes** and confirm both Daytona sandboxes are deleted while all artifacts remain in `results/<run-id>/`.
