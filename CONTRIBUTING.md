# Contributing to AquaSense

Thank you for contributing to AquaSense. This project was developed as a collaborative Software Development Group Project, so clean collaboration matters as much as working code.

## Branching Strategy

Use the following branch structure:

```text
main                         Production-ready branch
dev                          Integration branch
feature-ishan-20232686       IoT / firmware / integration work
feature-lathmi-20232796      Backend / database / analytics work
feature-ewmini-20240017      Flutter UI / auth screens / settings work
feature-kulith-20232529      Authentication and security work
feature-sahan-20240820       Dashboard UI / dynamic rendering work
feature-rashan-20231987      Reports / services / support modules
```

## Workflow

1. Pull latest `dev`.
2. Create or switch to your feature branch.
3. Make small, meaningful commits.
4. Test locally.
5. Open a pull request into `dev`.
6. After review, merge `dev` into `main` for production.

## Commit Message Style

Use clear messages:

```text
feat(auth): add OTP verification flow
fix(api): correct CORS production origin
docs(readme): update deployment guide
refactor(mqtt): simplify reconnect logic
test(frontend): add login validation tests
```

## Pull Request Checklist

- [ ] Code builds successfully
- [ ] No secrets committed
- [ ] API URLs are production-safe
- [ ] Screenshots added for UI changes
- [ ] Docs updated if feature behavior changed
- [ ] Tested locally
- [ ] Linked issue or task if applicable

## Code Review Rules

- Do not merge your own PR without review.
- Keep pull requests small and focused.
- Resolve conflicts locally before merging.
- Never force-push to `main` unless the team agrees.

## Secret Management

Do not commit `.env`, service keys, passwords, or Firebase private files. Use `.env.example` for safe configuration references.
