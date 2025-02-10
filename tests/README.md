# UMBRELLA-AI Test Suite

## Directory Structure
```
tests/
├── unit/                    # Unit tests for individual components
│   ├── agents/             # Tests for each agent's core functionality
│   ├── config/             # Configuration and setup tests
│   ├── orchestrator/       # Orchestrator component tests
│   └── utils/              # Utility function tests
├── integration/            # Integration tests between components
│   ├── agent_interaction/  # Tests for agent-to-agent communication
│   ├── api_integration/    # External API integration tests
│   └── workflow/           # Multi-component workflow tests
├── e2e/                    # End-to-end workflow tests
│   ├── scenarios/          # Real-world usage scenarios
│   └── performance/        # Performance and load tests
├── data/                   # Test data and fixtures
│   ├── documents/          # Sample documents for testing
│   ├── images/            # Test images
│   └── responses/         # Mock API responses
└── coverage/              # Test coverage reports
```

## Test Categories

### Unit Tests
- Individual component functionality
- Mocked dependencies
- Fast execution

### Integration Tests
- Component interaction
- Partial system testing
- Real dependencies when practical

### End-to-End Tests
- Complete workflow testing
- Real-world scenarios
- Performance benchmarks

## Running Tests

### Unit Tests
```bash
pytest tests/unit -v
```

### Integration Tests
```bash
pytest tests/integration -v
```

### End-to-End Tests
```bash
pytest tests/e2e -v
```

### All Tests with Coverage
```bash
pytest --cov=src tests/ -v
```

## Test Data
Test data is stored in `tests/data/` and includes:
- Sample PDFs
- Test images
- Mock API responses
- Configuration fixtures

## Coverage Requirements
- Unit Tests: 90% minimum coverage
- Integration Tests: 80% minimum coverage
- End-to-End Tests: Key workflows covered

## Adding New Tests
1. Place tests in appropriate directory
2. Follow naming convention: `test_*_*.py`
3. Include docstrings and comments
4. Add necessary fixtures to `conftest.py`
5. Update this README if adding new categories
