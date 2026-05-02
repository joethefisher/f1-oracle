import os
import pytest


def pytest_configure(config):
    config.addinivalue_line(
        "markers", "requires_db: mark test as requiring a live DATABASE_URL"
    )


def pytest_runtest_setup(item):
    if item.get_closest_marker("requires_db"):
        if not os.getenv("DATABASE_URL"):
            pytest.skip("DATABASE_URL not set — skipping DB integration test")
