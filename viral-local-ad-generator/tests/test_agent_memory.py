from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from typing import Any

from viral_local_ad_generator.agent_memory import AgentMemory, PipelineHalt, create_memory
from viral_local_ad_generator.models import VideoAdConcept
from viral_local_ad_generator.pipeline import discover_stories, generate_videos
from viral_local_ad_generator.staging import variant_id_for


class FakeTinybird:
    """Stands in for scripts/tb_events.py: records emits, serves canned prior events."""

    def __init__(self, prior: list[dict[str, Any]] | None = None) -> None:
        self.prior = prior or []
        self.emitted: list[dict[str, Any]] = []

    def emit(self, campaign_id, agent, event_type, payload=None, run_id=None, variant_id=None, cost_usd=None):
        self.emitted.append(
            {
                "campaign_id": campaign_id,
                "agent": agent,
                "event_type": event_type,
                "payload": payload,
                "run_id": run_id,
                "variant_id": variant_id,
                "cost_usd": cost_usd,
            }
        )
        return run_id or "run"

    def read(self, campaign_id, since=None, agent=None, limit=200):
        return list(self.prior)

    def types(self) -> list[str]:
        return [event["event_type"] for event in self.emitted]


class FakeBFL:
    def __init__(self, fail_on_submit: set[int] | None = None, poll_status: str = "Ready") -> None:
        self.fail_on_submit = fail_on_submit or set()
        self.poll_status = poll_status
        self.submitted: list[dict[str, Any]] = []
        self.logger = None

    def submit_flux3_video(self, payload: dict[str, Any]) -> dict[str, Any]:
        index = len(self.submitted) + 1
        self.submitted.append(payload)
        if index in self.fail_on_submit:
            raise RuntimeError("HTTP 402 from https://api.bfl.ai/v1/flux-3-video: insufficient credits")
        return {"id": f"job-{index}", "polling_url": f"https://poll/{index}"}

    def poll(self, polling_url: str, timeout_seconds: int = 900, interval_seconds: float = 2.0) -> dict[str, Any]:
        return {"status": self.poll_status, "result": {"sample": f"https://cdn/{polling_url[-1]}.mp4"}}


class FailingNimble:
    logger = None

    def search_recent_local_news(self, market, limit=10, outlets=None):
        raise RuntimeError("HTTP 503 from https://sdk.nimbleway.com/v2/search: upstream unavailable")


def concept(index: int) -> VideoAdConcept:
    return VideoAdConcept(
        story_title="Fog returns to Ocean Beach",
        story_url="https://example.com/fog",
        variant_index=index,
        angle=f"angle {index}",
        hook="hook",
        script="script",
        video_script="video script",
        visual_prompt="visual",
        audio_prompt="audio",
        negative_prompt="negative",
        bfl_payload={"prompt": f"variant {index}"},
    )


def memory_with(client: FakeTinybird, continue_on_error: bool = False) -> AgentMemory:
    return create_memory("sf-coffee-launch", client=client, run_id="run-1", continue_on_error=continue_on_error)


