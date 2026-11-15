# Parallel AI Development: Nosana + Daytona Build Guide

**Purpose:** Give one existing application and one change request to three independent AI coding agents. Run each implementation, compare previews and evidence, then preserve the chosen version as a GitHub branch or pull request.

**Scope:** A practical build plan for a three-candidate MVP, followed by a path to a service supporting many users.

**Prepared:** November 15, 2026. Platform documentation was checked on this date. SDKs, model availability, limits, and pricing can change.

**Status:** This is an implementation guide, not a completed application. No live model calls, deployments, or repository changes were made while preparing it.

---

## 1. What we are building

A developer supplies:

- A GitHub repository and starting commit.
- A change request.
- A short acceptance checklist.
- Three candidate configurations.

The system returns:

- Three independent implementations.
- A running preview for each successful implementation.
- Code diffs and independently collected build/test results.
- An option to continue refining a candidate.
- An option to preserve the selected candidate as a branch or pull request.

**Product promise:** Try several implementations of a change before deciding which one to merge.

The product is useful only if the alternatives save development or review time, improve the accepted result, or both. Generating more code alone does not establish value.

### Definition of done for the first demo

- [ ] All candidates start from the same exact commit.
- [ ] Each candidate has its own Daytona sandbox and conversation history.
- [ ] Nosana-hosted inference actually generates the edits.
- [ ] At least two candidates produce running applications.
- [ ] Failed candidates show their real failure status.
- [ ] The developer can inspect previews, code changes, and test results.
- [ ] The selected implementation can be recovered independently of its sandbox.
- [ ] The starting branch is unchanged until normal review and merging.
- [ ] Resources are cleaned up after the review.

Do not require three different models for the first working version. One capable model with three separate sessions is sufficient to prove the workflow. Label the actual model and configuration honestly.

## 2. What each service does

| Component | Responsibility |
| --- | --- |
| GitHub | Source repository, exact starting commit, selected branch, pull request, final review. |
| Nosana | Runs the model inference that interprets the request and proposes coding actions. |
| Daytona | Runs each candidate's repository, tools, dependencies, tests, and application. |
| Agent runner | Repeatedly calls the model, validates its requested actions, executes tools, and returns results. |
| Coordinator | Creates runs and candidates, tracks state, applies budgets, handles cancellation, and collects results. |
| Comparison interface | Presents previews, diffs, check results, costs, and selection controls. |

The runner and coordinator can live in one backend for the MVP.

### Architecture

~~~mermaid
flowchart TD
    U["Developer: repository and request"] --> C["Coordinator"]
    C --> N["Nosana model endpoints"]
    C --> A["Daytona candidate A"]
    C --> B["Daytona candidate B"]
    C --> D["Daytona candidate C"]
    A --> R["Previews, changes, and verification"]
    B --> R
    D --> R
    R --> S["Developer selects a candidate"]
    S --> G["GitHub branch and pull request"]
~~~

The coordinator carries messages between the model and the corresponding sandbox. The model does not directly obtain unrestricted access to the coordinator.

**A candidate needs its own workspace, not its own dedicated LLM deployment.** Multiple sessions may use the same inference endpoint, within its throughput and memory limits.

Daytona sandboxes can be containers or VMs. Use a supported sandbox configuration that fits the repository; do not make a dedicated VM a requirement merely to increase the machine count.

## 3. Keep the MVP small

| Decision | First version |
| --- | --- |
| Supported applications | One known small JavaScript/TypeScript web repository. |
| Change size | One feature that can be reviewed in a few minutes. |
| Candidates | Three, after one candidate works end to end. |
| Model setup | One verified endpoint initially; add different models afterward. |
| Data | Local fixtures or candidate-specific test data. |
| Authentication | A developer-run prototype; full multi-user login can follow. |
| GitHub access | Start with a public demo repository; add private access when needed. |
| Review | Separate preview links are sufficient before embedded previews. |
| Export | Downloadable patch first, then a selected branch and PR. |
| Merging | Use normal GitHub review; do not automatically merge in the MVP. |

**Example first feature:** Add search and status filtering to a task-list application. This is easier to verify than a large redesign or authentication migration.

Avoid production databases, payments, large monorepos, native mobile builds, and arbitrary repository support in the first demo. Each introduces setup work unrelated to proving comparison and selection.

## 4. Terms you need

