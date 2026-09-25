from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from viral_local_ad_generator.cli import analyze_run_log, find_previous_run_status
from viral_local_ad_generator.event_logger import PipelineLogger


class PipelineLoggerTests(unittest.TestCase):
    def test_analysis_uses_only_the_latest_run_in_reused_log(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "events.ndjson"
            path.write_text(
                "\n".join(
                    [
                        json.dumps({"run_id": "old", "stage": "run_status", "event_type": "started"}),
                        json.dumps({"run_id": "old", "stage": "run_status", "event_type": "failed", "status": "error"}),
                        json.dumps({"run_id": "new", "stage": "run_status", "event_type": "started"}),
                        json.dumps({"run_id": "new", "stage": "run_status", "event_type": "completed"}),
                        json.dumps({"run_id": "new", "stage": "cli", "event_type": "finish"}),
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            result = analyze_run_log(path)

            self.assertFalse(result["failed"])
            self.assertEqual(result["run_id"], "new")

    def test_finds_previous_run_in_the_output_folder_being_reused(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            runs_dir = Path(temporary_directory) / "runs"
            log_path = runs_dir / "campaign" / "logs" / "ad_gen_events.ndjson"
            log_path.parent.mkdir(parents=True)
            log_path.write_text(
                json.dumps({"run_id": "unfinished", "stage": "run_status", "event_type": "started"}) + "\n",
                encoding="utf-8",
            )

            result = find_previous_run_status(runs_dir)

            self.assertIsNotNone(result)
            assert result is not None
            self.assertTrue(result["failed"])
            self.assertEqual(result["run_id"], "unfinished")

    def test_failure_uses_last_pipeline_stage(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            logger = PipelineLogger(output_dir=Path(temporary_directory), command="run")
            logger.emit("nimble.news_search", "request")
            logger.emit_run_failed(RuntimeError("provider unavailable"))

            event = json.loads(logger.local_path.read_text(encoding="utf-8").splitlines()[-1])
            payload = json.loads(event["payload_json"])

            self.assertEqual(payload["failed_stage"], "nimble.news_search")

    def test_tinybird_timeout_does_not_fail_local_logging(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            logger = PipelineLogger(
                output_dir=Path(temporary_directory),
                command="run",
                tinybird_token="configured",
            )
            with patch("viral_local_ad_generator.event_logger.urllib.request.urlopen", side_effect=TimeoutError("slow")):
                logger.emit("pipeline", "checkpoint", {"count": 1})

            self.assertTrue(logger.local_path.exists())
            error_path = Path(temporary_directory) / "logs" / "tinybird_errors.ndjson"
            self.assertTrue(error_path.exists())
            self.assertEqual(len(logger.local_path.read_text(encoding="utf-8").splitlines()), 1)


if __name__ == "__main__":
    unittest.main()
