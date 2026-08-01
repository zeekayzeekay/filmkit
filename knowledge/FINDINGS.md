# FILMKIT — general findings

Faults that have cost something, and that survive the portability test: their fixture
still fires with every project proper noun stripped.

**A finding is not closed until it has a guard and a fixture.**

Each entry carries a metadata block, from which `checklist.py` derives the review
checklist — so the checklist cannot drift from the ledger.

```
<!-- guard: automatic|manual   scope: prompt|asset|frames|process|delivery
     ask: the question a reviewer must answer in writing -->
```

Populated by `bin/filmkit-promote`. Nothing is hand-added here.