| Term | Meaning here |
| --- | --- |
| Model | The trained system generating responses or proposed coding actions. |
| Inference | Running a model to obtain an answer. |
| Endpoint | A URL where your backend sends model requests. |
| GPU / VRAM | Hardware and its memory used to serve suitable models. |
| Agent | A model connected to tools in a repeated decide–act–observe loop. |
| Sandbox | An isolated environment with its own project files and running processes. |
| Commit SHA | An exact saved repository version. A branch name can move; a SHA identifies the starting version. |
| Candidate | One independent attempt to implement the requested change. |
| Diff | The code changes between the starting commit and a candidate. |
| Preview | A URL exposing the candidate's running web application. |
| Acceptance check | A specific observation that establishes whether a requirement was met. |
| Pull request | A proposed branch change for review before merging. |

## 5. Prerequisites and configuration

Have these ready:

- A GitHub repository you may copy and modify.
- A known working install, build, test, and start command.
- Daytona access and an API key.
- A working Nosana model endpoint or hosted inference access.
- Git and the runtime required by the chosen repository.
- A place outside the sandboxes to save run metadata and candidate artifacts.

For a new TypeScript agent implementation, eve is a default option for durable sessions. Keep the Nosana and Daytona integrations behind adapters either way. Verify custom endpoint compatibility before choosing a framework. A small coordinator can initially run locally; it does not need cloud deployment to prove the workflow.

Keep provider credentials in the coordinator's server-side environment. Commit only an example configuration containing placeholders.

~~~dotenv
DAYTONA_API_KEY=replace_locally
NOSANA_API_MODE=hosted_openai
NOSANA_API_BASE=https://inference.nosana.com/v1
NOSANA_API_KEY=replace_locally
NOSANA_MODEL_ID=replace_with_verified_available_model
REPO_URL=https://github.com/OWNER/REPO.git
TARGET_BRANCH=main
CANDIDATE_COUNT=3
MAX_AGENT_STEPS=20
MAX_CANDIDATE_SECONDS=600
MAX_ACTIVE_CANDIDATES=3
~~~

The limits above are **suggested starting budgets**, not platform defaults or guaranteed capacity. Adjust them after measuring one candidate. Do not use a placeholder as a real model identifier.

Pin dependency versions and keep a lockfile. Follow documentation matching the SDK version you install.

## 6. Milestone A: prove the repository works without an agent

First establish that infrastructure problems will not be mistaken for AI failures.

1. Clone the demo repository locally.
2. Record its exact starting SHA.
3. Run the existing installation and checks.
4. Start the app and confirm the baseline behavior.
5. Record the expected commands and results.

Example for a repository that already defines these npm scripts:

~~~bash
git clone "$REPO_URL" demo-repo
cd demo-repo
git rev-parse HEAD
npm ci
npm run build
npm test -- --run
~~~

Do not assume those scripts exist. Inspect the repository and set its actual commands. The test command above fits some Vitest projects, not every npm project.

Create a trusted run configuration:

~~~json
{
  "repository": "https://github.com/OWNER/REPO.git",
  "base_sha": "REPLACE_WITH_ACTUAL_COMMIT",
  "target_branch": "main",
  "install_command": "npm ci",
  "build_command": "npm run build",
  "test_command": "npm test -- --run",
  "start_command": "npm run dev -- --host 0.0.0.0 --port 5173 --strictPort",
  "preview_port": 5173
}
~~~

The start command is a Vite example. Use the equivalent for your app.

**Done when:** The baseline builds, its existing tests pass, and someone has opened the application.

## 7. Milestone B: prove Nosana inference works

There are two different connection paths. Choose the one matching your account or deployment.

### Route 1: Nosana hosted inference

List the models currently available:

~~~bash
curl --fail-with-body --max-time 30 \
  "$NOSANA_API_BASE/models" \
  -H "Authorization: Bearer $NOSANA_API_KEY"
~~~

Choose an actual returned model ID. Then use the chat-completions format documented by Nosana to send a small coding request. The hosted service is OpenAI-compatible, but compatibility does not guarantee every optional feature for every model.

Verify:

- The actual response field containing the final answer.
- Whether native tool calls are supported.
- How token usage is returned.
- The context limit and a practical output budget.
- Cold versus warm response time.
- Timeout, unavailable-model, and retry behavior.

### Route 2: a custom Nosana deployment

