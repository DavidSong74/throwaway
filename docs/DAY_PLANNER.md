# Run a Day Planner comparison

The runner snapshots only `examples/day_planner/Day Planner.html` into its own
local Git repository, then uploads that exact baseline to each Daytona sandbox.
No public GitHub repository is required. Your original HTML remains unchanged.

## Prepare and run

From the project root, with your provider keys/model in `.env` or exported in the terminal:

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -e '.[cloud]'
python3 -m tournament prepare-day-planner
python3 -m tournament plan task.day-planner.local.json
python3 -m tournament run task.day-planner.local.json --live
```

The `prepare-day-planner` and `plan` commands make no cloud calls. `run --live`
uses Daytona resources and Nosana inference. `NOSANA_MODEL_ID` must identify a
currently available model. Preparing again creates a new baseline and updates
`task.day-planner.local.json`; old snapshots and runs remain recoverable.

Daytona v2 is an alpha API and may not be enabled for an account. The adapter's
default `DAYTONA_API_VERSION=auto` falls back to the standard API only for that
explicit feature-disabled response. Authentication failures do not trigger a
second create attempt. `.[cloud]` includes both SDK namespaces. The standard path
uses remote process deadlines and a 15-minute idle stop with immediate deletion
on stop, in addition to explicit deletion and confirmation at run completion.

For another input file, use `prepare-day-planner --file '/absolute/path/page.html'`.
The generated task uses two candidates, one optional repair each, and up to 12,000
output tokens per request. Review the plan before launching. These limits are not
a provider dollar cap. Nosana generation requests have a separate 300-second response
timeout, configurable with `NOSANA_REQUEST_TIMEOUT` (10–600 seconds). The catalog
request uses 30 seconds. Each candidate installs Playwright and Chromium inside
Daytona, so first-run browser setup can take several minutes and incur sandbox time.
The image must permit installing Chromium's Linux dependencies and accessing package servers.

## First shared task

Improve the layout and add case-insensitive title search plus All/Open/Done filters,
while preserving scheduling, priorities, fixed times, breaks, completion, undo,
deletion, confirmation, persistence, and mobile usability. Filtering must not change
scheduled task start times. Edit the generated request if needed, keeping it aligned
with the fixed acceptance suite.

The browser tests require the existing IDs/markup in the request and these controls:

- A labeled search input with `id="search"`.
- A labeled status select with `id="status"` and values `all`, `open`, `done`.
- A non-empty no-matches message with `id="filter-empty"`, visible when no tasks match.

## Verification and artifacts

The verifier is coordinator-owned and uploaded outside the editable repository.
HTML tasks use that fixed browser profile, rather than the task's `test_command`
field. It first checks existing functionality on the unmodified baseline, then
tests each candidate's requested features and regressions. Browser networking is
blocked; pages must work with inline CSS/JS and fallback fonts.

Check `results/<run-id>/candidate-1/` and `candidate-2/`:

- `proposed_file.html`: complete generated page for manual review.
- `changes.diff`: patch against the exact baseline.
- `checks.json`: individual observed results, with missing checks marked `not_run`.
- `desktop.png`, `mobile.png`: screenshots at desktop and 390px mobile width.
- `failure.png`: failure screenshot when available.
- `baseline.log`, `baseline-checks.json`: checks before generation.
- `attempt-1.log`, optionally `attempt-2.log`: per-attempt browser output.
- `result.json`: source hash, model, usage if returned, verification, and cleanup.

The run also preserves `baseline.bundle`, `task.json`, and `summary.json`.
Screenshots may be absent if execution fails before reaching them. Final HTML and
reports are replaced on repair, while attempt logs remain. A browser launch failure
is recorded as an infrastructure error, not a successful check.

Create the passive review page for any completed run:

```bash
python3 -m tournament report results/YOUR_RUN_ID
```

Open the resulting `review.html` to compare screenshots and check results, then
follow its explicit links to candidate HTML, patches, and logs. The review page
does not embed or automatically execute generated candidate JavaScript. New runs
create the report automatically on completion.

Sandboxes are deleted after export; **no persistent hosted preview exists yet**.
Open exported HTML manually in an isolated browser profile. Generated JavaScript is
untrusted, and some browsers share file-origin localStorage across exported pages;
use separate profiles or origins for independent comparisons. The runner does not
automatically execute live model output on your computer, overwrite the original,
push branches, or select a winner. A passing bounded suite is not a full security,
accessibility, visual-quality, or scheduling-algorithm audit.

## Local verification without credits

```bash
python3 -m pip install -e '.[browser]'
export PLAYWRIGHT_BROWSERS_PATH="$PWD/work/playwright-browsers"
python3 -m playwright install chromium
python3 -m unittest discover -s tests -v
```

The integration tests use fixed trusted HTML fixtures, not model output. They
exercise baseline regressions, required-feature failure, parallel HTML candidates,
screenshots, bundle transfer, and patch reconstruction. Browser tests explicitly
skip if Playwright is absent. Without cloud credentials these tests do not establish
that the remote provider integration works.

For the original page's regression suite alone:

```bash
python3 -m tournament.verification.day_planner \
  --file 'examples/day_planner/Day Planner.html' \
  --output work/day-planner-baseline --baseline
```

The original page intentionally fails the full new-feature suite: it has no search
or status controls yet. Baseline regression and new-feature results stay separate.

### Agent-session browser limitation

This coding session's macOS process restrictions prevent Chromium from registering
its MachPortRendezvousServer (`bootstrap_check_in: Permission denied`). The browser
cannot start here, so this session has not established passing browser acceptance
results or screenshots. Run the browser tests in your normal terminal or inside
Daytona. Do not treat a browser-launch failure as a failed planner feature, and do
not mark those unobserved interactions as passed.
