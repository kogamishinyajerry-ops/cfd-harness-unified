# Codex GPT-5.4 Review · PR #20 FoamAgent Docker Guard Messaging (Phase 5 Round 6)

Date: 2026-04-21
Reviewer: GPT-5.4 via Codex post-merge review (first review under RETRO-V61-001 / v6.1 governance)
Subject files: `src/foam_agent_adapter.py`, `pyproject.toml`
Merge SHA: `b8be73a`
Baseline SHA: `320bed10`

## Verdict
APPROVED_WITH_NOTES

## Findings by severity
### Critical (must fix immediately)
None.

### High (fix before production use)
None.

### Medium (queue for follow-up)
None.

### Low / Informational
1. The alternate install command in the missing-SDK error text is shell-invalid unless the version specifier is quoted.
   Evidence: `src/foam_agent_adapter.py:424-429`. Direct probe: under `zsh`, `pip install docker>=7.0` failed with `zsh:1: 7.0 not found`; under `bash`, the same token sequence redirected output into a file named `=7.0`.
   Why it matters: this PR's goal is actionable remediation text. The extras-based install command is correct, but the alternate fallback is not reliably copy-pasteable in common shells.
   Suggested fix: change the fallback to `pip install 'docker>=7.0'` / `python -m pip install 'docker>=7.0'`, or drop it and keep only the extras-based install command.

2. The new branch-specific dispatch is reasonable but not directly pinned by tests.
   Evidence: `src/foam_agent_adapter.py:442-475`; `tests/test_foam_agent_adapter.py:111-165`. Existing tests cover generic `FakeDockerException` and a non-running container, but there is no direct test for `_DOCKER_AVAILABLE=False`, real `docker.errors.NotFound` dispatch, or the "MagicMock not a type" guard.
   Why it matters: the value of this PR is operator-facing error discrimination. Current passing tests show the wider executor flow still works, but they do not prove the new branch routing stays correct.
   Suggested fix: add narrow tests for `_DOCKER_AVAILABLE=False`, `NotFound` as a real subclass of `DockerException`, and a MagicMock-shaped `docker.errors.NotFound` attribute to pin the no-`TypeError` fallback behavior.

## Per-area analysis
### 1. Error-message dispatch / `NotFound` type guard
The dispatch logic is correct as written.

- In the real Docker SDK available in this workspace (`docker 7.1.0`), `docker.errors.NotFound` is a real exception type and a subclass of `docker.errors.DockerException`.
- With a plain `MagicMock`, `getattr(docker.errors, "NotFound", None)` returns another `MagicMock`, not a type. The `isinstance(not_found_cls, type)` guard therefore evaluates to `False`, so the code does not execute `isinstance(exc, not_found_cls)` and avoids the `TypeError` that a separate `except docker.errors.NotFound:` clause would trigger under that mock shape.
- If tests later set `docker.errors.NotFound = FakeNotFound` where `FakeNotFound` subclasses `FakeDockerException`, the same dispatch correctly classifies it as the NotFound branch.

So the pattern is a reasonable compatibility compromise between real SDK behavior and the existing loose mock shape.

### 2. Checking `NotFound` inside `except DockerException`
This is safe, and under the current test strategy it is actually safer than a separate `except docker.errors.NotFound:` clause.

- In production, `NotFound` is a `DockerException` subclass, so catching `DockerException` first and re-dispatching preserves the intended semantics.
- In tests where `docker.errors.NotFound` is a `MagicMock`, a standalone `except docker.errors.NotFound:` is not valid because Python requires an exception type there. The current manual dispatch avoids that runtime failure.
- I did not find an ordering or scope bug from `self._docker_client` being assigned before the container lookup; on any failure path, `execute()` returns immediately and later `_docker_exec()` calls are never reached.

### 3. `pyproject.toml` optional-dependency group
The declaration matches existing repo conventions.

- It is defined in the existing `[project.optional-dependencies]` table beside `dev` and `ui` at `pyproject.toml:22-43`.
- The group is scoped to one concern (`docker>=7.0`) the same way `ui` scopes FastAPI-related packages.
- The extras install syntax `.[cfd-real-solver]` is valid. Naming with hyphens is normalizable per packaging rules and does not introduce a repo-local inconsistency.

The only mismatch I saw is stylistic: some repo docs/use sites prefer `uv pip install -e ".[ui]"`, while this new operator guidance uses `.venv/bin/pip install -e '.[cfd-real-solver]'`. That is documentation style drift, not a packaging bug.

### 4. Latent-bug sweep for `foam_agent_adapter.py:418-460`
No new blocking bug stood out.

- Exception ordering is fine.
- `exc` variable reuse is local to each handler and does not shadow anything meaningful.
- Returning raw exception text in `DockerException` / generic-exception messages does not create command injection here because the string is only surfaced as an error message, not executed.
- The NotFound-specific message is more actionable than the old blanket Foam-Agent guidance, and the generic DockerException path now correctly covers daemon-unavailable and container-stopped cases.

The only concrete regression I found in this area is the unquoted `pip install docker>=7.0` fallback noted above.

### 5. Test-coverage assessment
The existing test suite is good enough to show the change did not destabilize the wider executor flow, but it is thin for the new operator-facing behavior.

What is covered:
- generic Docker failure returns a failed `ExecutionResult`
- non-running container returns a failed `ExecutionResult`
- broader happy path and downstream failure paths still work

What is not directly covered:
- `_DOCKER_AVAILABLE=False` emits the new missing-SDK guidance
- `docker.errors.NotFound` emits the container-not-found guidance
- a MagicMock-shaped `docker.errors.NotFound` attribute does not trigger `TypeError`
- exact user-facing strings for the newly differentiated branches

Given the PR purpose, those would be worthwhile to pin.

## Verification note
Executed:

- `git diff --stat 320bed10..b8be73a -- src/foam_agent_adapter.py pyproject.toml`
- `python3 -m pytest -q tests/test_foam_agent_adapter.py -k 'docker_unavailable_returns_failed_result or container_not_running_returns_failed_result or execute_success_path or execute_blockmesh_failure or execute_solver_failure or execute_mkdir_failure'` → `6 passed`
- direct Python probes against the merged `FoamAgentExecutor.execute()` path for:
  - `_DOCKER_AVAILABLE=False`
  - `docker.errors.NotFound`
  - generic `docker.errors.DockerException`
  - generic `Exception`
- live SDK probe in this workspace:
  - `docker.__version__ == 7.1.0`
  - `issubclass(docker.errors.NotFound, docker.errors.DockerException) == True`
- shell probe for the fallback install command:
  - under `zsh`, `pip install docker>=7.0` failed with `zsh:1: 7.0 not found`
  - under `bash`, the same token sequence redirected output into a file named `=7.0`
- repo grep:
  - `rg -n "foam-agent not found in PATH|Install Foam-Agent"` returned no remaining matches under the reviewed tree

I did not rerun the full 94/94 adapter file or the full 327/1skip matrix; conclusions above are based on static review plus focused verification of the changed paths.