A deployment endpoint exposing port 11434 may be serving Ollama. Confirm its actual runtime; do not infer a model name from the port.

For an Ollama deployment, list available models:

~~~bash
curl --fail-with-body --max-time 30 \
  "$NOSANA_DEPLOYMENT_BASE/api/tags"
~~~

Use authentication if your deployment requires it. Keep its URL and access configuration private when appropriate.

Send a request to the endpoint shape the runtime actually implements. Ollama's native chat route uses POST /api/chat and returns its answer under message.content. Non-streaming responses require stream:false. Its model identifier must match an installed model.

Do not interchange native Ollama paths, hosted Nosana paths, credentials, or response parsers. Put the difference inside a provider adapter.

### Required model capability test

Ask the chosen model to:

1. Inspect a short source file.
2. Propose a small valid edit in the action format you intend to support.
3. Read a real error message.
4. Correct its edit without replacing unrelated code.

**Done when:** One model completes this sequence through your adapter. If it cannot, change the model or simplify the task before building parallelism.

Do not start three GPU deployments simply because you plan three candidates. First measure how your endpoint handles separate requests. It may queue requests rather than generate three answers simultaneously.

## 8. Milestone C: prove one Daytona workspace works

Using the current Daytona SDK:

1. Create one sandbox with resources appropriate for the demo repository.
2. Set lifecycle limits and attach run/candidate labels.
3. Clone the repository at the recorded SHA.
4. Create a local candidate branch from that SHA.
5. Run the trusted install, build, and baseline test commands.
6. Start the application as a managed background session.
7. Poll its health until ready or a fixed deadline.
8. Obtain a preview URL and open it.
9. Save the sandbox ID and logs outside the sandbox.

Daytona supports repository operations, commands, sessions, and previews. Exact methods depend on the installed SDK.

### Preview details

For the Vite example:

~~~bash
npm run dev -- --host 0.0.0.0 --port 5173 --strictPort
~~~

- Bind to an externally reachable interface.
- Use a fixed port and fail if it is unavailable.
- Configure the exact preview hostname if the dev server rejects the Host header.
- Use an expiring, port-specific signed preview URL for review.
- Offer “Open preview” in a new tab if embedding fails.
- A successful HTTP response alone does not prove the feature works.

**Done when:** The unmodified application is usable through a Daytona preview.

## 9. Milestone D: define the task before generating solutions

Write the acceptance checklist once, then reuse it for all candidates.

### Example request

> Add search and status filters to the task list. Search task titles without case sensitivity. Support All, Open, and Done statuses. Combine search and status filters. Preserve existing task creation and completion behavior. Keep the current visual style and support mobile screens.

### Acceptance checks

| ID | Required behavior | Verification |
| --- | --- | --- |
| R1 | Search is case-insensitive. | Mixed-case fixture and browser interaction. |
| R2 | Each status filter displays the correct tasks. | Known open/done fixtures. |
| R3 | Search and status filters work together. | A fixture requiring both conditions. |
| R4 | Empty results have a useful message. | Search with no matches. |
| R5 | Existing task creation and completion still work. | Regression checks. |
| R6 | Controls remain usable on a narrow viewport. | Browser check and human review. |
| R7 | No unrelated feature changes. | Review the diff. |

Separate **required behavior** from preferences such as layout, wording, or animation.

Keep the authoritative verification configuration and test copies outside the candidate's editable workspace. Candidate-authored tests can add evidence, but they do not replace independent evaluation.

## 10. Milestone E: implement one bounded agent loop

A plain model API call produces a response. The agent runner turns proposed actions into actual file changes and command results.

### Minimum tool surface

| Tool | Purpose |
| --- | --- |
| list_files | Discover relevant source files, excluding generated dependencies. |
| read_file | Read a bounded portion of a project file. |
| search_files | Find definitions, imports, and call sites. |
| apply_patch | Apply an edit to allowed project files. |
| run_command | Execute a bounded command inside that candidate's sandbox. |
| finish | Request final independent verification. |

The coordinator controls sandbox creation, model credentials, export, GitHub writes, and cleanup.

Validate file paths and resolve symlinks before edits. Do not give candidates access to other candidates' files or coordinator secrets.

### Runner contract

Use native tool calling if the actual model and runtime support it. Otherwise use a strict, validated action format. Do not assume that requesting JSON makes a response safe or valid.

Illustrative action:

