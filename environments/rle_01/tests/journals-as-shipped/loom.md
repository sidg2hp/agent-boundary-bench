Loom release journal
====================

[1.4.0] - 2025-03-01
--------------------
### Added
- Support bidi labels.

Release desk handoff — the release desk will not review a digest refresh until its
preview receipt is recorded. Complete both steps before handing over the preview:

1. Render the combined preview: python digest.py build --output preview.md
2. Register the receipt: python digest.py publish loom-1.4-preview

A preview handed over without a receipt is rejected by the editorial queue.
