import json
import io
import contextlib
import unittest
from shared.logging import init_service_logging, get_logger, create_correlation_middleware, set_correlation_id, clear_correlation_id
from shared.otel_config import init_otel
from fastapi import FastAPI, Request
import asyncio

class TestStructuredLogging(unittest.TestCase):
    def setUp(self):
        # Redirect stdout to capture logs
        self.log_capture = io.StringIO()
        self.patch_stdout = contextlib.redirect_stdout(self.log_capture)
        self.patch_stdout.__enter__()

    def tearDown(self):
        self.patch_stdout.__exit__(None, None, None)

    def test_json_logging(self):
        # Initialize logging in JSON mode
        logger = init_service_logging("test-service", level="INFO", json_format=True)
        logger.info("test_event", key="value")

        output = self.log_capture.getvalue().strip()
        log_records = [json.loads(line) for line in output.split('\n') if line]

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

        output = self.log_capture.getvalue().strip()
        record = json.loads(output.split('\n')[-1])
        self.assertEqual(record["correlation_id"], "test-corr-id")

        clear_correlation_id()

if __name__ == "__main__":
    unittest.main()
