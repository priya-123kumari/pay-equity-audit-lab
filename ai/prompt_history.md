### 1. Purpose

I used AI tools such as Claude, Claude Code, and ChatGPT to support the development of Pay Equity Audit Lab.

AI assistance was mainly used for understanding requirements, planning the architecture, developing business logic, handling exceptions, debugging, and testing. AI-generated code was run and tested before use.

**AI tools used:**

- Claude (Anthropic), claude.ai chat.
- Claude Code, in VS Code: Tailwind redesign of the React dashboard and project clean-up.
- ChatGPT: general support during development.

Prompts are in my original wording. Terminal pastes are summarised in [brackets]. AI responses are not included (optional). Prompt 01 uses "Compensation Equity Analyzer", an earlier name for this project.

### 2. Requirement Analysis and Planning 

**Prompt 01 – Requirement Understanding**

Help me understand the Compensation Equity Analyzer requirements. Identify the main entities, business rules, workflows, exceptions, and expected results before starting development.

**Prompt 02 – Technical Architecture**

Suggest a suitable project structure using React, Python, Pandas, NumPy, and SQLite. Explain how the frontend, backend, database, and data processing modules should work together.

### 3. Business Logic and Implementation 
**Prompt 03 – Compensation Normalization**

Help implement salary normalization for different currencies, salary periods, and employee FTE values. Handle missing information through proper exceptions.

**Prompt 04 – Compensation Metrics**

Help calculate compa-ratio and range position using compensation band minimum, midpoint, and maximum values. Include proper validation for missing or invalid data.

**Prompt 05 – Employee Comparison**

Develop logic to compare employees based on role, level, location, experience, and documented job-related factors.

**Prompt 06 – Disparity Detection**

Help identify potentially unexplained salary differences using business rules and statistical analysis. Each flagged case should include its reason and supporting evidence.

**Prompt 07 – Exception Handling**

Identify and handle cases such as expired salary bands, missing currency rates, incorrect FTE values, and unapproved adjustments.

### 4. Database and Data Generation 

**Prompt 08 – Synthetic Data Generation**

Create realistic employee records, salary history, compensation bands, promotions, and adjustment records using Python. Keep the generated data consistent and reproducible.

**Prompt 09 – Database Validation**

Check database relationships, duplicate records, foreign keys, salary calculations, and data consistency.

### 5. Testing and Debugging 

**Prompt 10 – Functional Testing**

Create test cases covering salary calculations, employee comparisons, disparity detection, adjustment approvals, and exception handling.

**Prompt 11 – Code Review and Debugging**

Review the existing code, identify errors, explain their causes, and suggest the smallest reliable fixes without changing unrelated functionality.

**Prompt 12 – Final Project Validation**

Review the complete application against the original requirements. Identify missing functionality, test results, and areas that need improvement.


### 9. Development Approach

- Used AI to understand requirements, plan the project and solve technical problems.
- Ran and tested AI-generated code before using it.
- Kept business logic separate from other modules.
- Focused on accurate calculations and proper exception handling.
- Maintained data consistency and audit history.
- Tested the application against the expected requirements.

### 10. Important Note

AI wrote almost all of the backend code, tests, documentation and the dashboards (React + JavaScript, plus an earlier offline HTML version that has since been removed). I gave the direction, ran and verified the results on my own machine, and own the submission. This matches `AI_USAGE.md`.

### 11. Why FastAPI Is Not Used

FastAPI is not needed to build this project, so I did not use it.

- The Python generator runs from the command line and writes its results as CSV, JSON and SQL files.
- The React dashboard loads those generated files directly with `fetch`, so it does not call a backend API.
- The dashboard only reads the data. It has no logins and does not save changes, so there is nothing for an API to handle.
- Leaving out a backend server keeps the project simpler to run and check: the core needs only Python, and the dashboard needs only Node.js.

FastAPI would be useful if the app later needs live queries, user logins or saving approval decisions.