class AgentMemoryTests(unittest.TestCase):
    def test_video_stages_emit_submit_and_ready_with_variant_and_cost(self) -> None:
        client = FakeTinybird()
        memory = memory_with(client)
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["BFL_VIDEO_COST_USD"] = "0.05"
            try:
                generate_videos([concept(1)], Path(tmp), FakeBFL(), poll=True, download_media=False, memory=memory)
            finally:
                del os.environ["BFL_VIDEO_COST_USD"]

        self.assertEqual(client.types(), ["bfl_submit", "bfl_ready"])
        submit = client.emitted[0]
        self.assertEqual(submit["campaign_id"], "sf-coffee-launch")
        self.assertEqual(submit["agent"], "campaign-gen")
        self.assertEqual(submit["variant_id"], variant_id_for(concept(1)))
        self.assertEqual(submit["cost_usd"], 0.05)
        self.assertEqual(memory.cost_usd, 0.05)

    def test_bfl_error_emits_error_event_and_halts_before_next_variant(self) -> None:
        client = FakeTinybird()
        memory = memory_with(client)
        bfl = FakeBFL(fail_on_submit={1})
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(PipelineHalt) as raised:
                generate_videos([concept(1), concept(2)], Path(tmp), bfl, poll=True, download_media=False, memory=memory)

        self.assertEqual(raised.exception.step, "bfl_submit")
        self.assertEqual(len(bfl.submitted), 1, "second variant must not be submitted after an error")
        self.assertEqual(client.types(), ["error"])
        error_event = client.emitted[0]
        self.assertEqual(error_event["payload"]["step"], "bfl_submit")
        self.assertIn("HTTP 402", error_event["payload"]["message"])
        self.assertEqual(error_event["variant_id"], variant_id_for(concept(1)))
        self.assertTrue(memory.failed)

    def test_non_ready_poll_status_is_an_error(self) -> None:
        client = FakeTinybird()
        memory = memory_with(client)
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(PipelineHalt) as raised:
                generate_videos(
                    [concept(1)], Path(tmp), FakeBFL(poll_status="Content Moderated"), poll=True, download_media=False, memory=memory
                )
        self.assertEqual(raised.exception.step, "bfl_poll")
        self.assertEqual(client.types(), ["bfl_submit", "error"])

    def test_continue_on_error_records_error_and_moves_to_next_variant(self) -> None:
        client = FakeTinybird()
        memory = memory_with(client, continue_on_error=True)
        bfl = FakeBFL(fail_on_submit={1})
        with tempfile.TemporaryDirectory() as tmp:
            generate_videos([concept(1), concept(2)], Path(tmp), bfl, poll=True, download_media=False, memory=memory)

        self.assertEqual(len(bfl.submitted), 2)
        self.assertEqual(client.types(), ["error", "bfl_submit", "bfl_ready"])
        self.assertTrue(memory.failed)
        memory.finish({"concept_count": 2})
        self.assertEqual(client.emitted[-1]["payload"]["status"], "failed")

    def test_variants_already_ready_in_a_previous_run_are_skipped(self) -> None:
        done = variant_id_for(concept(1))
        client = FakeTinybird(prior=[{"event_type": "bfl_ready", "variant_id": done, "run_id": "older"}])
        memory = memory_with(client)
        bfl = FakeBFL()
        with tempfile.TemporaryDirectory() as tmp:
            concepts = [concept(1), concept(2)]
            generate_videos(concepts, Path(tmp), bfl, poll=True, download_media=False, memory=memory)

        self.assertEqual(len(bfl.submitted), 1)
        self.assertEqual(bfl.submitted[0]["prompt"], "variant 2")
        self.assertEqual(client.types(), ["variant_skipped", "bfl_submit", "bfl_ready"])
        self.assertEqual(client.emitted[0]["variant_id"], done)
        self.assertTrue(concepts[0].bfl_job and concepts[0].bfl_job.get("skipped"))

    def test_nimble_failure_emits_error_and_always_halts(self) -> None:
        client = FakeTinybird()
        memory = memory_with(client, continue_on_error=True)
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(PipelineHalt) as raised:
                discover_stories(
                    market="San Francisco",
                    output_dir=Path(tmp),
                    nimble_client=FailingNimble(),  # type: ignore[arg-type]
                    use_mock_news=False,
                    outlets=[],
                    memory=memory,
                )
        self.assertEqual(raised.exception.step, "nimble_query")
        self.assertEqual(client.types(), ["error"])
        self.assertIn("HTTP 503", client.emitted[0]["payload"]["message"])

    def test_mock_news_run_emits_story_ranked(self) -> None:
        client = FakeTinybird()
        memory = memory_with(client)
        with tempfile.TemporaryDirectory() as tmp:
            stories = discover_stories(
                market="San Francisco",
                output_dir=Path(tmp),
                nimble_client=FailingNimble(),  # type: ignore[arg-type]
                use_mock_news=True,
                max_stories=1,
                memory=memory,
            )
        self.assertEqual(len(stories), 1)
        self.assertEqual(client.types(), ["story_ranked"])
        self.assertEqual(len(client.emitted[0]["payload"]["selected"]), 1)

    def test_memory_client_failures_never_break_the_pipeline(self) -> None:
        class BrokenClient(FakeTinybird):
            def emit(self, *args, **kwargs):
                raise OSError("tinybird down")

            def read(self, *args, **kwargs):
                raise OSError("tinybird down")

        memory = memory_with(BrokenClient())
        with tempfile.TemporaryDirectory() as tmp:
            generate_videos([concept(1)], Path(tmp), FakeBFL(), poll=True, download_media=False, memory=memory)
        self.assertEqual(memory.completed_variants(), set())

    def test_without_tinybird_key_memory_is_a_no_op_but_guards_still_halt(self) -> None:
        os.environ.pop("TINYBIRD_API_KEY", None)
        memory = create_memory("sf-coffee-launch", run_id="run-2")
        self.assertFalse(memory.enabled)
        bfl = FakeBFL(fail_on_submit={1})
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(PipelineHalt):
                generate_videos([concept(1), concept(2)], Path(tmp), bfl, poll=False, download_media=False, memory=memory)
        self.assertEqual(len(bfl.submitted), 1)

    def test_helper_loader_uses_repo_tb_events(self) -> None:
        os.environ["TINYBIRD_API_KEY"] = "test-token"
        try:
            memory = create_memory("sf-coffee-launch", run_id="run-3")
        finally:
            del os.environ["TINYBIRD_API_KEY"]
        self.assertTrue(memory.enabled)
        self.assertTrue(hasattr(memory.client, "emit") and hasattr(memory.client, "read"))
        self.assertEqual(getattr(memory.client, "DATASOURCE", None), "agent_events")


if __name__ == "__main__":
    unittest.main()
