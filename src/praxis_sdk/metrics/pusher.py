"""
Metrics pusher for sending metrics to Prometheus Remote Write API.
"""

import asyncio
import time
import httpx
import snappy
from typing import Optional, Dict
from loguru import logger
from prometheus_client.parser import text_string_to_metric_families
from prometheus_client.samples import Sample

from .collector import MetricsCollector

try:
    from praxis_sdk.metrics import remote_pb2
except ImportError:
    logger.warning("Protobuf definitions not found, Remote Write will not work")
    remote_pb2 = None


class MetricsPusher:
    """
    Pushes metrics to Prometheus Remote Write API at regular intervals.

    Uses Prometheus Remote Write protocol with Snappy compression.
    """

    def __init__(
        self,
        collector: MetricsCollector,
        remote_write_url: str,
        job_name: str,
        instance: str,
        push_interval: int = 15,
        basic_auth_username: Optional[str] = None,
        basic_auth_password: Optional[str] = None,
        labels: Optional[Dict[str, str]] = None,
    ):
        """
        Initialize metrics pusher.

        Args:
            collector: MetricsCollector instance
            remote_write_url: Prometheus Remote Write URL (e.g., https://monitoring.prxs.ai/prometheus/api/v1/write)
            job_name: Prometheus job name
            instance: Instance identifier (usually agent name)
            push_interval: Push interval in seconds (default: 15)
            basic_auth_username: Optional basic auth username (not needed for prxs.ai)
            basic_auth_password: Optional basic auth password (not needed for prxs.ai)
            labels: Additional labels to attach to all metrics
        """
        self.collector = collector
        self.remote_write_url = remote_write_url.rstrip("/")
        self.job_name = job_name
        self.instance = instance
        self.push_interval = push_interval
        self.basic_auth_username = basic_auth_username
        self.basic_auth_password = basic_auth_password

        # Add job and instance to default labels
        self.labels = labels or {}
        self.labels["job"] = job_name
        self.labels["instance"] = instance

        self._running = False
        self._push_count = 0
        self._error_count = 0

        logger.info(
            f"MetricsPusher initialized: {remote_write_url}, "
            f"job={job_name}, instance={instance}, interval={push_interval}s"
        )

    def _convert_to_remote_write(self, metrics_text: bytes) -> bytes:
        """
        Convert Prometheus text format to Remote Write protobuf format.

        Args:
            metrics_text: Metrics in Prometheus text format

        Returns:
            Snappy-compressed protobuf bytes
        """
        if not remote_pb2:
            raise RuntimeError("Protobuf definitions not available")

        families = text_string_to_metric_families(metrics_text.decode('utf-8'))

        timeseries_list = []
        timestamp_ms = int(time.time() * 1000)

        for family in families:
            for sample in family.samples:
                labels = []

                # Add metric name
                labels.append(remote_pb2.Label(
                    name="__name__",
                    value=sample.name
                ))

                # Add sample labels
                for label_name, label_value in sample.labels.items():
                    labels.append(remote_pb2.Label(
                        name=label_name,
                        value=label_value
                    ))

                # Add default labels
                for label_name, label_value in self.labels.items():
                    # Don't override existing labels
                    if label_name not in sample.labels:
                        labels.append(remote_pb2.Label(
                            name=label_name,
                            value=label_value
                        ))

                # Create sample
                samples = [remote_pb2.Sample(
                    value=sample.value,
                    timestamp=timestamp_ms
                )]

                # Create timeseries
                timeseries_list.append(remote_pb2.TimeSeries(
                    labels=labels,
                    samples=samples
                ))

        # Build write request
        write_request = remote_pb2.WriteRequest(timeseries=timeseries_list)

        # Serialize and compress
        serialized = write_request.SerializeToString()
        compressed = snappy.compress(serialized)

        return compressed

    async def push_once(self) -> bool:
        """
        Push metrics to Prometheus Remote Write endpoint once.

        Returns:
            True if successful, False otherwise
        """
        try:
            # Serialize metrics to text format
            metrics_data = self.collector.serialize()

            if not metrics_data:
                logger.warning("No metrics data to push")
                return False

            # Convert to Remote Write format
            remote_write_data = self._convert_to_remote_write(metrics_data)

            # Prepare auth
            auth = None
            if self.basic_auth_username and self.basic_auth_password:
                auth = (self.basic_auth_username, self.basic_auth_password)

            # Push to Remote Write endpoint
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    self.remote_write_url,
                    content=remote_write_data,
                    headers={
                        "Content-Encoding": "snappy",
                        "Content-Type": "application/x-protobuf",
                        "X-Prometheus-Remote-Write-Version": "0.1.0",
                    },
                    auth=auth,
                )

                if response.status_code in (200, 204):
                    self._push_count += 1
                    logger.debug(
                        f"Successfully pushed metrics to Remote Write endpoint "
                        f"(push #{self._push_count})"
                    )
                    return True
                else:
                    self._error_count += 1
                    logger.error(
                        f"Failed to push metrics: HTTP {response.status_code} "
                        f"- {response.text}"
                    )
                    return False

        except httpx.TimeoutException:
            self._error_count += 1
            logger.error("Timeout while pushing metrics to Remote Write endpoint")
            return False
        except httpx.ConnectError as e:
            self._error_count += 1
            logger.error(f"Connection error while pushing metrics: {e}")
            return False
        except Exception as e:
            self._error_count += 1
            logger.error(f"Unexpected error while pushing metrics: {e}")
            return False

    async def run(self) -> None:
        """
        Run the metrics pusher loop.

        Continuously pushes metrics at the configured interval.
        """
        self._running = True
        logger.info(f"Starting metrics pusher loop (interval: {self.push_interval}s)")

        try:
            while self._running:
                await self.push_once()
                await asyncio.sleep(self.push_interval)
        except asyncio.CancelledError:
            logger.info("Metrics pusher cancelled")
            raise
        finally:
            self._running = False
            logger.info(
                f"Metrics pusher stopped (total pushes: {self._push_count}, "
                f"errors: {self._error_count})"
            )

    async def delete_metrics(self) -> bool:
        """
        Delete metrics from Remote Write endpoint.

        Note: Remote Write API does not support deletion.
        This method exists for API compatibility but does nothing.

        Returns:
            Always returns True
        """
        logger.info("Remote Write API does not support metric deletion")
        return True

    def stop(self) -> None:
        """Stop the metrics pusher."""
        self._running = False

    def get_stats(self) -> Dict[str, int]:
        """Get pusher statistics."""
        return {
            "push_count": self._push_count,
            "error_count": self._error_count,
        }
