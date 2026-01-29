# Contributing to Skyflo.ai

Thank you for considering contributing to Skyflo.ai. This document outlines how to contribute effectively and what standards are expected.

We are committed to providing a friendly, safe, and welcoming environment for all contributors. Please read and follow our [Code of Conduct](CODE_OF_CONDUCT.md).

Before making changes, read the [Architecture Guide](docs/architecture.md). It explains the system layout and will save you time.

## Quick Start

1. **Find an Issue**: Browse existing issues or create a new one  
   https://github.com/skyflo-ai/skyflo/issues
2. **Fork & Clone**: Fork the repository and clone it locally
3. **Setup**: Install dependencies and configure your development environment
4. **Create a Branch**:  
   - `feature/<issue-number>-description`  
   - `fix/<issue-number>-description`
5. **Make Changes**: Follow coding standards and add tests where applicable
6. **Submit a PR**: Open a pull request with a clear description

## Coding Standards

- **Python**
  - PEP 8
  - Type hints required
  - Docstrings for public functions
- **JavaScript / TypeScript**
  - Airbnb Style Guide
  - TypeScript required
- **Go**
  - Go Code Review Comments
- **Documentation**
  - Markdown
  - Clear, concise language
  - Concrete examples
- **Commits**
  - Conventional Commits format: `type (scope): message`
  - Valid scopes: `ui`, `engine`, `mcp`, `k8s`, `docs`, `infra`
  - Use component scope only for single-component changes:
    - `feat (ui):` Frontend-only changes
    - `feat (engine):` Engine-only changes
    - `feat (mcp):` MCP server-only changes
    - `feat (k8s):` Kubernetes-only changes
    - `fix (docs):` Documentation-only changes
    - `chore (infra):` Infra or build changes
  - For multi-component or full-stack changes, omit the scope:
    - `feat: add analytics dashboard`
    - `fix: resolve auth flow issue`
  - **All PRs must be squashed to a single commit before merge**

## Pull Request Process

### Before Opening a PR

1. Code follows the standards above
2. Changes tested locally (Engine, MCP server, UI as applicable)
3. No debug output, console logs, or commented code
4. No regressions to existing behavior

### After Opening a PR

1. Fill out the PR template completely
2. Link related issue(s)
3. Ensure all CI checks pass

### Code Review Process

We use CodeRabbit for automated reviews.

1. **CodeRabbit Review**  
   CodeRabbit runs automatically on PR creation and updates.

2. **Resolve All CodeRabbit Comments**  
   All comments must be resolved before requesting maintainer review. This is mandatory.

3. **Request Maintainer Review**  
   After resolving CodeRabbit feedback, request review from @KaranJagtiani.

4. **Address Maintainer Feedback**  
   Apply all requested changes and re-request review.

5. **Squash Commits**  
   Squash to a single commit following Conventional Commits.

6. **Merge**  
   The maintainer merges approved PRs.

### Review Checklist

Before requesting maintainer review, confirm:

- [ ] All CodeRabbit comments resolved
- [ ] All CI checks passing
- [ ] No `package-lock.json` (UI uses `yarn`)
- [ ] No debug `print` or `console.log`
- [ ] No redundant or obvious comments
- [ ] TypeScript types match backend contracts
- [ ] Errors do not expose internal details

## License

Skyflo.ai is licensed under the Apache License 2.0.

By contributing, you agree that your contributions are licensed under Apache License 2.0.

## Trademarks

The Skyflo name and logos are trademarks and are **not** covered by the Apache License.  
See [TRADEMARKS.md](TRADEMARKS.md) for usage rules.

## Community

- [Discord](https://discord.gg/kCFNavMund)
- [GitHub Discussions](https://github.com/skyflo-ai/skyflo/discussions)
- [X](https://x.com/skyflo_ai)
