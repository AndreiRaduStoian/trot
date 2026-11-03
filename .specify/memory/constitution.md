<!--
Sync Impact Report
Version change: 0.0.0 -> 1.0.0
Modified principles: new constitution baseline for the Trot project
Added sections: Core Principles, Additional Constraints, Development Workflow
Removed sections: none
Follow-up TODOs: RATIFICATION_DATE
-->

# Trot Constitution

## Core Principles

### I. Data Integrity and Evidence First
All market data, indicators, and strategy assumptions must be sourced from explicit inputs and validated before they influence execution or reporting. Rejected or missing data must never be silently converted into a valid signal. Every major calculation must retain its provenance, assumptions, and failure path so an operator can reconstruct the decision trail.

This project works with live market information and financial decisions. Silent data loss, implicit defaults, and undocumented assumptions create direct operational and trust risk.

### II. Risk Controls Are Non-Negotiable
Any trading logic, execution path, or configuration change must define clear loss limits, position caps, and kill-switch behavior before it is used in a live or simulated environment. Trade sizing, exposure, and failure handling must be explicit and reviewable.

The system must fail safe, not fast, when volatility, stale data, or unexpected conditions appear. Risk controls are the difference between disciplined automation and uncontrolled loss.

### III. Test-First and Reproducible Validation
New behavior must be specified by an executable failing check or deterministic fixture before implementation. Data pipelines, signal logic, and execution changes must be reproducible in CI and must not rely on ad hoc local state.

This project depends on complex, time-sensitive logic; reproducibility is required to separate real signals from brittle assumptions and accidental drift.

### IV. Explainability and Observability
Every decision path must produce enough evidence to explain why a signal, trade, or alert was generated. Logs, metrics, and state snapshots must capture the inputs, intermediate calculations, and final action for each significant event.

When the system fails or behaves unexpectedly, the code alone is not enough. Operators must be able to verify the reasoning behind the decision in a clear and auditable form.

### V. Simplicity and Conservative Defaults
Prefer straightforward, well-named implementations over clever abstractions. Default behavior must be conservative, transparent, and easy to audit; complex logic requires explicit justification and stronger review standards.

In a trading context, unnecessary complexity multiplies failure modes. A simpler design with clear defaults is more robust and easier to trust under stress.

## Additional Constraints

Trot operates as a Python-based trading and market-data project. The project must keep the runtime environment reproducible, with explicit dependency management and a clear minimum supported Python version. Secrets, API keys, and broker credentials must remain outside version control and be loaded via secure environment variables or equivalent approved mechanisms.

No live trading or production execution may proceed without a documented dry-run or approval path. All external integrations must be isolated, monitored, and reviewed for failure modes. Dependency upgrades must be deliberate, and any use of third-party exchange or market-data libraries must be justified by the operational requirement.

## Development Workflow

Changes to Trot must follow a reviewable workflow: define the requirement, create or update the failing test or deterministic verification, implement the smallest safe change, and validate the result in the project environment. Behavioral changes that affect data sourcing, risk thresholds, or execution flow require explicit documentation and review before merge.

Production changes must include a rollback or disable plan, a summary of the affected risk assumptions, and a clear note about any new operational dependencies. Pull requests must confirm compliance with this constitution and identify which principles are affected by the change.

## Governance

This constitution governs all project decisions that affect trading logic, data handling, execution safety, and operational standards. It supersedes informal practices that conflict with its rules. Amendments require a documented rationale, review from the responsible maintainer or reviewers, and a clear migration note for any affected workflows.

Versioning follows Semantic Versioning. A MAJOR version change is required for backward-incompatible principle or governance changes. A MINOR change is required for a new principle or materially expanded guidance. A PATCH change is used for clarifications, wording fixes, and non-semantic refinements.

Compliance review is mandatory for any change that affects rules in this constitution. Reviewers must confirm that the proposal preserves data integrity, operational safety, and explainability. Exceptions must be documented, time-bounded, and approved explicitly rather than tolerated by default.

**Version**: 1.0.0 | **Ratified**: TODO(RATIFICATION_DATE): confirm the original adoption date for this constitution | **Last Amended**: 2026-11-03
