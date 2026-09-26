import pytest


@pytest.fixture(autouse=True)
def clear_derive_cache():
    from app import derive

    derive.cache.clear()
    yield
    derive.cache.clear()
