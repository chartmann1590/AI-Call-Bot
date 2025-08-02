# Contributing to AI Call Bot 🤝

Thank you for your interest in contributing to AI Call Bot! We welcome contributions from the community and appreciate your help in making this project better.

## 📋 Table of Contents

- [🤝 How to Contribute](#-how-to-contribute)
- [🐛 Reporting Bugs](#-reporting-bugs)
- [💡 Suggesting Enhancements](#-suggesting-enhancements)
- [🔧 Development Setup](#-development-setup)
- [📝 Code Style](#-code-style)
- [🧪 Testing](#-testing)
- [📚 Documentation](#-documentation)
- [🚀 Pull Request Process](#-pull-request-process)
- [📋 Issue Templates](#-issue-templates)
- [🏆 Recognition](#-recognition)

## 🤝 How to Contribute

### Types of Contributions

We welcome various types of contributions:

- **🐛 Bug Reports**: Help us identify and fix issues
- **💡 Feature Requests**: Suggest new features or improvements
- **🔧 Code Contributions**: Submit code fixes or new features
- **📚 Documentation**: Improve or add documentation
- **🧪 Testing**: Write tests or improve test coverage
- **🌐 Translations**: Help translate the interface
- **🎨 UI/UX**: Improve the user interface and experience

### Getting Started

1. **Fork the repository**
2. **Create a feature branch**: `git checkout -b feature/amazing-feature`
3. **Make your changes**
4. **Test your changes**
5. **Commit your changes**: `git commit -m 'Add amazing feature'`
6. **Push to the branch**: `git push origin feature/amazing-feature`
7. **Open a Pull Request**

## 🐛 Reporting Bugs

### Before Reporting

1. **Check existing issues**: Search for similar issues
2. **Test with latest version**: Ensure the bug exists in the latest release
3. **Reproduce the issue**: Create a minimal reproduction case

### Bug Report Template

```markdown
## Bug Description
Brief description of the bug

## Steps to Reproduce
1. Step 1
2. Step 2
3. Step 3

## Expected Behavior
What you expected to happen

## Actual Behavior
What actually happened

## Environment
- OS: [e.g., Windows 10, macOS 12.0, Ubuntu 20.04]
- Python Version: [e.g., 3.10.6]
- AI Call Bot Version: [e.g., 1.0.3]
- Ollama Version: [e.g., 0.1.0]

## Additional Information
- Screenshots (if applicable)
- Logs (if applicable)
- Configuration files (sanitized)
```

## 💡 Suggesting Enhancements

### Enhancement Request Template

```markdown
## Enhancement Description
Brief description of the enhancement

## Problem Statement
What problem does this solve?

## Proposed Solution
How would you like to see this implemented?

## Alternative Solutions
Any alternative approaches you've considered

## Additional Context
Any other relevant information
```

## 🔧 Development Setup

### Prerequisites

- Python 3.10+
- Git
- Ollama (for testing)
- Docker (optional)

### Local Development Setup

1. **Clone the repository**:
   ```bash
   git clone https://github.com/chartmann1590/AI-Call-Bot.git
   cd AI-Call-Bot
   ```

2. **Create virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: .\venv\Scripts\Activate.ps1
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   pip install -r requirements-dev.txt  # Development dependencies
   ```

4. **Set up environment**:
   ```bash
   cp env.example .env
   # Edit .env with your development settings
   ```

5. **Install pre-commit hooks**:
   ```bash
   pre-commit install
   ```

### Development Commands

```bash
# Run tests
make test

# Run linting
make lint

# Run type checking
make type-check

# Run the application
make run

# Run in debug mode
make run-debug

# Clean up
make clean
```

## 📝 Code Style

### Python Style Guide

We follow [PEP 8](https://www.python.org/dev/peps/pep-0008/) with some modifications:

- **Line length**: 88 characters (Black formatter)
- **Import sorting**: isort
- **Type hints**: Required for all functions
- **Docstrings**: Google style docstrings

### Code Formatting

We use automated tools for code formatting:

- **Black**: Code formatting
- **isort**: Import sorting
- **flake8**: Linting
- **mypy**: Type checking

### Pre-commit Hooks

The following hooks are automatically run on commit:

- **Black**: Code formatting
- **isort**: Import sorting
- **flake8**: Linting
- **mypy**: Type checking
- **bandit**: Security linting

### Example Code Style

```python
"""Module for handling audio processing operations."""

from typing import List, Optional, Tuple
import numpy as np
from dataclasses import dataclass

@dataclass
class AudioConfig:
    """Configuration for audio processing."""
    
    sample_rate: int = 16000
    frame_duration_ms: int = 30
    silence_threshold: float = 0.01

def process_audio(audio_data: np.ndarray, config: AudioConfig) -> np.ndarray:
    """Process audio data according to configuration.
    
    Args:
        audio_data: Input audio data as numpy array
        config: Audio processing configuration
        
    Returns:
        Processed audio data
        
    Raises:
        ValueError: If audio_data is empty or invalid
    """
    if audio_data.size == 0:
        raise ValueError("Audio data cannot be empty")
    
    # Process audio data
    processed_data = audio_data * config.silence_threshold
    
    return processed_data
```

## 🧪 Testing

### Running Tests

```bash
# Run all tests
make test

# Run specific test file
python -m pytest tests/test_audio_processor.py

# Run with coverage
make test-coverage

# Run integration tests
make test-integration
```

### Writing Tests

- **Unit tests**: Test individual functions and classes
- **Integration tests**: Test component interactions
- **End-to-end tests**: Test complete workflows

### Test Structure

```python
"""Tests for audio processing module."""

import pytest
import numpy as np
from src.audio_processor import AudioProcessor, AudioConfig

class TestAudioProcessor:
    """Test cases for AudioProcessor class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.config = AudioConfig()
        self.processor = AudioProcessor(self.config)
    
    def test_process_audio_valid_input(self):
        """Test audio processing with valid input."""
        # Arrange
        audio_data = np.array([0.1, 0.2, 0.3])
        
        # Act
        result = self.processor.process(audio_data)
        
        # Assert
        assert result is not None
        assert len(result) == len(audio_data)
    
    def test_process_audio_empty_input(self):
        """Test audio processing with empty input."""
        # Arrange
        audio_data = np.array([])
        
        # Act & Assert
        with pytest.raises(ValueError, match="Audio data cannot be empty"):
            self.processor.process(audio_data)
```

## 📚 Documentation

### Documentation Standards

- **Code comments**: Explain complex logic
- **Docstrings**: Google style for all functions
- **README files**: Clear setup and usage instructions
- **API documentation**: Comprehensive endpoint documentation

### Documentation Structure

```
docs/
├── README.md              # Main documentation
├── PROJECT_STRUCTURE.md   # Project structure details
├── REFACTOR_SUMMARY.md    # Refactoring documentation
├── IMPLEMENTATION_GUIDE.md # Implementation details
├── UPGRADES.md           # Upgrade history
├── API.md                # API documentation
├── DEPLOYMENT.md         # Deployment guide
└── CONTRIBUTING.md       # This file
```

### Writing Documentation

- **Clear and concise**: Avoid unnecessary complexity
- **Examples**: Include practical examples
- **Screenshots**: Add visual aids when helpful
- **Links**: Cross-reference related documentation

## 🚀 Pull Request Process

### Before Submitting

1. **Test your changes**: Ensure all tests pass
2. **Update documentation**: Add/update relevant docs
3. **Follow code style**: Run formatting tools
4. **Check for conflicts**: Ensure no merge conflicts

### Pull Request Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix (non-breaking change which fixes an issue)
- [ ] New feature (non-breaking change which adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] Documentation update

## Testing
- [ ] Unit tests pass
- [ ] Integration tests pass
- [ ] Manual testing completed

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Documentation updated
- [ ] Tests added/updated
- [ ] No breaking changes (or documented)

## Screenshots (if applicable)
Add screenshots for UI changes

## Additional Notes
Any additional information
```

### Review Process

1. **Automated checks**: CI/CD pipeline runs tests
2. **Code review**: Maintainers review the code
3. **Testing**: Manual testing may be required
4. **Approval**: At least one maintainer approval required
5. **Merge**: Changes merged to main branch

## 📋 Issue Templates

### Bug Report Template

```markdown
## Bug Description
[Describe the bug]

## Steps to Reproduce
1. [Step 1]
2. [Step 2]
3. [Step 3]

## Expected vs Actual Behavior
[What you expected vs what happened]

## Environment
- OS: [e.g., Windows 10]
- Python: [e.g., 3.10.6]
- Version: [e.g., 1.0.3]

## Additional Context
[Any other relevant information]
```

### Feature Request Template

```markdown
## Feature Description
[Describe the feature]

## Problem Statement
[What problem does this solve?]

## Proposed Solution
[How would you implement this?]

## Alternative Solutions
[Any alternatives considered]

## Additional Context
[Any other relevant information]
```

## 🏆 Recognition

### Contributors Hall of Fame

We recognize contributors in several ways:

- **GitHub contributors**: Listed in repository contributors
- **Release notes**: Credit for significant contributions
- **Documentation**: Contributors listed in docs
- **Special thanks**: For major contributions

### Contribution Levels

- **🥉 Bronze**: 1-5 contributions
- **🥈 Silver**: 6-15 contributions
- **🥇 Gold**: 16+ contributions
- **💎 Diamond**: Major feature contributions

### Getting Recognition

- **Consistent contributions**: Regular, quality contributions
- **Documentation**: Help improve docs
- **Community support**: Help other contributors
- **Feature development**: Implement significant features

## 📞 Contact

### Questions or Concerns?

- **GitHub Issues**: For bug reports and feature requests
- **Discussions**: For general questions and discussions
- **Email**: [contributors@aicallbot.com](mailto:contributors@aicallbot.com)

### Community Guidelines

- **Be respectful**: Treat others with respect
- **Be helpful**: Help other contributors
- **Be patient**: Maintainers are volunteers
- **Be constructive**: Provide constructive feedback

---

**Thank you for contributing to AI Call Bot! 🎉**

Your contributions help make this project better for everyone. 