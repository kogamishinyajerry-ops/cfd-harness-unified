# AI Advisor Interaction Spec

The AI advisor is a feature, not the product. The product is the trust loop.
The advisor sits next to the trust loop and explains its outputs.

## What the AI advisor MAY do

- Read `case_manifest.yaml`, every `artifacts/*.json` and `*.csv`, and `trust_report.json`.
- Explain residual / mesh / BC / QoI / reference findings in natural language.
- Summarize Red Team findings.
- Recommend the next experiment ("try mesh-level 2 + recheck y+").
- Cite artifact paths and exact field names.
- Refuse to answer when evidence is missing.

## What the AI advisor MUST NOT do

- modify any case file (manifest, BC, mesh, scripts)
- silently change turbulence model, residual targets, or tolerances
- overwrite or "improve" `trust_report.json`
- turn FAIL into PASS in any artifact
- approve previous output it generated
- assert facts not present in the artifacts it cites

## Output contract

Every advisor output is a structured block:

```yaml
advisor_response:
  case_id: <string>
  question: <string>
  answer: <markdown text>
  evidence:
    - artifact: cases/<case>/artifacts/solver.log
      excerpt: "..."
    - artifact: cases/<case>/artifacts/trust_report.json
      jsonpath: "$.gates.solver_execution.status"
      value: "MOCKED"
  recommendations:
    - <string>
  confidence: low | medium | high
  refusal_reason: <string or null>
```

If `evidence` is empty, the response is presented as opinion, never as fact.
If the response cites an artifact that does not exist on disk, the advisor must
return `refusal_reason: "evidence not available"`.

## Interaction modes (Phase 4 design preview)

- **explain** — given a `trust_report.json`, summarize what it says
- **diagnose** — given a non-PASS report, propose hypotheses with evidence
- **recommend** — propose the next experiment with explicit assumptions
- **review** — read a candidate case manifest and flag risks before the run

The advisor never has a "fix it" mode in this project.

## Failure modes the advisor protects against

- residuals look fine but QoI drifts → advisor must surface qoi_stability gate
- reference dataset wrong-applied → advisor must surface reference_comparison.notes
- mesh quality passes but BL is missing → advisor must surface mesh_contract details
- AI overconfidence → advisor must report `confidence: low` when evidence is thin

## Failure modes the advisor must NOT cause

- creating evidence (don't write residuals.csv)
- changing limits (don't widen tolerance)
- replacing operator judgment (the operator is the decision-maker)
