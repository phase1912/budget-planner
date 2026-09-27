# ADR 0011: Source-available under the PolyForm Strict License

**Date:** 2026-09-27
**Status:** Accepted

## Context

The repository was published under the MIT License (#150), which lets anyone use, change
and sell the code. The author means to take the product commercial, yet the repository has
to stay public: it is a diploma project, reviewed as such, and it is shared as a portfolio
piece. Every commit so far is the author's own, so the author alone holds the copyright and
may relicense.

## Decision

From this change on, the project is licensed under the **PolyForm Strict License 1.0.0**,
its official text unmodified in `LICENSE`, with the required notice naming the author.

- Anyone may read the code and run it for a noncommercial purpose: personal study, research,
  evaluation. Educational institutions may use it whatever their funding, which covers the
  diploma review.
- Nobody may modify it, distribute it or build new works on it, even without charge.
- Commercial use needs a separate licence from the author.

PolyForm Noncommercial was considered and rejected: it permits distributing modified
versions for noncommercial purposes, which would allow a free clone of the product. Keeping
no licence at all ("all rights reserved") was rejected because it grants nobody, reviewers
included, the right even to run the code.

## Consequences

- The project is source-available, not open source; the README says so plainly.
- The MIT grant cannot be withdrawn from copies already taken. Commits before this change
  stay available under MIT to anyone who obtained them; the new terms cover this commit and
  everything after it.
- Outside contributions are accepted only by prior agreement, and a contributor agrees the
  author may license their work under any terms (CONTRIBUTING.md), so the author keeps the
  sole right to relicense.
- The licence covers the project's own code only. Dependencies keep their own licences,
  and any commercial release should check them — copyleft ones especially — at that point.