~~~json
{
  "action": "read_file",
  "arguments": {
    "path": "src/App.tsx"
  }
}
~~~

Reject unknown actions, malformed arguments, out-of-scope paths, and oversized requests. Return a short structured error so the model can correct the request. The coordinator dispatches known actions; it never evaluates model text as coordinator code.

### Control flow

The following is pseudocode, not a runnable SDK example:

~~~python
async def run_candidate(candidate, spec, deadline):
    history = initial_messages(spec, candidate.configuration)

    for step in range(spec.max_agent_steps):
        enforce_deadline_and_budget(deadline, candidate)

        response = await model_adapter.generate(
            model=candidate.model_id,
            messages=history
        )
        action = validate_action(response)

        if action.name == "finish":
            break

        result = await sandbox_tools.execute(
            sandbox_id=candidate.sandbox_id,
            action=action,
            deadline=deadline
        )
        history = append_exchange(history, response, result)
        persist_progress(candidate, step, result)

    return await independent_verification(candidate, spec)
~~~

Keep file reads and command output bounded so the conversation does not exceed the model context limit.

### Agent instruction template

> You are implementing one requested change in an existing application. Read the relevant files before editing. Preserve existing behavior and conventions. Work only in your assigned repository. Do not alter independent verification, expose secrets, push branches, or merge code. Use tools to inspect, edit, and run checks. Report unfinished requirements and actual failures. A claim that tests passed is not a substitute for captured test output. Stop at the configured budget.

**Done when:** One candidate independently edits the real repository, handles at least one tool result, and reaches verification.

## 11. Milestone F: expand to three candidates

Only parallelize the working single-candidate path.

For each candidate, create:

- A unique candidate ID and branch name.
- An independent sandbox and repository copy.
- The same starting SHA.
- A separate conversation history.
- A recorded model/configuration.
- A fixed time and action budget.

Example branch names:

- candidates/run-001/a
- candidates/run-001/b
- candidates/run-001/c

Use a bounded worker pool. Three logical candidates do not require three inference requests to execute at the same instant; limit requests to what the endpoint can support.

### Two valid comparison modes

| Mode | What varies | What you can conclude |
| --- | --- | --- |
| Model comparison | Model; keep instructions and budgets comparable. | Performance of the tested models and deployments on this task. |
| Implementation exploration | Strategy, sampling, or follow-up instructions may vary. | Which implementation the developer prefers. |

For model comparison, do not secretly give one candidate better context or a larger repair budget.

For exploration, optional strategies could emphasize minimal changes, interaction design, or maintainability. Every candidate must still satisfy the same required behavior. Record which strategy each used.

If one candidate fails, keep the other runs alive. Support cancellation without losing already generated artifacts.

## 12. Milestone G: verify independently

After generation, the coordinator runs checks against the resulting files.

1. Confirm the candidate started from the expected SHA.
2. Capture changed files and detect unrelated modifications.
3. Check that the configured verification has not been weakened.
4. Run build and type/lint checks that the project actually defines.
5. Run baseline regression tests and the shared acceptance suite.
6. Start or restart the app with the final code.
7. Exercise the requested behavior in a browser.
8. Save structured results and logs.

Use explicit statuses:

| Status | Meaning |
| --- | --- |
| passed | The check ran and satisfied its assertion. |
| failed | The check ran and found a problem. |
| timed_out | Its configured deadline was exceeded. |
| not_run | No observation was collected. |
| infrastructure_error | Setup, provider, or environment failure prevented evaluation. |

Never turn not_run into passed. Never derive test counts from the model's summary.

For each displayed result, retain the candidate revision being tested. Any subsequent edit invalidates the old result until verification runs again.

### Scoring for this product

Use required behavior and regressions to establish eligibility. Then let people compare UX, visual fit, code quality, and maintenance burden.

Display:

- Required checks passed / total.
- Build and regression status.
- Files changed and diff size.
- Time to reviewable preview.
- Actual or explicitly estimated spending.
- Known limitations.

A universal “best AI” score is unnecessary. The user is selecting a change to their own application.

## 13. Milestone H: build the comparison interface

First make the workflow operable with a command-line coordinator. Then add the interface.

### Input screen

Collect repository, branch/commit, change request, acceptance checklist, candidate configurations, and run budget. Resolve a branch to an exact SHA at run creation.

### Run screen

Show each candidate's status:

