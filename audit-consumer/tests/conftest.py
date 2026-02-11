import pytest
from unittest.mock import AsyncMock, MagicMock

from src.services.bigquery import AuditBigQuery


@pytest.fixture
def mock_bigquery():
    bq = AsyncMock(spec=AuditBigQuery)
    bq.insert.return_value = None
    bq.flush.return_value = None
    bq.close.return_value = None
    return bq
