---
trigger: manual
---

# 🏗️ Devin Standard Project Structure & Architecture Ruleset

This ruleset defines the **official standards for organizing, structuring, and maintaining** software projects under the Devin ecosystem.  
It ensures **consistency, scalability, and clarity** across repositories and teams.

---

## 🌍 Core Principles

- **Separation of Concerns:** Code, configuration, documentation, and assets must reside in clearly distinct directories.  
- **Consistency:** Follow the same directory and naming conventions across all projects.  
- **Scalability:** Structure should support incremental growth without refactoring.  
- **Readability:** Anyone new should locate key modules within 1 minute of opening the repo.

---

## 🧭 Universal Directory Pattern

Each project **must follow this base layout**:

```
project-root/
├── src/           # Main application source
│   ├── components/  # Reusable UI/logic components
│   ├── services/    # Business logic, API handlers
│   ├── utils/       # Helper functions, constants
│   ├── models/      # Domain or data models
│   └── main/        # Entry points or executables
│
├── tests/         # Unit & integration tests
├── docs/          # Architecture, API, usage guides
├── config/        # Environment & build configs
├── scripts/       # Deployment & automation scripts
├── assets/        # Static files (images, fonts, etc.)
├── build/         # Generated or compiled output
└── README.md
```

**Rules:**
- Do not create unused or placeholder directories.  
- `/build`, `/dist`, `/target`, and dependency folders must be in `.gitignore`.  
- `/src` is mandatory for all application logic.

---

## 🧩 Project-Type Specific Additions

**Python Projects**
```
├── src/mypackage/
│   ├── __init__.py
│   ├── core/
│   ├── api/
│   └── utils/
├── tests/
├── requirements.txt
└── setup.py
```
- Include `__init__.py` in all Python package folders.
- Mirror source folder structure under `/tests`.

**JavaScript/Node.js Projects**
```
├── src/
│   ├── components/
│   ├── services/
│   ├── hooks/
│   ├── styles/
│   └── index.js
├── public/
└── package.json
```
- Keep static assets under `/public`.  
- Environment template files must be named `.env.example`.

**Java or .NET Projects**
Follow their native conventions (`/src/main/java/…`, `/src/main/resources/`, etc.).

---

## 🏗️ Advanced Architecture Patterns

### Feature-Based Structure
```
src/
├── features/
│   ├── auth/
│   ├── dashboard/
│   └── reports/
├── shared/
│   ├── components/
│   ├── hooks/
│   └── utils/
└── core/
    ├── api/
    └── routing/
```
✅ Use when your app has independent, modular features.  
🚫 Don’t mix unrelated logic under `/features`.

### Layered Architecture
```
src/
├── presentation/   # UI, controllers
├── application/    # Use-cases, DTOs
├── domain/         # Entities, business logic
└── infrastructure/ # External systems (DB, APIs, logs)
```
Use this pattern for large enterprise or DDD-style systems.

---

## 🧱 Directory Naming Rules

- Use **lowercase with hyphens** for folder names (`data-models`, `api-clients`).  
- Avoid ambiguous directories like `/misc`, `/helpers`, `/tmp`.  
- Group files that change together in one directory (principle of *locality of behavior*).  
- Maximum nesting: **3 levels deep**.

---

## 🧠 Code Ownership & Team Conventions

- Each major feature or module should have a **designated owner** in `OWNERS.md`.  
- Shared utilities must live under `/shared` or `/common`, not under feature folders.  
- Each project must include a short section in `README.md` describing:
  - Directory structure
  - Naming conventions
  - Build commands

---

## ⚙️ .gitignore Standards

Every repository must include:
```
# Dependencies
node_modules/
vendor/

# Build outputs
dist/
build/
target/
*.pyc
__pycache__/

# Environment files
.env
.env.local

# IDE & OS
.vscode/
.idea/
.DS_Store
Thumbs.db
```

---

## 🧰 Scaling Guidelines

- Start with a minimal structure; **add directories only when needed.**
- Refactor the structure when:
  - Files become hard to find
  - Multiple teams modify the same folders
  - Directories exceed 20 files

---

## 📘 Documentation Requirements

- Maintain `/docs` for:
  - Architecture diagrams  
  - API specs  
  - Developer guides  
  - Design decisions
- Always update documentation after structural or architectural changes.
- Include `CONTRIBUTING.md` describing rules, naming, and structure.

**Documentation Standards:**
  - Use Markdown for all documentation
  - Include code examples with syntax highlighting
  - Keep diagrams as code (Mermaid, PlantUML, XML, draw.io) when possible
  - Version documentation alongside code
  - Update docs in the same PR as code changes
  - You do not make new unneccessary document to show what changes you have done unless specifically asked to do so. Best is to update the existing document to show what changes you have done.
  - Development changes to be in changelog.md file and not in README.md file. Any error or bugfix can be in diagnostics.md file. Any new feature can be in feature.md file. Any new model can be in model.md file. Any new prompt can be in prompt.md file. Any new architecture can be in architecture.md file. These are all to be in the development folder in the docs folder. 
  - In case these documents are too big to read, you can split them into smaller documents like changelog-1.md, changelog-2.md and so on and read them. You can write them in same way if they are too big to read. But do not make multiple readme.md file in every folder.
  - **README.md naming rule (mandatory):** There must be exactly ONE `README.md` file per project, located at the project root. Any documentation file in a subdirectory that you might be tempted to name `README.md` must instead be named descriptively after the folder's purpose and topic, e.g. `trust-scenarios-overview.md`, `bsi-survey-app-guide.md`, `p12-survey-paper-details.md`. Use lowercase-hyphenated names that describe what the file covers. Never create `README.md` inside any subdirectory — only at the repository root.
  - The main Readme.md file should give the over view of the project and point to specific documents in docs folder which has the deeper details like installation, deployment, configurations, tests, errorhandling etc.
  - When citing anything from literature, always use <authorname> et al. <year> format. Know which documents are citable and which are not. There will be some articles that are from tools like perplexity or elicit and there are some documents that compile thoughts written by user. Remember that these are not citable.
---

## ✅ Review Checklist for Devin Projects

- [ ] Project follows base directory structure  
- [ ] `.gitignore` covers build, env, and dependency artifacts  
- [ ] No excessive nesting or ambiguous folder names  
- [ ] README explains structure and ownership  
- [ ] Documentation updated under `/docs`  
- [ ] Project build/test workflow validated  

---

### 🌊 Remember: “A clean structure is self-documenting — your project should explain itself without opening a single file.”