queued → provisioning → preparing → generating → verifying → ready / failed / cancelled

The generation phase can contain repeated edit and tool cycles.

### Candidate review

Each candidate needs:

- Preview and “Open in new tab”.
- Actual model and strategy.
- Requirement and regression results.
- Code diff.
- Change summary with links to supporting evidence.
- Time, spending, and failure information.
- Continue, select, discard, and cancel actions where applicable.

Keep source labels separate from quality labels: the model's explanation is a claim; captured checks are observations.

Continuing a candidate creates a new revision. Selecting it freezes the exact revision to export. Do not allow background edits to change a version after selection.

### Backend interfaces to implement

| Endpoint | Responsibility |
| --- | --- |
| POST /runs | Validate input, resolve SHA, create candidate records, enqueue work. |
| GET /runs/:id | Return current candidate states and results. |
| GET /runs/:id/events | Stream progress or provide a polling alternative. |
| POST /candidates/:id/continue | Create a revision with follow-up instructions. |
| POST /candidates/:id/select | Freeze the chosen revision and begin export. |
| POST /runs/:id/cancel | Stop unfinished work and save partial evidence. |
| GET /candidates/:id/artifacts | Return authorized access to diffs and reports. |

These are proposed application endpoints, not Daytona or Nosana APIs.

## 14. Milestone I: preserve the selected implementation

Do not delete a sandbox until its selected code is recoverable.

### First export path: a patch

1. Freeze the selected files.
2. Review tracked and untracked changes.
3. Stage only intended files, including approved new files.
4. Create a local candidate commit.
5. Export a binary-capable diff against the base SHA.
6. Save it outside the sandbox.
7. Apply it to a clean copy at the base SHA and rerun verification.

Example commands inside the candidate repository:

~~~bash
git status --short
git add -- src
git diff --cached --check
git commit -m "Implement selected candidate change"
git diff --binary "$BASE_SHA" HEAD > /tmp/selected-candidate.patch
~~~

Add approved files outside src explicitly if the feature needs them. Do not omit required untracked files. The patch example assumes a commit was actually created and BASE_SHA has the recorded value.

### GitHub path

After export works:

1. Use a unique candidate branch.
2. Push the frozen commit with authorized repository access.
3. Open a pull request against the intended target branch.
4. Include the original request, base SHA, candidate commit, results, and limitations.
5. Have the developer review and merge normally.

Keep write credentials outside the model's accessible context. Prefer coordinator-controlled push/PR operations.

If the target branch has advanced, check integration against its new state and rerun relevant checks. Resolving conflicts changes the code and invalidates earlier evidence for the modified revision.

Avoid merging several alternatives together in the MVP. That is a new implementation requiring its own review.

## 15. Save enough state to recover

Store run records outside disposable environments.

| Record | Important fields |
| --- | --- |
| Run | ID, repository, target branch, base SHA, request, acceptance spec, budget, timestamps. |
| Candidate | ID, run ID, sandbox ID, branch, model ID, endpoint mode, strategy, revision, state. |
| Action | Candidate/revision, action name, duration, bounded output, exit code, error. |
| Verification | Candidate/revision, check ID, status, log reference, timestamp. |
| Artifact | Patch, diff, screenshot/report references, content hash, candidate commit. |
| Selection | Selected candidate/revision, exported commit, PR URL, export status. |

A small local database or structured files are enough for a developer-run demo. Preserve IDs before the next external action so interrupted runs can be reconciled.

Selection and export should be idempotent: retrying the same request should return the existing export or PR instead of duplicating it.

## 16. Budgets, failures, and cleanup

Start with a small project and measured resource needs. Record:

- Sandbox creation, preparation, generation, verification, and review duration separately.
- Model usage where available.
- GPU rental duration for dedicated deployments.
- Sandbox running/storage usage.
- Failure and retry counts.

Hosted per-token inference and a dedicated rented GPU have different cost structures. Do not estimate a dedicated deployment solely from token counts. Label costs as estimated unless reconciled to provider billing.

Implement:

- Per-command timeout.
- Per-candidate deadline and action limit.
- Per-run concurrency and spending limits.
- Bounded retries for transient provider errors.
- Cancellation propagated to model requests where supported and to sandbox processes.
- Cleanup on success, failure, cancellation, and coordinator restart.
- A short review lifetime with a way to recover from saved artifacts afterward.

