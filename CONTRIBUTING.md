# Contributing to Skyflo.ai

Thank you for considering contributing to Skyflo.ai! This document provides guidelines for contributing to the project.

We are committed to providing a friendly, safe, and welcoming environment for all contributors. Please read and follow our [Code of Conduct](CODE_OF_CONDUCT.md).

We highly recommend reading our [Architecture Guide](docs/architecture.md) if you'd like to contribute! The repo is not as intimidating as it first seems if you read the guide!

## Quick Start

1. **Find an Issue**: Browse [issues](https://github.com/skyflo-ai/skyflo/issues) or [create one](https://github.com/skyflo-ai/skyflo/issues/new/choose)
2. **Fork & Clone**: Fork the repository and clone it locally
3. **Setup**: Install dependencies and configure development environment
4. **Create Branch**: Use `feature/issue-number-description` or `fix/issue-number-description`
5. **Make Changes**: Follow our coding standards and add tests
6. **Submit PR**: Create a pull request with a clear description of changes

## Coding Standards

- **Python**: [PEP 8](https://www.python.org/dev/peps/pep-0008/), type hints, docstrings
- **JavaScript/TypeScript**: [Airbnb Style Guide](https://github.com/airbnb/javascript), TypeScript for type safety
- **Go**: [Go Code Review Comments](https://github.com/golang/go/wiki/CodeReviewComments)
- **Documentation**: Markdown, clear language, code examples
- **Commits**: [Conventional Commits](https://www.conventionalcommits.org/) format
  - Use component scope only for single-component changes:
    - `feat (ui):` — Frontend-only changes
    - `feat (engine):` — Engine-only changes
    - `feat (mcp):` — MCP server-only changes
    - `feat (k8s):` — Kubernetes controller-only changes
    - `fix (docs):` — Documentation-only changes
    - `chore (infra):` — Infrastructure or build system changes
  - For full-stack changes spanning multiple components, omit the scope:
    - `feat: add analytics dashboard page`
    - `fix: resolve authentication flow issues`
  - Squash all commits into a single commit before merge

## Pull Request Process

### Before Opening a PR

1. Ensure your code follows the coding standards above
2. Test your changes locally (run the Engine, MCP server, and UI)
3. Remove debug statements, console logs, and commented-out code
4. Verify no regressions to existing functionality

### After Opening a PR

1. Fill out the PR template completely
2. Link to the related issue(s)
3. Ensure all CI checks pass

### Code Review Process

We use [CodeRabbit](https://coderabbit.ai/) for automated code reviews. The review process works as follows:

1. **CodeRabbit Review**: When you open or update a PR, CodeRabbit will automatically review your changes and post comments.

2. **Resolve All CodeRabbit Comments**: You must address and resolve **all** CodeRabbit comments before requesting a maintainer review. This is not optional. CodeRabbit catches common issues, style violations, and potential bugs that need to be fixed.

3. **Request Maintainer Review**: Only after all CodeRabbit comments are resolved should you request a review from the maintainer (@KaranJagtiani).

4. **Address Maintainer Feedback**: The maintainer may request additional changes. Address all feedback and re-request review.

5. **Squash Commits**: Before final approval, squash all your commits into a single commit with a clear message following the conventional commits format.

6. **Merge**: The maintainer will merge your PR once approved.

### Review Checklist

Before requesting maintainer review, verify:

- [ ] All CodeRabbit comments are resolved
- [ ] All CI checks pass
- [ ] No `package-lock.json` (we use `yarn` only for the UI)
- [ ] No debug `print` statements or `console.log` calls
- [ ] No redundant or self-explanatory comments
- [ ] TypeScript types match backend contracts
- [ ] Error handling does not expose internal details to users

## License

Skyflo.ai is fully open source and licensed under the [Apache License 2.0](LICENSE).

By contributing, you agree that your contributions will be licensed under the Apache License 2.0.

## Community

Join our community channels:

- [Discord Server](https://discord.gg/kCFNavMund)
- [GitHub Discussions](https://github.com/skyflo-ai/skyflo/discussions)
- [Twitter/X](https://x.com/skyflo_ai)

---

Thank you for contributing to Skyflo.ai! Your efforts help make cloud infrastructure management accessible through AI. 
