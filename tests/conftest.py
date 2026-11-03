from __future__ import annotations

import pytest

from tests.fixtures.candles import make_invalid_series, make_valid_series


@pytest.fixture
def valid_candles():
    return make_valid_series()


@pytest.fixture
def invalid_candles():
    return make_invalid_series()
