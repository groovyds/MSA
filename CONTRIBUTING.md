# Contributing to Marketing Strategist AI

Thank you for your interest in contributing to Marketing Strategist AI! This document provides guidelines and instructions for contributing to the project.

## Code of Conduct

By participating in this project, you agree to abide by our Code of Conduct. Please be respectful and considerate of others.

## How to Contribute

### 1. Reporting Bugs

- Use the GitHub issue tracker to report bugs
- Include a clear title and description
- Provide steps to reproduce the issue
- Include relevant logs or screenshots
- Specify your environment (OS, Python/Node versions, etc.)

### 2. Suggesting Features

- Use the GitHub issue tracker to suggest features
- Clearly describe the feature and its benefits
- Provide use cases and examples
- Consider potential implementation approaches

### 3. Pull Requests

1. Fork the repository
2. Create a new branch for your feature/fix:
   ```bash
   git checkout -b feature/your-feature-name
   ```
3. Make your changes
4. Write or update tests as needed
5. Ensure all tests pass
6. Update documentation if necessary
7. Submit a pull request

### Development Setup

1. Set up the development environment as described in the README
2. Install pre-commit hooks:
   ```bash
   # Backend
   cd backend
   pre-commit install

   # Frontend
   cd frontend
   npm install
   ```

### Code Style

#### Backend (Python)
- Follow PEP 8 style guide
- Use type hints
- Document functions and classes
- Write unit tests for new features
- Use pre-commit hooks for formatting

#### Frontend (TypeScript/React)
- Follow ESLint rules
- Use TypeScript for type safety
- Follow React best practices
- Write unit tests for components
- Use Prettier for formatting

### Testing

- Write unit tests for new features
- Ensure all tests pass before submitting PR
- Update tests when modifying existing features

### Documentation

- Update README.md for major changes
- Document new API endpoints
- Add comments for complex logic
- Update inline documentation

### Commit Messages

- Use clear, descriptive commit messages
- Reference issues in commit messages
- Follow conventional commit format:
  ```
  feat: add new feature
  fix: fix bug
  docs: update documentation
  style: format code
  refactor: refactor code
  test: add tests
  chore: update dependencies
  ```

### Review Process

1. PR will be reviewed by maintainers
2. Address any feedback or requested changes
3. PR will be merged once approved

## Getting Help

- Open an issue for questions
- Check existing documentation

## Thank You!

Your contributions help make Marketing Strategist AI better for everyone. Thank you for your time and effort! 