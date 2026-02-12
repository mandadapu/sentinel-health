"""BigQuery streaming insert service with batch buffering."""

import asyncio
import logging

from src.config import ConsumerSettings

logger = logging.getLogger(__name__)


class AuditBigQuery:
    def __init__(self, settings: ConsumerSettings, table_override: str | None = None) -> None:
        self._client = None
        self._table_ref = ""
        self._buffer: list[dict] = []
        self._batch_size = settings.batch_size
        self._flush_interval = settings.flush_interval_seconds
        self._flush_task: asyncio.Task | None = None
        table_name = table_override or settings.bigquery_table

        if settings.bigquery_dataset:
            try:
                from google.cloud import bigquery

                self._client = bigquery.Client(project=settings.gcp_project_id)
                self._table_ref = (
                    f"{settings.gcp_project_id}.{settings.bigquery_dataset}.{table_name}"
                )
                logger.info("BigQuery client initialized for %s", self._table_ref)
            except Exception:
                logger.warning("BigQuery client unavailable — rows will be logged only")
        else:
            logger.info("BigQuery dataset not configured — running in log-only mode")

    async def start_periodic_flush(self) -> None:
        """Start background task that flushes buffer on a timer."""
        self._flush_task = asyncio.create_task(self._periodic_flush())

    async def _periodic_flush(self) -> None:
        while True:
            await asyncio.sleep(self._flush_interval)
            await self.flush()

    async def insert(self, row: dict) -> None:
        """Buffer a row and flush if batch size reached."""
        self._buffer.append(row)
        if len(self._buffer) >= self._batch_size:
            await self.flush()

    async def flush(self) -> None:
        """Flush buffered rows to BigQuery."""
        if not self._buffer:
            return

        rows = list(self._buffer)
        self._buffer.clear()

        if not self._client:
            logger.info("Log-only mode — %d audit rows: %s", len(rows), [r.get("encounter_id") for r in rows])
            return

        loop = asyncio.get_running_loop()
        errors = await loop.run_in_executor(
            None, self._client.insert_rows_json, self._table_ref, rows
        )
        if errors:
            logger.error("BigQuery insert errors: %s", errors)
        else:
            logger.info("Flushed %d rows to BigQuery", len(rows))

    async def close(self) -> None:
        """Flush remaining rows and cancel periodic task."""
        if self._flush_task:
            self._flush_task.cancel()
            try:
                await self._flush_task
            except asyncio.CancelledError:
                pass
        await self.flush()
        if self._client:
            self._client.close()