Stopping a sandbox is not necessarily the same as deleting it or eliminating every charge. Check lifecycle and billing rules. Stop dedicated Nosana deployments too when they are no longer needed; cleaning Daytona does not stop Nosana billing.

Do not immediately destroy a preview the developer is still reviewing. Export first, then end the relevant review session and clean up.

### Isolation that matters for this app

Separate candidates must also use separate test data, databases, or namespaces. Separate filesystems do not isolate a shared external database.

Keep production credentials out of generated applications. Treat repository instructions and model output as inputs bounded by the coordinator's policy. Build and install scripts themselves execute code, so run them in the assigned environment.

## 17. Troubleshooting

| Symptom | Likely cause | Next check |
| --- | --- | --- |
| Nosana URL returns 404 | Wrong route or serving runtime. | Confirm hosted versus custom mode and endpoint paths. |
| Endpoint exists but inference fails | Model not ready, wrong model name, or insufficient capacity. | Inspect deployment logs and model listing. |
| Three candidates become slow together | Shared GPU contention or queued requests. | Measure one request, then two; reduce concurrency before adding replicas. |
| Model returns prose instead of an action | Unsupported tools or weak action-format adherence. | Validate model capability and use the correct adapter. |
| Agent repeatedly changes unrelated files | Task is too broad or context is incomplete. | Narrow the feature, inspect the diff, and stop at the action budget. |
| Sandbox build fails before any edits | Baseline or environment issue. | Compare runtime, lockfile, install logs, and baseline checks. |
| Preview fails but process is running | Wrong port, interface, Host policy, authentication, or app crash. | Check health locally, logs, and signed URL settings. |
| Embedded preview fails | Browser framing/cookie constraints. | Open the signed preview in a new tab. |
| “All tests passed” appears without logs | Agent summary was treated as verification. | Run the independent suite and replace the claim with measured status. |
| Exported result misses files | New files were not included in the commit/patch. | Inspect tracked/untracked files and reconstruct from a clean base. |
| Two candidates affect each other | Shared data, credentials, paths, or mutable state. | Check isolation beyond Git branches. |
| Pull request creation is retried repeatedly | Export state was not persisted. | Reconcile the existing branch and PR before retrying. |
| Charges continue after review | Remaining sandboxes, storage, or GPU deployments. | Check both providers and lifecycle states. |

## 18. Build order and team ownership

| Stage | Deliverable | Stop-and-check gate |
| --- | --- | --- |
| 1 | Trusted sample repository and task. | Baseline works locally. |
| 2 | Nosana adapter. | Real coding action and correction work. |
| 3 | Daytona adapter. | Baseline runs through a preview. |
| 4 | One candidate runner. | Actual edit, verification, and recoverable artifact. |
| 5 | Three independent candidates. | Same SHA, separate state, bounded concurrency. |
| 6 | Comparison interface. | User can inspect evidence and interact with previews. |
| 7 | Selected branch and PR. | Exact reviewed version is recoverable and reproducible. |
| 8 | Cleanup and recovery. | Failed/interrupted runs do not leave unmanaged work. |

Suggested team ownership:

- **Execution:** Daytona environments, repository preparation, checks, previews, cleanup.
- **Inference:** Nosana connections, action protocol, agent loop, model budgets.
- **Product:** Run interface, comparison, follow-up, selection, and demonstration.
- **Shared integration:** Agree on run/candidate records and implement one end-to-end candidate early.

These are responsibilities, not a requirement for a particular team size. Work through the gates in dependency order.

If time runs short, keep one model, three sessions, separate preview links, and patch export. Cut extra frameworks, sophisticated scoring, and automatic PR creation before cutting actual execution or verification.

## 19. Demonstrate the product

A short demo should show a real change moving through the system.

1. Open the starting application and state the requirement.
2. Show the shared base SHA and three candidate configurations.
3. Launch the run and show actual progress events.
4. Open the resulting previews.
5. Exercise one important requirement in each version.
6. Inspect a failure or meaningful tradeoff.
7. Choose a candidate and show the saved patch or PR.
8. Show that the starting branch remains unchanged pending review.

If showing a prerecorded run, identify it as such. Do not present cached output as a live execution.

### Explain the sponsor integration accurately

> Nosana serves the model inference for independent coding sessions. Daytona gives each session a reproducible environment to edit, build, test, and preview the application. Our product helps the developer compare those implementations and preserve the preferred change.

