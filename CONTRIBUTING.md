# Contributing to kfix

Thank you for considering contributing to kfix! This document provides guidelines and instructions for contributing.

## Development Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/yourusername/kfix.git
   cd kfix
   ```

2. **Create a virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install development dependencies:**
   ```bash
   make install-dev
   # or
   pip install -e ".[dev]"
   ```

4. **Install pre-commit hooks:**
   ```bash
   pre-commit install
   ```

## Code Style

We use several tools to maintain code quality:

- **Black**: Code formatting (line length: 100)
- **isort**: Import sorting
- **Ruff**: Linting
- **mypy**: Type checking

### Running Code Quality Tools

```bash
# Format code
make format

# Run linter
make lint

# Type check
make type-check

# Run all checks
make all
```

### Code Style Guidelines

1. **Type Hints**: All functions must have type hints
   ```python
   def diagnose_pod(pod_name: str, namespace: str = "default") -> str:
       """Diagnose a pod issue."""
       pass
   ```

2. **Docstrings**: Use Google-style docstrings
   ```python
   def gather_diagnostics(resource: str) -> Dict[str, str]:
       """Gather diagnostic information for a resource.

       Args:
           resource: The name of the Kubernetes resource.

       Returns:
           A dictionary containing diagnostic data.

       Raises:
           KubectlError: If kubectl command fails.
       """
       pass
   ```

3. **Imports**: Organized by isort
   - Standard library
   - Third-party packages
   - Local imports

4. **Line Length**: Maximum 100 characters

## Testing

### Running Tests

```bash
# Run all tests
make test

# Run with coverage
make test-cov

# Run specific test file
pytest tests/test_kubectl.py

# Run specific test
pytest tests/test_kubectl.py::test_check_cluster_access
```

### Writing Tests

1. **Location**: Place tests in `tests/` directory
2. **Naming**: Test files must start with `test_`
3. **Structure**: Use pytest fixtures for setup
4. **Mocking**: Use `pytest-mock` for mocking external calls

Example:
```python
import pytest
from kfix.kubectl import Kubectl

def test_check_cluster_access(mocker):
    """Test cluster access check."""
    # Mock subprocess.run
    mocker.patch("subprocess.run", return_value=mocker.Mock(returncode=0))

    kubectl = Kubectl()
    assert kubectl.check_cluster_access() is True
```

## Pull Request Process

1. **Create a branch** for your feature/fix:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes** and commit:
   ```bash
   git add .
   git commit -m "Add feature: your feature description"
   ```

3. **Ensure all checks pass**:
   ```bash
   make all
   ```

4. **Push to your fork**:
   ```bash
   git push origin feature/your-feature-name
   ```

5. **Create a Pull Request** on GitHub

### PR Guidelines

- **Title**: Clear and descriptive
- **Description**: Explain what and why
- **Tests**: Include tests for new features
- **Documentation**: Update docs if needed
- **Commits**: Keep commits focused and well-described

## Adding New Features

### Adding a New Diagnose Command

1. **Update kubectl.py**: Add data gathering method
   ```python
   def gather_deployment_diagnostics(self, name: str, namespace: str) -> Dict[str, str]:
       """Gather deployment diagnostics."""
       return {
           "describe": self.describe_deployment(name, namespace),
           "events": self.get_deployment_events(name, namespace),
       }
   ```

2. **Update ai.py**: Add AI analysis method
   ```python
   def diagnose_deployment(self, name: str, diagnostics: Dict[str, str]) -> str:
       """Diagnose deployment issues."""
       # Implementation
   ```

3. **Update cli.py**: Add CLI command
   ```python
   @diagnose_app.command("deployment")
   def diagnose_deployment(name: str, namespace: str = "default"):
       """Diagnose a deployment issue."""
       # Implementation
   ```

4. **Add tests**: Create test cases
5. **Update documentation**: Add to README

## Project Structure

```
kfix/
├── kfix/              # Main package
│   ├── __init__.py    # Package info
│   ├── cli.py         # CLI interface
│   ├── kubectl.py     # Kubectl wrapper
│   ├── ai.py          # AI diagnostician
│   └── config.py      # Configuration
├── tests/             # Test suite
│   ├── test_cli.py
│   ├── test_kubectl.py
│   ├── test_ai.py
│   └── test_config.py
├── docs/              # Documentation
├── examples/          # Example manifests
├── Makefile           # Development commands
├── pyproject.toml     # Package configuration
└── README.md          # Main documentation
```

## Release Process

1. Update version in `kfix/__init__.py`
2. Update CHANGELOG.md
3. Create a git tag
4. Build and publish:
   ```bash
   make publish
   ```

## Getting Help

- **Issues**: GitHub Issues for bugs
- **Discussions**: GitHub Discussions for questions
- **Email**: Contact maintainers

## Code of Conduct

- Be respectful and inclusive
- Welcome newcomers
- Focus on constructive feedback
- Respect differing viewpoints

Thank you for contributing to kfix!
