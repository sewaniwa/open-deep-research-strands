# Contributing to Open Deep Research Strands

Thank you for your interest in contributing to Open Deep Research Strands! This guide will help you get started with contributing to our multi-agent research system.

## 🎯 Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Contributing Guidelines](#contributing-guidelines)
- [Pull Request Process](#pull-request-process)
- [Issue Guidelines](#issue-guidelines)
- [Code Style](#code-style)
- [Testing](#testing)
- [Documentation](#documentation)

## Code of Conduct

This project and everyone participating in it is governed by our Code of Conduct. By participating, you are expected to uphold this code. Please report unacceptable behavior to the project maintainers.

## Getting Started

### Ways to Contribute

- **Bug Reports**: Help us identify and fix issues
- **Feature Requests**: Suggest new features or improvements
- **Code Contributions**: Implement new features or fix bugs
- **Documentation**: Improve our documentation
- **Testing**: Help us improve test coverage
- **Performance**: Optimize system performance

### What We're Looking For

- Implementation of core agent functionality
- Improvements to the A2A communication system
- Enhanced quality control mechanisms
- Performance optimizations
- Better test coverage
- Documentation improvements

## Development Setup

### Prerequisites

- Python 3.8 or higher
- Git
- Virtual environment tools (venv, conda, etc.)
- API keys for LLM providers (for testing)

### Local Development Environment

1. **Fork and Clone**
   ```bash
   git fork https://github.com/yourusername/open-deep-research-strands.git
   git clone https://github.com/yourusername/open-deep-research-strands.git
   cd open-deep-research-strands
   ```

2. **Set up Virtual Environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   pip install -r open_deep_research_strands/requirements.txt
   ```

4. **Set up Configuration**
   ```bash
   cp open_deep_research_strands/configs/local_config.py.example open_deep_research_strands/configs/local_config.py
   # Edit configuration with your settings
   ```

5. **Validate Setup**
   ```bash
   python open_deep_research_strands/scripts/validate_setup.py
   ```

### Development Workflow

1. Create a new branch for your feature/fix
2. Make your changes
3. Add/update tests
4. Run the test suite
5. Update documentation if needed
6. Submit a pull request

## Contributing Guidelines

### Branch Naming Convention

- `feature/description` - for new features
- `fix/description` - for bug fixes
- `docs/description` - for documentation changes
- `test/description` - for test improvements
- `refactor/description` - for code refactoring

### Commit Message Format

We follow the [Conventional Commits](https://www.conventionalcommits.org/) specification:

```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

Types:
- `feat`: new feature
- `fix`: bug fix
- `docs`: documentation changes
- `style`: code style changes
- `refactor`: code refactoring
- `test`: test additions/modifications
- `chore`: maintenance tasks

Examples:
```
feat(agents): implement supervisor agent control loop
fix(communication): resolve A2A message routing issue
docs(readme): add installation instructions
test(integration): add end-to-end workflow tests
```

## Pull Request Process

### Before Submitting

1. **Code Quality**
   - Ensure your code follows our style guidelines
   - Add docstrings to new functions and classes
   - Include type hints where appropriate

2. **Testing**
   - Add tests for new functionality
   - Ensure all existing tests pass
   - Aim for good test coverage

3. **Documentation**
   - Update relevant documentation
   - Add docstrings to new code
   - Update README if needed

### PR Checklist

- [ ] My code follows the project's style guidelines
- [ ] I have performed a self-review of my code
- [ ] I have commented my code, particularly in hard-to-understand areas
- [ ] I have made corresponding changes to the documentation
- [ ] My changes generate no new warnings
- [ ] I have added tests that prove my fix is effective or that my feature works
- [ ] New and existing unit tests pass locally with my changes
- [ ] Any dependent changes have been merged and published

### PR Description Template

```markdown
## Description
Brief description of the changes

## Type of Change
- [ ] Bug fix (non-breaking change which fixes an issue)
- [ ] New feature (non-breaking change which adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] Documentation update

## Testing
- [ ] Added new tests
- [ ] Updated existing tests
- [ ] All tests pass

## Screenshots (if applicable)

## Additional Notes
```

## Issue Guidelines

### Bug Reports

When reporting bugs, please include:

- **Environment**: OS, Python version, dependency versions
- **Expected Behavior**: What you expected to happen
- **Actual Behavior**: What actually happened
- **Steps to Reproduce**: Minimal steps to reproduce the issue
- **Error Messages**: Full error messages and stack traces
- **Code Samples**: Minimal code that reproduces the issue

### Feature Requests

When requesting features, please include:

- **Problem Statement**: What problem does this solve?
- **Proposed Solution**: How should this work?
- **Alternatives**: What alternatives have you considered?
- **Implementation**: Any ideas on implementation approach?

## Code Style

### Python Style Guide

We follow [PEP 8](https://pep8.org/) with some modifications:

- **Line Length**: 100 characters maximum
- **Imports**: Use absolute imports, group by standard/third-party/local
- **Naming**: 
  - Functions and variables: `snake_case`
  - Classes: `PascalCase`
  - Constants: `UPPER_SNAKE_CASE`
  - Private attributes: `_leading_underscore`

### Type Hints

Use type hints for all public functions and class methods:

```python
from typing import List, Dict, Optional, Union

async def process_research_results(
    results: List[Dict[str, Any]], 
    quality_threshold: float = 0.8
) -> Optional[Dict[str, Any]]:
    """Process research results with quality filtering."""
    pass
```

### Docstrings

Use Google-style docstrings:

```python
def analyze_research_quality(results: Dict[str, Any]) -> float:
    """Analyze the quality of research results.
    
    Args:
        results: Dictionary containing research findings and metadata.
        
    Returns:
        Quality score between 0.0 and 1.0.
        
    Raises:
        ValueError: If results format is invalid.
    """
    pass
```

## Testing

### Test Structure

- **Unit Tests**: Test individual functions and classes
- **Integration Tests**: Test component interactions
- **End-to-End Tests**: Test complete workflows

### Running Tests

```bash
# Run all tests
python -m pytest open_deep_research_strands/tests/

# Run with coverage
python -m pytest --cov=open_deep_research_strands open_deep_research_strands/tests/

# Run specific test categories
python -m pytest open_deep_research_strands/tests/test_agents.py
python -m pytest open_deep_research_strands/tests/test_integration.py
```

### Test Guidelines

- Write tests for all new functionality
- Aim for high test coverage (>80%)
- Use descriptive test names
- Include both positive and negative test cases
- Mock external dependencies appropriately

### Test Example

```python
import pytest
from unittest.mock import AsyncMock, MagicMock
from open_deep_research_strands.src.agents.supervisor_agent import SupervisorAgent

class TestSupervisorAgent:
    @pytest.fixture
    async def supervisor(self):
        """Create a supervisor agent for testing."""
        return SupervisorAgent()
    
    @pytest.mark.asyncio
    async def test_execute_control_loop_success(self, supervisor):
        """Test successful execution of control loop."""
        # Arrange
        query = "Test research query"
        
        # Act
        result = await supervisor.execute_control_loop(query)
        
        # Assert
        assert result is not None
        assert "report" in result
```

## Documentation

### Documentation Types

- **API Documentation**: Docstrings for all public interfaces
- **User Guides**: How-to guides for common tasks
- **Developer Guides**: Technical implementation details
- **Examples**: Working code examples

### Documentation Standards

- Write clear, concise documentation
- Include code examples where appropriate
- Keep documentation up-to-date with code changes
- Use proper Markdown formatting

## Release Process

### Version Numbering

We use [Semantic Versioning](https://semver.org/):

- **MAJOR**: Incompatible API changes
- **MINOR**: New functionality in a backwards compatible manner
- **PATCH**: Backwards compatible bug fixes

### Release Checklist

- [ ] Update version numbers
- [ ] Update CHANGELOG.md
- [ ] Run full test suite
- [ ] Update documentation
- [ ] Create release tag
- [ ] Publish release notes

## Questions and Support

- **General Questions**: Use [GitHub Discussions](https://github.com/yourusername/open-deep-research-strands/discussions)
- **Bug Reports**: Use [GitHub Issues](https://github.com/yourusername/open-deep-research-strands/issues)
- **Security Issues**: Email maintainers privately

## Recognition

Contributors will be recognized in:
- CHANGELOG.md for their contributions
- README.md in the acknowledgments section
- GitHub contributors page

Thank you for contributing to Open Deep Research Strands! 🚀