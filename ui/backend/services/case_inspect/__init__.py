"""DEC-V61-102 Phase 1.3 · case_inspect — case state preview service.

Powers the frontend "Preview before AI 处理" modal: returns the current
manifest, a per-dict-file summary, and (critically) a list of paths
that the next AI re-author would CLOBBER if the engineer doesn't
explicitly confirm. The frontend uses that list to surface a
confirm-overwrite prompt.
"""
from .preview import build_state_preview, StatePreview

__all__ = ["build_state_preview", "StatePreview"]
