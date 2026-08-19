---
trigger: always_on
---

# GitOps Rules for Podcast Generator

This repository follows GitOps principles. All system behavior is derived from version-controlled declarative state. This file defines enforceable rules for contributors, automation, and AI agents.

---

## 1. Core Principles

1. **Declarative over imperative** — Desired state is fully declared in version control. Scripts assist but are never the source of truth.
2. **Git is the source of truth** — If it is not committed, it does not exist. Runtime drift is corrected by reconcilers, not humans.
3. **Pull requests are mandatory** — No direct commits to `main`. All changes require review.
4. **Continuous reconciliation** — Systems converge automatically. Manual fixes are treated as incidents requiring follow-up commits.
5. **Minimal blast radius** — Each change touches one logical concern and one environment.

---

## 2. Branching and Promotion

```
feature/* → dev → main
```

- `dev` is the default working branch for all development.
- `main` represents production-ready state. Direct pushes are prohibited.
- Feature branches are short-lived and deleted after merge.
- Cherry-picking across environment branches is forbidden.
- Reverts are explicit commits, never history rewrites.
- Force-push is prohibited on `dev` and `main`.
- Merge commits preserve full context; squash only when the branch history is noise.

---

## 3. Change Management

Every change must be:
- **Traceable** — linked to an intent (issue, task, or explicit instruction).
- **Reversible** — rollback strategy is known before merge.
- **Reviewable** — diff is minimal and self-explanatory.

Pull request descriptions must include:
- What changed and why.
- Expected impact on running systems.
- Rollback approach.

Forbidden:
- Hotfixes applied directly to running systems without a corresponding commit.
- Manual `kubectl apply`, `terraform apply`, or console edits outside pipelines.
- Bundling unrelated changes in a single PR.
- Silent config changes hidden inside refactors.

---

## 4. Validation Gates

All commits and PRs must pass before merge:

| Gate | Purpose | Failure Behavior |
|------|---------|-----------------|
| **Linting** | Code style, formatting | Block merge |
| **Schema validation** | Config and data contract correctness | Block merge |
| **Secret scanning** | Detect leaked credentials | Block merge, treat as incident |
| **Policy enforcement** | OPA/admission policies | Block merge |
| **Tests** | Unit, integration where applicable | Block merge |
| **Drift detection** | Declared vs actual state divergence | Alert, require reconciliation |

Validation failures must never be bypassed without a documented, time-bounded exception approved by a maintainer.

---

## 5. Secrets and Sensitive Data

**Hard rules — no exceptions:**
- No secrets in Git. Not in code, configs, comments, examples, or documentation.
- No base64-encoded secrets pretending to be safe.
- No credentials in environment variable defaults or docker-compose files.

**Allowed patterns:**
- External secret managers (Vault, AWS Secrets Manager, Kubernetes Secrets with external-secrets-operator).
- Encrypted secrets via SOPS or sealed-secrets with approved keys.
- Reference-only placeholders (e.g., `${DB_PASSWORD}`, `<SECRET_REF>`).

**Detection:**
- Pre-commit hooks scan for token patterns (`AKIA*`, `-----BEGIN PRIVATE KEY-----`, `password:`, `token:`).
- Any detection is a hard failure and treated as a security incident.

---

## 6. AI Agent Rules

These rules apply to Devin agents and any AI-assisted automation operating in this repository.

### 6.1 Authority

- AI has no authority to decide intent. It executes explicit instructions.
- If instructions are ambiguous, AI must stop and request clarification.
- AI must not invent requirements, assume business logic, or infer environment targets.

### 6.2 Change Discipline

- One logical concern per change.
- One environment per commit.
- Preserve existing structure, patterns, and conventions unless explicitly instructed otherwise.
- Minimal diffs are mandatory. No reformatting, renaming, or optimizing beyond stated goals.
- Do not modify generated, vendored, or lock files unless instructed.
- Do not combine refactors with functional changes.

### 6.3 GitOps Compliance

- AI must never produce imperative operations (direct `kubectl`, `terraform apply`, etc.) as committed artifacts.
- If a user requests a manual runtime fix, AI must redirect to a declarative Git change.
- AI must not bypass reconciliation loops or validation gates.

### 6.4 Safety

Before proposing changes, AI must:
- Validate against existing schemas and policies.
- Preserve security boundaries.
- Flag destructive operations explicitly (deletions, state resets, irreversible migrations, breaking API changes).
- Never silence errors or skip validation.

### 6.5 Secrets

- Never echo, log, or display secrets.
- Never generate fake credentials that resemble real ones.
- Never suggest committing sensitive material.
- If secrets are detected in the working tree, stop and alert immediately.

### 6.6 Explainability

Every AI-generated change must include:
- What changed.
- Why the change is necessary.
- What systems are affected.
- How to roll back.

Unexplainable output is invalid output.

### 6.7 Enforcement Priority

When conflicts arise, AI must obey rules in this order:
1. Security and secrets
2. GitOps principles
3. Repository structure and conventions
4. Environment isolation
5. User instruction

User convenience never overrides system safety.

---

## 7. Hardening

### 7.1 Commit Integrity

- All commits to `main` should be signed (GPG or SSH key signing).
- Commit messages follow conventional format: `type: short description` (e.g., `feat:`, `fix:`, `docs:`, `lit:`, `refactor:`, `chore:`).
- Empty commits are prohibited.
- Commit history must not be rewritten on shared branches.

