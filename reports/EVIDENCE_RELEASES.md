# Evidence releases — archived artifacts

Historical process/evidence files removed from the local working copy to reclaim disk space. Restore from GitHub Releases when forensic audit is needed.

## Recent

### `evidence-20260424` · DEC-V61-050 + V61-053 close (2026-04-24)

GitHub Release: <https://github.com/kogamishinyajerry-ops/cfd-harness-unified/releases/tag/evidence-20260424>

| Asset | Size (compressed) | Contents |
|-------|-------------------|----------|
| `evidence-deep-acceptance-archive.tar.gz` | 91 MB | `reports/deep_acceptance/_archive_20260420_iteration_dupes/` — quarantined iteration dupes from pre-V61-050 acceptance cycles |
| `evidence-html-dupes.tar.gz` | 150 MB | 41 timestamped `visual_acceptance_report_*.html` + 28 `contract_status_dashboard_*.html` (each ~5MB HTML with inline PNG fixtures). Master non-timestamped files preserved on main. |
| `evidence-phase5-fields-orphans.tar.gz` | 18 MB | 16 orphan `reports/phase5_fields/<case>/<timestamp>/` dirs no longer referenced by any `runs/audit_real_run.json` manifest. Current manifest-pointed timestamps preserved locally (Compare-tab runtime). |

**Related DECs closed in this cycle:**
- DEC-V61-050 LDC true multi-dim — closed round 4 APPROVE clean (`bef6d50`)
- DEC-V61-053 cylinder Type I multi-dim — closed round 4 APPROVE_WITH_COMMENTS demonstration-grade (`41fdf37`)

**Reclamation delta**: 2.3 GB → 1.7 GB locally (600 MB reclaimed; 259 MB on GitHub Release).

## Restore instructions

Authenticate once: `gh auth login`.

```bash
# Download a single asset
gh release download evidence-20260424 \
  -R kogamishinyajerry-ops/cfd-harness-unified \
  --pattern 'evidence-html-dupes.tar.gz'

# Extract into the repo (overlays into reports/ tree)
tar -xzf evidence-html-dupes.tar.gz -C /path/to/cfd-harness-unified

# Clean up the tarball after restore
rm evidence-html-dupes.tar.gz
```

To restore everything:
```bash
gh release download evidence-20260424 -R kogamishinyajerry-ops/cfd-harness-unified
for f in evidence-*.tar.gz; do tar -xzf "$f" -C /path/to/cfd-harness-unified; done
```

## Also regenerable locally (not uploaded)

These were removed to reclaim space but are rebuildable from source — no backup needed:

- `ui/frontend/node_modules/` (144 MB) → `cd ui/frontend && npm install`
- `ui/frontend/dist.stale.*/` (~1 MB) → obsolete Vite build output
- `__pycache__/` across repo (~30 MB) → Python auto-generates on import

## Policy for future cycles

When a DEC closes and the iteration-dupe / evidence HTML accumulation gets heavy:
1. Tag: `evidence-YYYYMMDD-<context>`
2. Tarball the categories into `evidence-<category>.tar.gz`
3. `gh release create` with tarball assets
4. Add a row to this file with asset list + reclamation delta
5. Delete locally
