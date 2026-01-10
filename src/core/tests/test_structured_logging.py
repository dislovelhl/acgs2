import asyncio
import contextlib
import io
import json
import sys
import unittest

from fastapi import FastAPI
from src.core.shared.acgs_logging import (
    clear_correlation_id,
    get_logger,
    init_service_logging,
    set_correlation_id,
)


class TestStructuredLogging(unittest.TestCase):
    def setUp(self):
        # Capture stderr where logging output goes
        self.stderr_capture = io.StringIO()
        self.patch_stderr = contextlib.redirect_stderr(self.stderr_capture)
        self.patch_stderr.__enter__()

    def tearDown(self):
        self.patch_stderr.__exit__(None, None, None)

    def test_json_logging(self):
        # Initialize logging in JSON mode
        logger = init_service_logging("test-service", level="INFO", json_format=True)
        logger.info("test_event", key="value")

        output = self.stderr_capture.getvalue().strip()
        log_records = [json.loads(line) for line in output.split("\n") if line]

        self.assertTrue(len(log_records) > 0)
        record = log_records[0]
        self.assertEqual(record["event"], "test_event")
        self.assertEqual(record["service"], "test-service")
        self.assertEqual(record["key"], "value")
        self.assertIn("timestamp", record)
        self.assertIn("level", record)

    def test_correlation_id_propagation(self):
        init_service_logging("test-service", level="INFO", json_format=True)
        logger = get_logger("test")

        set_correlation_id("test-corr-id")
        logger.info("event_with_corr")

        output = self.stderr_capture.getvalue().strip()
        # Parse all JSON lines from output
        json_lines = [line for line in output.split("\n") if line.strip()]
        if json_lines:
            record = json.loads(json_lines[-1])
        else:
            self.fail("No log output captured")

        self.assertEqual(record["correlation_id"], "test-corr-id")

        clear_correlation_id()


if __name__ == "__main__":
    unittest.main()
