# Project Governance

## Development Model

AquaSense was developed using a branch-based collaborative workflow.

## Core Branches

| Branch | Purpose |
|---|---|
| `main` | Production-ready stable code |
| `dev` | Integration branch for tested features |
| `feature-*` | Individual contribution branches |

## Release Process

1. Feature branches merge into `dev`.
2. `dev` is tested locally.
3. Frontend and backend production URLs are verified.
4. `dev` is merged into `main`.
5. Render deploys backend from `main`.
6. Firebase frontend is manually deployed from the latest build.
7. GitHub release tag is created.

## Suggested Tags

```text
v1.0.0-production-demo
v1.1.0-docs-refresh
v1.2.0-hardware-demo
```
