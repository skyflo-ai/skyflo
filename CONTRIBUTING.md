# Contributing to Skyflo.ai

Thank you for considering contributing to Skyflo.ai! This document provides guidelines for contributing to the project.

We are committed to providing a friendly, safe, and welcoming environment for all contributors. Please read and follow our [Code of Conduct](CODE_OF_CONDUCT.md).

We highly recommend reading our [Architecture Guide](ARCHITECTURE.md) if you'd like to contribute! The repo is not as intimidating as it first seems if you read the guide!

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
  - Include component scope in commit messages: `type(scope): message`
  - Use the following component scopes:
    - `ui`: Frontend components
    - `engine`: Engine components
    - `mcp`: MCP server components
    - `k8s`: Kubernetes controller components
    - `docs`: Documentation changes
    - `infra`: Infrastructure or build system changes
  - Example: `feat (mcp): add docker tools` or `fix (ui): resolve workflow visualizer overflow`

## Pull Request Process

1. Fill out the PR template
2. Link to related issues
3. Ensure CI checks pass
4. Address review feedback
5. Await approval from maintainer

## License

Skyflo.ai is fully open source and licensed under the [Apache License 2.0](LICENSE).

## Community

Join our community channels:

- [Discord Server](https://discord.gg/kCFNavMund)
- [GitHub Discussions](https://github.com/skyflo-ai/skyflo/discussions)
- [Twitter/X](https://x.com/skyflo_ai)

---

Thank you for contributing to Skyflo.ai! Your efforts help make cloud infrastructure management accessible through AI. 