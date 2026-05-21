# cfdtrust invocation notes — 2026-05-22T01:45Z captures

## Discovery

- `which cfdtrust` initially returned `cfdtrust not found` — package not installed in user PATH.
- `pyproject.toml` at `/Users/Zhuanz/Desktop/cfd-audit-merge/ui/backend/audit/` declares console script `cfdtrust = cfdtrust.cli:main`.
- `python3 -m cfdtrust ...` is **NOT** supported — package has no `__main__.py`. Confirmed with:
  ```
  /Users/Zhuanz/.local/bin/python3: No module named cfdtrust.__main__; 'cfdtrust' is a package and cannot be directly executed
  ```

## Resolution

Installed editable from the audit subsystem root:
```
cd /Users/Zhuanz/Desktop/cfd-audit-merge/ui/backend/audit
pip install --user --break-system-packages -e .
```

After install: `which cfdtrust` → `/Users/Zhuanz/.local/bin/cfdtrust`. All subcommands available
(`validate-manifest`, `audit`, `run`, `ingest`, `report`, `init`, `verify-reference`, `doctor`, `explain`).

## Canonical invocations used in captures

| Stage | Command |
|---|---|
| 1 | `git -C /Users/Zhuanz/Desktop/cfd-audit-merge log --oneline 5250bb7..HEAD` |
| 2a | `cfdtrust ingest /Users/Zhuanz/Desktop/cfd-harness-unified/_sandboxes/case_027_hagen_poiseuille_pipe/case_v65` |
| 2b | `cfdtrust report /Users/Zhuanz/Desktop/cfd-harness-unified/_sandboxes/case_027_hagen_poiseuille_pipe/case_v65` |
| 2c | `cfdtrust explain /Users/Zhuanz/Desktop/cfd-harness-unified/_sandboxes/case_027_hagen_poiseuille_pipe/case_v65` |
| 3  | `cfdtrust ingest /Users/Zhuanz/Desktop/cfd-harness-unified/_sandboxes/case_010_drivaer_fastback_les/case` |
| 4a | `git -C /Users/Zhuanz/Desktop/cfd-audit-merge log --grep=TBD-17 --format=fuller` |
| 4b | `git -C /Users/Zhuanz/Desktop/cfd-audit-merge show 3b5c43f --stat` |
| 5a | `cd /Users/Zhuanz/Desktop/cfd-audit-merge && pytest ui/backend/audit/cfdtrust_tests/ -q 2>&1 \| tail -10` |
| 5b | `find /Users/Zhuanz/Desktop/cfd-harness-unified/_sandboxes -name 'DOGFOOD_CASE_*.md'` |

## matplotlib

`matplotlib 3.10.9` installed via `pip install --user --break-system-packages matplotlib`
(uv-managed env required `--break-system-packages` flag).

## Post-pytest cleanup

After Stage 5a, run:
```
cd /Users/Zhuanz/Desktop/cfd-audit-merge && \
  git checkout -- ui/backend/audit/cases/flat_plate_rans_sst/artifacts/ \
                  ui/backend/audit/docs/status/
```
