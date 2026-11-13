#!/usr/bin/env python3
"""Offline adapter checks: mocks Adaption SDK, never calls an API or uses credits."""
import importlib
import json
import os
import sys
import tempfile
import types
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
import adaption_backend as backend
import run_experiment


class FakeClient:
    last_kwargs = None
    def __init__(self):
        self.responses = self
        self.models = self

    def create(self, **kwargs):
        FakeClient.last_kwargs = kwargs
        return types.SimpleNamespace(status="completed",
            output_text=json.dumps({"final_answer": "Canberra", "confidence": 90,
                                    "explanation": "It is the capital."}),
            usage=types.SimpleNamespace(input_tokens=41, output_tokens=27))

    def list(self, **kwargs):
        assert kwargs == {"type": "hosted"}
        return types.SimpleNamespace(data=[
            types.SimpleNamespace(id="sample-hosted-model", display_name="Sample Hosted Model")
        ])


def main():
    with patch.dict(os.environ, {"ADAPTION_API_KEY": "dummy-local-test-only"}), \
         patch.dict(sys.modules, {"adaption": types.SimpleNamespace(Adaption=FakeClient)}):
        t1 = [{"role": "user", "content": "What is the capital of Australia?"}]
        raw, usage = backend.call_adaption("sample-hosted-model", t1, 0.0)
        assert json.loads(raw)["final_answer"] == "Canberra"
        assert usage == {"input_tokens": 41, "output_tokens": 27}
        options = FakeClient.last_kwargs
        assert options["model"] == "sample-hosted-model"
        assert options["instructions"] == run_experiment.SYSTEM
        assert options["input"] == t1
        assert options["temperature"] == 0.0
        assert options["agentic_memory"] is False
        assert options["store"] is False
        assert options["tool_choice"] == "none"
        assert options["tools"] == []
        assert backend.list_available_hosted_models()[0]["id"] == "sample-hosted-model"

        # Run a complete two-item synthetic smoke test through the same runner.
        # It must be marked mock and never call the fake Adaption provider.
        with tempfile.TemporaryDirectory() as d:
            out = str(Path(d) / "mock.jsonl")
            data = json.loads((ROOT / "data/benchmark.json").read_text(encoding="utf-8"))
            selected = [r for r in data["items"] if r["id"] in ("P01", "P07")]
            n = run_experiment.run(selected, "mock", "mock-1", 0.0, out, 0, "mock-run")
            assert n == 8
    with patch.dict(os.environ, {}, clear=True):
        try:
            backend.call_adaption("sample-hosted-model", [], 0)
        except RuntimeError as exc:
            assert "ADAPTION_API_KEY" in str(exc)
        else:
            raise AssertionError("Missing credential accepted")
    print("Adaption adapter offline tests: PASS (request shape, no tools/memory, usage, missing key)")


if __name__ == "__main__":
    main()
