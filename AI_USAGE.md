### 1. Purpose

This file explains how I used AI tools to build Pay Equity Audit Lab, what I checked myself, and what I can explain.

**AI tools used:**

- Claude (Anthropic), in the claude.ai chat: planning and first version of the project.
- Claude Code, in VS Code: Tailwind redesign of the React dashboard and project clean-up.
- ChatGPT: general support during development, as listed in the prompt history.

Prompts: [`ai/prompt_history.md`](ai/prompt_history.md).

### 2. Where AI Helped

- Turning the problem statement into a plan: entities, build order, validation list and repo layout.
- Understanding the requirements: main entities, business rules, workflows, exceptions and expected results.
- Business logic: salary normalization, compa-ratio and range position, employee comparison, disparity detection and exception handling.
- Synthetic data generation and database validation: relationships, duplicates, foreign keys, salary calculations and data consistency.
- Test cases, code review and a final check of the project against the requirements.
- Writing the first version of essentially all code: generator, schema, rules, validator, evaluation, export, tests, README and docs.
- Writing the React + JavaScript dashboard, including the current Tailwind design, and an earlier offline HTML dashboard that has since been removed.
- Debugging Windows-specific problems: UTF-8 file encoding, a bad manual edit and the PowerShell `fc` alias.

### 3. Where I Relied Heavily on AI


AI wrote the dashboard from my direction. I directed the redesign, ran it and checked the results. AI was also used for the other code, technical guidance, debugging and validation.


My contribution was the direction, running and verifying the result on my own machine, understanding the design, and owning the submission.

### 4. What I Reviewed and Validated

- Ran the project on my own Windows machine (Python 3.12): `python -m pytest -q` gave **18 passed**.
- Ran the generator for 200 and 5,000 employees: `validation=PASS`, 0 unexpected errors, every injected anomaly detected.
- Hit a `UnicodeEncodeError` when writing docs and an `IndentationError` from a manual edit. The fixes were to write all text files as UTF-8 and to replace the files rather than hand-edit them.
- Ran the same-seed reproducibility check: two runs, identical SHA-256 checksums.
- Directed the dashboard's redesign and cut it down to what a reviewer needs.
- Merged the docs and ignore rules into one README and one `.gitignore`.
- Tried a `frontend/` + `backend/` folder layout, then reverted it and kept `dashboard/` and `generator/`.
- Asked AI to audit the project for duplication and to check my prompt history against the real code.

### 5. What I Can Explain

- Why compensation bands are effective-dated.
- How pay is generated from documented factors.
- Compa-ratio and range-position formulas.
- Why ground truth is kept separate, and how labels come from rules.
- How the robust z-score flags unexplained gaps.
- The exception path.
- The approval lifecycle.
- How reproducibility is achieved: one seeded RNG, no wall-clock time, sorted output.

### 6. More Detail

See [`docs/DESIGN_DECISIONS.md`](docs/DESIGN_DECISIONS.md) for assumptions, trade-offs, testing approach and limitations.
