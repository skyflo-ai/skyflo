# Contributing to Skyflo.ai

Thank you for considering contributing to Skyflo.ai! This document provides guidelines for contributing to the project.

By participating, you agree to abide by our [Code of Conduct](CODE_OF_CONDUCT.md).

## Quick Start

1. **Find an Issue**: Browse [issues](https://github.com/skyflo-ai/skyflo/issues) or [create one](https://github.com/skyflo-ai/skyflo/issues/new/choose)
2. **Fork & Clone**: Fork the repository and clone it locally
3. **Setup**: Install dependencies and configure development environment
4. **Create Branch**: Use `feature/issue-number-description` or `fix/issue-number-description`
5. **Make Changes**: Follow our coding standards and add tests
6. **Submit PR**: Create a pull request with a clear description of changes

## Development Environment

### Prerequisites

- Python 3.9+
- Node.js 18+ (frontend)
- Go 1.19+ (specific components)
- Docker and Docker Compose
- Kubernetes cluster (testing)
- AWS account (testing)

### Setup

```bash
# Python repositories
make setup-dev

# Frontend repositories
yarn install
```

### Testing

```bash
# Python components
make test

# Frontend repositories
yarn test
```

## Coding Standards

- **Python**: [PEP 8](https://www.python.org/dev/peps/pep-0008/), type hints, docstrings
- **JavaScript/TypeScript**: [Airbnb Style Guide](https://github.com/airbnb/javascript), TypeScript for type safety
- **Go**: [Go Code Review Comments](https://github.com/golang/go/wiki/CodeReviewComments)
- **Documentation**: Markdown, clear language, code examples
- **Commits**: [Conventional Commits](https://www.conventionalcommits.org/) format

## Pull Request Process

1. Fill out the PR template
2. Link to related issues
3. Ensure CI checks pass
4. Address review feedback
5. Await approval from maintainer

### PR Checklist

- [ ] Code follows style guidelines
- [ ] Tests for new features/fixes
- [ ] Documentation updates
- [ ] Changelog entry (significant changes)
- [ ] Signed-off commits (`git commit -s`)

## Testing Guidelines

- Write tests for new features and bug fixes
- Include unit, integration, and end-to-end tests as appropriate
- Mock external dependencies
- Ensure tests are deterministic and fast

## License

Contributions are licensed under the repository-specific license:

- UI, Crawlers, Main Repository: Apache License 2.0
- Core Engine, API: Business Source License 1.1 (converts to Apache 2.0 after 4 years)

## Community

Join our community channels:

- [Discord Server](https://discord.gg/kCFNavMund)
- [GitHub Discussions](https://github.com/skyflo-ai/skyflo/discussions)
- [Twitter/X](https://x.com/skyflo_ai)

---

Thank you for contributing to Skyflo.ai! Your efforts help make cloud infrastructure management accessible through AI. 