# CargoSim Test Suite

This directory contains the comprehensive test suite for CargoSim.

## Directory Structure

### `unit/`
Unit tests organized by module:
- `core/` - Core simulation logic tests
- `ui/` - User interface component tests
- `rendering/` - Visualization and rendering tests

### `integration/`
Integration tests that test multiple components together:
- End-to-end simulation tests
- Component interaction tests
- Performance and stress tests

### `fixtures/`
Test data and fixtures:
- Sample configurations
- Test aircraft definitions
- Mock data for testing

## Test Categories

### Unit Tests
**Purpose**: Test individual functions and classes in isolation
**Coverage**: Core logic, configuration, utilities
**Speed**: Fast execution
**Dependencies**: Minimal external dependencies

**Examples**:
- `test_simulation.py` - Simulation logic tests
- `test_config.py` - Configuration validation tests
- `test_utils.py` - Utility function tests

### Integration Tests
**Purpose**: Test component interactions and system behavior
**Coverage**: Multi-component scenarios, end-to-end workflows
**Speed**: Slower execution
**Dependencies**: Full system setup

**Examples**:
- `test_advanced_simulation.py` - Complex simulation scenarios
- `test_fullscreen.py` - Display mode integration
- `test_ops_gate.py` - Resource gating logic

### UI Tests
**Purpose**: Test user interface components
**Coverage**: GUI elements, user interactions, fleet builder
**Speed**: Medium execution
**Dependencies**: Tkinter, GUI frameworks

**Examples**:
- `test_fleet_builder.py` - Fleet builder functionality
- `test_gui.py` - Main GUI component tests

### Rendering Tests
**Purpose**: Test visualization and rendering
**Coverage**: Pygame rendering, themes, recording
**Speed**: Medium execution
**Dependencies**: Pygame, graphics libraries

**Examples**:
- `test_renderer.py` - Core rendering tests
- `test_recorder.py` - Recording functionality
- `test_renderer_complete.py` - Full rendering pipeline

## Running Tests

### Basic Test Execution
```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/unit/core/test_simulation.py

# Run specific test function
pytest tests/unit/core/test_simulation.py::test_simulation_initialization
```

### Test Categories
```bash
# Run only unit tests
pytest tests/unit/

# Run only integration tests
pytest tests/integration/

# Run tests by module
pytest tests/unit/core/
pytest tests/unit/ui/
pytest tests/unit/rendering/
```

### Test Markers
```bash
# Run fast tests only
pytest -m "not slow"

# Run integration tests
pytest -m integration

# Run unit tests
pytest -m unit
```

### Coverage and Reporting
```bash
# Run with coverage
pytest --cov=cargosim

# Generate HTML coverage report
pytest --cov=cargosim --cov-report=html

# Generate XML coverage report
pytest --cov=cargosim --cov-report=xml
```

## Test Configuration

### pytest.ini
```ini
[tool:pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = --strict-markers --strict-config --verbose --tb=short
markers =
    slow: marks tests as slow
    integration: marks tests as integration tests
    unit: marks tests as unit tests
```

### conftest.py
Contains shared fixtures and test configuration:
- Database setup/teardown
- Mock objects
- Test data generation
- Environment configuration

## Test Writing Guidelines

### Test Structure
```python
import pytest
from cargosim.core import SimConfig

class TestSimConfig:
    def test_config_initialization(self):
        """Test that SimConfig initializes correctly."""
        config = SimConfig()
        assert config.periods == 60
        assert config.fleet_label == "2xC130"
    
    def test_config_validation(self):
        """Test configuration validation."""
        config = SimConfig()
        config.periods = -1  # Invalid value
        issues = validate_config(config)
        assert "periods must be positive" in issues
```

### Best Practices
1. **Descriptive Names**: Use clear, descriptive test names
2. **Single Responsibility**: Each test should test one thing
3. **Arrange-Act-Assert**: Structure tests clearly
4. **Documentation**: Include docstrings explaining test purpose
5. **Edge Cases**: Test boundary conditions and error cases

### Test Data
```python
@pytest.fixture
def sample_config():
    """Provide a sample configuration for testing."""
    return SimConfig(
        fleet_label="TestFleet",
        periods=10,
        initial_stocks={"A": 5, "B": 5, "C": 5, "D": 5}
    )

def test_with_sample_config(sample_config):
    """Test using the sample configuration fixture."""
    assert sample_config.fleet_label == "TestFleet"
```

## Continuous Integration

### GitHub Actions
Tests run automatically on:
- Pull requests
- Push to main branch
- Scheduled runs

### Test Matrix
- Python versions: 3.10, 3.11, 3.12, 3.13
- Operating systems: Windows, macOS, Linux
- Dependencies: All supported versions

## Performance Testing

### Benchmark Tests
```bash
# Run performance benchmarks
pytest tests/integration/ -m "benchmark"

# Generate performance reports
pytest --benchmark-only
```

### Memory Testing
```bash
# Run memory leak tests
pytest tests/integration/ -m "memory"

# Profile memory usage
pytest --memray
```

## Debugging Tests

### Verbose Output
```bash
# Maximum verbosity
pytest -vvv

# Show local variables on failure
pytest -l

# Show captured output
pytest -s
```

### Debugging Specific Tests
```bash
# Run with debugger
pytest --pdb

# Stop on first failure
pytest -x

# Run only failing tests
pytest --lf
```

## Contributing

### Adding New Tests
1. Place tests in appropriate subdirectory
2. Follow naming conventions
3. Include proper documentation
4. Add to appropriate test categories
5. Ensure tests pass locally

### Test Maintenance
1. Keep tests up to date with code changes
2. Remove obsolete tests
3. Update test data as needed
4. Maintain test performance
5. Review test coverage regularly

## Troubleshooting

### Common Issues
- **Import Errors**: Check Python path and package installation
- **Missing Dependencies**: Install test dependencies
- **Configuration Issues**: Verify pytest configuration
- **Environment Problems**: Check Python version and virtual environment

### Getting Help
- Check test output for error details
- Review test configuration
- Consult pytest documentation
- Ask in project discussions
