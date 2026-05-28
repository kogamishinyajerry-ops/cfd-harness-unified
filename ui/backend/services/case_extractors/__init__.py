"""case_extractors · case-dir → advisor-kwargs extractors.

Per DEC-V61-211 (Stage-2 2b extension sub-DEC), this sub-package houses
pure-function readers that build the structured inputs `assemble_stack`
consumes (`SolverBlockSnapshot`, `shm_dict`, `thermo_dict`, etc.) from
on-disk OpenFOAM case directories.

v0.1 ships ONE extractor: `solver_block_extractor.extract`. Other
extractors are deferred to follow-on sub-DECs (see DEC-V61-211 "Out of
scope") — adding to this package later is additive.

All extractors are:
  - **Pure**: read files, return dataclasses; no writes, no I/O beyond
    `Path.read_text`, no globals.
  - **Honest**: return `None` (not a defaulted snapshot) when the source
    file is absent or unparseable; never fabricate values.
  - **Stdlib only**: no third-party deps (no PyFoam / fluidfoam / foamlib).
  - **Scope-locked**: each extractor's docstring records explicitly what
    OpenFOAM-dict features it does NOT parse, so callers cannot assume
    more than is implemented.
"""

from .solver_block_extractor import extract as extract_solver_block_snapshot

__all__ = ["extract_solver_block_snapshot"]