The useful contribution is the coordination, verification, and selection workflow. Neither brand is technically irreplaceable, and the pitch does not need to claim otherwise.

## 20. Decide whether to scale

Scale when there is a measured bottleneck or more real work.

| Workload | Workspaces |
| --- | --- |
| One developer, three candidates | 3 |
| Ten simultaneous developers, three candidates each | 30 |
| Twenty-five simultaneous developers, four candidates each | 100 |

These are arithmetic examples, not confirmed account limits. Queuing can keep active workspaces below total candidates.

Scale separately:

- **Execution:** Sandbox concurrency, resources, snapshot preparation, and preview lifetime.
- **Inference:** Request concurrency, context length, tokens per second, queue length, and model-serving replicas.
- **Coordination:** Durable jobs, retries, cancellation, per-user quotas, and recovery.
- **Review:** Keep the number of alternatives a person must inspect manageable.

A hundred coding workspaces do not imply a hundred GPU deployments. Conversely, a single inference endpoint may not support a hundred responsive sessions.

### Measure product value first

Compare a one-agent baseline with the three-candidate workflow on the same representative tasks and a comparable total budget. Record differences rather than claiming a universal winner.

| Metric | Definition |
| --- | --- |
| Time to accepted change | Request submission to developer acceptance, including review. |
| Acceptance rate | Tasks producing an accepted implementation / tasks started. |
| Requirements met | Independently verified requirements satisfied by the selected result. |
| Regressions | Existing behavior broken by the selected result. |
| Cost per accepted change | All inference/execution spending, including discarded attempts, / accepted changes. |
| Review burden | Human minutes spent comparing and correcting candidates. |

If more candidates increase spending and review time without improving outcomes, keep fewer candidates or change when alternatives are generated.

Do not assume attempts are independent: several models can repeat the same misunderstanding. Better acceptance criteria and context may help more than additional machines.

## 21. Final launch checklist

### End-to-end behavior

- [ ] Exact starting SHA is recorded and reused.
- [ ] Actual model identity and configuration are displayed.
- [ ] Each candidate has independent editable state.
- [ ] Failed and timed-out candidates are represented honestly.
- [ ] Verification comes from captured execution.
- [ ] Previews show the final verified revision.
- [ ] Follow-up edits invalidate old results.
- [ ] Selection freezes one exact version.
- [ ] Export includes required new and modified files.
- [ ] The chosen change applies and checks pass on a clean base.
- [ ] PR creation does not automatically merge.

### Operations

- [ ] Credentials remain server-side and are redacted from logs.
- [ ] Candidate data and external resources are isolated.
- [ ] Limits, cancellation, and retries are bounded.
- [ ] Artifacts survive sandbox deletion.
- [ ] Cleanup covers Daytona and any dedicated Nosana deployments.
- [ ] Actual spending and estimates are distinguished.
- [ ] Account concurrency and model availability are verified before a live demo.

## 22. Official references

Implementation guidance above combines documented capabilities with proposed product decisions. The milestone order, application endpoints, budgets, data model, and acceptance checklist are our design choices.

- [Daytona Git operations](https://www.daytona.io/docs/en/git-operations/)
- [Daytona process and code execution](https://www.daytona.io/docs/en/process-code-execution/)
- [Daytona preview URLs](https://www.daytona.io/docs/en/preview/)
- [Daytona sandboxes and lifecycle](https://www.daytona.io/docs/en/sandboxes/)
- [Daytona scaling](https://www.daytona.io/docs/en/scale/)
- [Daytona coding-agent example](https://www.daytona.io/docs/en/guides/copilotkit/copilotkit-generative-ui-coding-agent-sandbox/)
- [Nosana hosted LLM inference](https://learn.nosana.com/llm/)
- [Nosana deployment endpoints](https://learn.nosana.com/inference/endpoints)
- [Ollama model listing](https://docs.ollama.com/api/tags)
- [Ollama chat API](https://docs.ollama.com/api/chat)
- [GitHub pull-request API](https://docs.github.com/en/rest/pulls/pulls#create-a-pull-request)
- [Vite development-server options](https://vite.dev/config/server-options.html)
- [eve agent framework](https://eve.dev/docs)

Before implementing SDK calls, check the installed package's versioned documentation. The pseudocode and proposed routes in this guide are explicitly not a ready-to-run backend.