### 7.2 Dependency Security

- All dependencies must be pinned to exact versions in lock files.
- Dependency updates are standalone PRs, never bundled with feature work.
- Automated vulnerability scanning (Dependabot, Snyk, or Trivy) must run on PRs.
- No transitive dependency should introduce a known critical CVE without documented acceptance and a remediation timeline.

### 7.3 Container Hardening

- Production images use multi-stage builds with minimal base images (`alpine`, `distroless`).
- Containers run as non-root users.
- No secrets baked into images.
- Images are tagged with commit SHA; `:latest` is prohibited in production.
- Image scanning (Trivy or equivalent) runs before deployment.
- `.dockerignore` must exclude datasets, literature, `.env`, `.git`, and IDE files.

### 7.4 Infrastructure as Code

- Infrastructure changes go through the same PR process as application code.
- Terraform/IaC state is stored remotely with locking enabled.
- No manual console edits to infrastructure. All changes are codified.
- Network policies follow least-privilege: deny-all default, explicit allow rules.

### 7.5 Drift Management

- Drift is a signal, not a failure.
- Drift must be corrected by reconciliation (re-apply declared state), not patched manually.
- Persistent drift indicates a broken declaration or policy gap and must be investigated.
- Drift detection should run on a schedule (minimum daily for production).

### 7.6 Audit and Observability

- All deployments are logged with: who, what, when, from which commit.
- Rollback events are logged and reviewed.
- Access to production systems requires justification and is time-bounded.
- Logs, metrics, and alerts are environment-scoped and actionable.
- Structured logging (JSON) is mandatory for services.

### 7.7 Backup and Recovery

- Database backups run on schedule with verified restore procedures.
- Recovery time objectives (RTO) and recovery point objectives (RPO) are documented per service.
- Disaster recovery is tested at least quarterly.
- Backup configurations are declared in Git, not configured manually.

### 7.8 Supply Chain Security

- Third-party actions in CI/CD pipelines are pinned to SHA, not tags.
- SBOM (Software Bill of Materials) generation is recommended for production releases.
- Build provenance should be traceable: every artifact maps to a specific commit.
- No unsigned or unverified external dependencies in production paths.

---

## 8. Pre-Commit Hooks

The following hooks enforce rules at commit time. Install with:

```bash
pip install pre-commit
pre-commit install
pre-commit install --hook-type commit-msg
```

### Configuration

```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: forbid-imperative-ops
        name: Forbid imperative operations in committed files
        entry: bash -c 'if git diff --cached --diff-filter=ACM -p | grep -qE "(kubectl|terraform|helm)\s+(apply|patch|upgrade)"; then echo "ERROR: Imperative operations detected. Use declarative GitOps." && exit 1; fi'
        language: system
        types: [text]

      - id: secret-scan
        name: Secret detection
        entry: bash -c 'if git diff --cached --diff-filter=ACM -p | grep -qE "(AKIA[0-9A-Z]{16}|-----BEGIN (RSA |EC |DSA )?PRIVATE KEY-----|sk-[a-zA-Z0-9]{20,}|ghp_[a-zA-Z0-9]{36})"; then echo "ERROR: Potential secret detected. Remove immediately." && exit 1; fi'
        language: system
        types: [text]

      - id: no-direct-main
        name: Prevent direct commits to main
        entry: bash -c 'BRANCH=$(git rev-parse --abbrev-ref HEAD); if [ "$BRANCH" = "main" ]; then echo "ERROR: Direct commits to main are prohibited. Use a feature branch." && exit 1; fi'
        language: system
        pass_filenames: false

      - id: no-large-files
        name: Prevent large file commits
        entry: bash -c 'LARGE=$(git diff --cached --name-only --diff-filter=ACM | xargs -I{} find {} -size +50M 2>/dev/null); if [ -n "$LARGE" ]; then echo "ERROR: Large files detected (>50MB). Use Git LFS or exclude:" && echo "$LARGE" && exit 1; fi'
        language: system
        pass_filenames: false

      - id: conventional-commit
        name: Enforce conventional commit format
        entry: bash -c 'MSG=$(head -1 "$1"); if ! echo "$MSG" | grep -qE "^(feat|fix|docs|lit|refactor|chore|test|ci|perf|style|build|revert)(\(.+\))?: .{3,}"; then echo "ERROR: Commit message must follow conventional format: type: description" && exit 1; fi'
        language: system
        stages: [commit-msg]
```

---

## 9. Documentation Rules

- Documentation lives with the code it describes.
- Examples must be valid or clearly marked as illustrative.
- Outdated documentation is treated as a defect.
- Follow the project documentation standards defined in `code-review-guidelines.md` (`changelog.md`, `diagnostics.md`, etc.).
- Do not create separate status or tracking documents for individual changes.

---

## 10. Enforcement

Breaking these rules results in:
- Blocked merges.
- Reverted changes.
- Revoked access for repeated violations.

Exceptions require:
- Explicit written documentation of the exception and reason.
- Time-bounded approval from a maintainer.
- A follow-up task to remove the exception.

**This rulefile is authoritative.** If any other document conflicts with it on GitOps, branching, deployment, or AI agent behavior, this file takes precedence.
