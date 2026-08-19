---
trigger: always_on
---

# 🌊 Devin Code Review Guidelines

These guidelines ensure code quality, maintainability, and consistency across the project.  
When reviewing or submitting code, use this as a checklist.

---

## 🏷️ Naming
- Use **clear, descriptive, and unambiguous** names for variables, functions, and classes.  
- Avoid single-letter identifiers, except for short-lived loop indices (`i`, `j`, `k`).  
- Follow the **project’s naming conventions** (e.g., `snake_case` for variables, `CamelCase` for classes).  
- Names should convey intent — prefer `calculate_wind_speed()` over `calc_ws()`.  
- Use consistent prefixes/suffixes for related concepts (e.g., `fetch_data()`, `process_data()`, `store_data()`).

---

## 🎨 Style & Formatting
- Keep lines **within 100–120 characters** for readability.  
- Use **consistent indentation** (spaces or tabs as defined by project settings).  
- Leave **blank lines** to separate logical sections of code.  
- Write comments for **non-trivial logic**, assumptions, or decisions.  
- Remove commented-out code before merging.  
- Ensure code is **linted and formatted** according to project rules (e.g., `black`, `eslint`, `prettier`).
- Systematically replace em-dashes (“—”) with a dot (”.”) to start a new sentence, or a comma (”,”) to continue the sentence. - You are an expert who double-checks things, you are skeptical, and you do thorough research. I am not always right. Neither are you, but we both strive for accuracy and the truth.
---

## 🧩 Structure & Design
- Keep functions and methods **short and focused** — each should do *one thing well*.  
- Avoid deep nesting; refactor complex conditions into helper functions.  
- Keep parameter lists short; use configuration objects if needed.  
- Group related logic into **modules or classes** to improve discoverability.  
- Respect **separation of concerns** — don’t mix data access, business logic, and presentation.  
- Favor **immutability** and **pure functions** where possible.

---

## ⚙️ Best Practices
- Eliminate **duplicate code** — use utilities or shared components.  
- Prefer **composition over inheritance** unless inheritance adds real clarity.  
- Write **defensive code**: check assumptions and handle edge cases gracefully.  
- Include **error handling and logging** where relevant.  
- Review performance implications for large data structures or loops.  
- Keep dependencies minimal and justified.  
- Ensure changes are **backward-compatible** where applicable.
- Always work on dev branch by default. Main branch is only for final push on production code. 

---

## 📚 Documentation

**CRITICAL RULE**: Do NOT create separate markdown files for every change or status update.

- Include concise **docstrings** or comments for all public functions, classes, and modules.  
- Update or create documentation when adding new features or APIs.  

**Use ONLY these two files for tracking changes**:
- `docs/changelog.md` - ALL new features, changes, deprecated items with timestamps
- `docs/diagnostics.md` - ALL bug fixes, issue resolutions, troubleshooting with timestamps

**Forbidden**:
- ❌ Do NOT create STATUS.md, IMPLEMENTATION_COMPLETE.md, or similar tracking documents
- ❌ Do NOT create separate documents explaining what was done
- ❌ Do NOT duplicate information across multiple files
- ✅ Instead: Update changelog.md or diagnostics.md with timestamped entries

**Required files** (and ONLY these):
- `README.md` - Project overview, quick start (ONE file at root)
- `CONTRIBUTING.md` - Contribution guidelines (ONE file at root)
- `docs/changelog.md` - All changes (append-only with timestamps)
- `docs/diagnostics.md` - All issues and fixes (append-only with timestamps)

**Documentation Standards:**
  - Use Markdown for all documentation
  - Include code examples with syntax highlighting
  - Keep diagrams as code (Mermaid, PlantUML, XML, draw.io) when possible
  - Version documentation alongside code
  - Update docs in the same PR as code changes
  - You do not make new unneccessary document to show what changes you have done unless specifically asked to do so. Best is to update the existing document to show what changes you have done.
  - Development changes to be in changelog.md file and not in README.md file. Any error or bugfix can be in diagnostics.md file. Any new feature can be in feature.md file. Any new model can be in model.md file. Any new prompt can be in prompt.md file. Any new architecture can be in architecture.md file. These are all to be in the development folder in the docs folder. 
  - In case these documents are too big to read, you can split them into smaller documents like changelog-1.md, changelog-2.md and so on and read them. You can write them in same way if they are too big to read. But do not make multiple readme.md file in every folder.
  - The main Readme.md file should give the over view of the project and point to specific documents in docs folder which has the deeper details like installation, deployment, configurations, tests, errorhandling etc.
  - When citing anything from literature, always use <authorname> et al. <year> format. Know which documents are citable and which are not. There will be some articles that are from tools like perplexity or elicit and there are some documents that compile thoughts written by user. Remember that these are not citable.

**When refactoring**:
- Do NOT remove `.devin` rules files
- Do not remove any existing documentations unless specifically directed.
- Keep module-specific README files in their directories with their specific purposes (e.g., `services/*/services-<purpose>.md`)
- Include **code examples** in docs where appropriate for clarity
---

## 🧰 Tools & Workflow
- Follow all **project-specific tooling**, linters, and formatting configurations.  
- Validate code with **CI checks** before submitting for review.  
- Commit changes in **small, atomic commits** with clear, imperative messages  
  (e.g., `Fix: handle null wind speed in parser`).  
- Rebase or squash before merging to maintain a clean history.  
- Always review **test coverage**; add or update unit/integration tests for new or changed code.  
- Use **pull requests (PRs)** for all changes — no direct pushes to main branches.

---

## 🧠 Review Mindset
- Be **constructive and respectful** — reviews are about improving code, not criticizing authors.  
- Ask clarifying questions when logic is unclear.  
- Suggest improvements with rationale, not mandates.  
- Prioritize **readability, maintainability, and correctness** over micro-optimizations.  
- Ensure all reviewers understand the **context** of changes before approval.

---

### ✅ Quick Reviewer Checklist
- [ ] Code is readable, consistent, and follows style conventions  
- [ ] No duplicate logic or unnecessary complexity  
- [ ] Tests exist and pass  
- [ ] Documentation and changelogs are updated  
- [ ] Commit messages are meaningful  
- [ ] Code integrates cleanly with the latest `main`