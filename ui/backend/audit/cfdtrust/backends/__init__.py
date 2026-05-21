"""Solver backends.

Each backend exposes a single entry point::

    def run(case_dir: Path, manifest: Dict[str, Any]) -> Dict[str, Any]: ...

returning a gate dict in the same shape as `cfdtrust.audit.solver` produces.

Phase 1 ships one backend: `openfoam` (Docker-only, per DEC-0005).
"""
