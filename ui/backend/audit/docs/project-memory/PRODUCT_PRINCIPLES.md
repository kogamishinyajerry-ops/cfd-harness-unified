# Product Principles

These principles override agent creativity. If a proposed feature violates one,
the feature is wrong, not the principle.

## 1. Correctness before convenience
A button that runs a case is less valuable than a gate that rejects an unsound case.
The product is "the case is correct" before it is "the case is easy."

## 2. Evidence over assertion
Every status, badge, score, or summary the product shows must point to an artifact
on disk. If a claim cannot point to an artifact, the product does not show it.

## 3. Honest defaults
If the solver is mocked, the cockpit says "MOCKED." If the reference is a placeholder,
the case manifest says `placeholder`. There is no "make it look green" mode.

## 4. Low cognitive load for the human
The owner must be able to understand state in under one minute. Anything that
requires reading multiple chat windows or memorizing agent histories has already
lost.

## 5. The advisor is an advisor
AI does not change the case, override gates, or generate evidence. The AI advisor
exists to summarize, explain, and recommend — not to act.

## 6. Project truth lives in the repo
Decisions, blockers, progress, and risks live in versioned files. Chat memory is
working memory, not project memory.

## 7. No premature workbench
The temptation to build a "real-looking" CFD UI before the trust loop is credible
is the single greatest historical risk for this project. The product owner has
been burned by this before. Refuse the temptation.

## 8. Negative space
What the product does not have is part of the product. `SCOPE_FIREWALL.md` is a
product artifact, not a planning artifact.
