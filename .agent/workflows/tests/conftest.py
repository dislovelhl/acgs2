def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line(
        "markers", "constitutional: mark test as constitutional compliance check"
    )
