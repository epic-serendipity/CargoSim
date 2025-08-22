# CargoSim Test Suite

This directory contains the comprehensive test suite for the CargoSim project. All tests have been updated to work with the current codebase and provide reliable validation of the simulation functionality.

## Test Overview

- **Total Tests:** 19
- **Test Files:** 5
- **Coverage:** Core simulation, CLI, rendering, enhanced features, and operations

## Test Files

### 1. `test_simulation.py` - Core Simulation Tests
**Type:** Unit Tests  
**Tests:** 11  
**Coverage:** Aircraft management, fleet building, operations, resource management

- **TestAircraft:** Aircraft creation, max active periods, hub location detection
- **TestLogisticsSim:** Simulation initialization, world reset, fleet building, operations
- **TestUtilityFunctions:** Row-to-spoke conversion, operational capability detection

### 2. `test_cli_entrypoints.py` - Command Line Interface Tests
**Type:** Unit Tests  
**Tests:** 2  
**Coverage:** CLI entry points, headless mode

- Python module execution (`python -m cargosim`)
- Headless simulation mode with exit codes

### 3. `test_enhanced_features.py` - Enhanced Features Tests
**Type:** Integration Tests  
**Tests:** 1  
**Coverage:** Aircraft animation, spoke bar scaling, state mapping

- Aircraft state mapping system
- Bar scaling modes (linear/geometric)
- Animation toggle functionality
- Bar height calculations

### 4. `test_ops_gate.py` - Operations Gate Tests
**Type:** Integration Tests  
**Tests:** 3  
**Coverage:** Operations synchronization, resource consumption, timing

- UI synchronization with operations gate
- C/D resource consumption during operations
- Arrival timing and resource application

### 5. `test_fullscreen.py` - Display Mode Tests
**Type:** Integration Tests  
**Tests:** 2  
**Coverage:** Fullscreen and windowed display modes

- Fullscreen mode functionality
- Windowed mode functionality
- Display initialization and configuration

## Test Categories

### Unit Tests (`-m unit`)
- **13 tests** - Fast, isolated tests for individual components
- Focus on core simulation logic and CLI functionality
- No external dependencies or complex setup required

### Integration Tests (`-m integration`)
- **6 tests** - Tests that require multiple components working together
- Include pygame rendering, display initialization
- Test real-world usage scenarios

## Running Tests

### Basic Test Execution
```bash
# Run all tests
python -m pytest tests/

# Run with verbose output
python -m pytest tests/ -v

# Run with short traceback
python -m pytest tests/ --tb=short
```

### Test Categories
```bash
# Run only unit tests
python -m pytest tests/ -m unit

# Run only integration tests
python -m pytest tests/ -m integration

# Run tests excluding slow ones
python -m pytest tests/ -m "not slow"
```

### Specific Test Files
```bash
# Run specific test file
python -m pytest tests/test_simulation.py

# Run specific test class
python -m pytest tests/test_simulation.py::TestAircraft

# Run specific test method
python -m pytest tests/test_simulation.py::TestAircraft::test_aircraft_creation
```

## Test Configuration

### `conftest.py`
- **Common fixtures** for test configuration and simulation instances
- **Environment setup** for pygame testing (SDL_VIDEODRIVER=dummy)
- **Automatic test categorization** with pytest markers
- **Proper cleanup** of pygame resources

### Test Fixtures
- **`test_config`:** Basic simulation configuration
- **`test_simulation`:** Pre-configured simulation instance
- **`test_renderer`:** Initialized renderer with proper cleanup

## Environment Requirements

### Required Dependencies
- **Python 3.10+**
- **pytest** - Test framework
- **pygame** - Graphics library (for integration tests)

### Optional Dependencies
- **pytest-cov** - Coverage reporting
- **pytest-xdist** - Parallel test execution

## Test Environment Setup

The test suite automatically configures the environment for testing:

1. **SDL_VIDEODRIVER=dummy** - Prevents display issues in CI/headless environments
2. **PYGAME_HIDE_SUPPORT_PROMPT=1** - Suppresses pygame welcome messages
3. **Proper Python path** - Ensures imports work correctly

## Writing New Tests

### Test Structure
```python
def test_feature_name():
    """Test description of what is being tested."""
    # Arrange - Set up test data
    cfg = SimConfig()
    sim = LogisticsSim(cfg)
    
    # Act - Execute the functionality
    result = sim.some_method()
    
    # Assert - Verify the results
    assert result == expected_value
```

### Test Naming Conventions
- **Test functions:** `test_descriptive_name`
- **Test classes:** `TestClassName`
- **Test files:** `test_module_name.py`

### Test Categories
- **Unit tests:** Test individual functions/methods in isolation
- **Integration tests:** Test multiple components working together
- **Slow tests:** Mark with `@pytest.mark.slow` for long-running tests

## Troubleshooting

### Common Issues

1. **Import Errors**
   - Ensure you're running from the project root
   - Check that `conftest.py` is properly setting up the Python path

2. **Pygame Display Issues**
   - Tests automatically use `SDL_VIDEODRIVER=dummy`
   - Ensure pygame is properly installed

3. **Test Failures**
   - Run with `-v` for verbose output
   - Use `--tb=long` for detailed tracebacks
   - Check that all dependencies are installed

### Debug Mode
```bash
# Run tests with debug output
python -m pytest tests/ -v -s

# Run specific failing test
python -m pytest tests/test_file.py::test_name -v -s
```

## Continuous Integration

The test suite is designed to work in CI environments:

- **Headless execution** - No display required
- **Automatic cleanup** - Resources properly managed
- **Consistent results** - Tests are deterministic
- **Fast execution** - Unit tests complete quickly

## Performance

- **Unit tests:** ~0.5 seconds
- **Integration tests:** ~1.5 seconds
- **Total suite:** ~2 seconds

## Contributing

When adding new tests:

1. **Follow existing patterns** for test structure and naming
2. **Use appropriate markers** (unit/integration/slow)
3. **Include proper cleanup** for any resources created
4. **Add descriptive docstrings** explaining test purpose
5. **Ensure tests are deterministic** and don't depend on external state

## Support

For test-related issues:

1. Check this README for common solutions
2. Review existing test patterns
3. Ensure all dependencies are properly installed
4. Run tests with verbose output for debugging
