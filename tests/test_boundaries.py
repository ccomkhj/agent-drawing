"""The seam contract: the fakes satisfy the injectable boundary protocols, and
the boundaries behave as the core will rely on."""

from __future__ import annotations

from docvault.boundaries import Embedder, LLMClient
from tests.fakes import FakeEmbedder, FakeLLMClient


def test_fake_llm_conforms_to_protocol():
    assert isinstance(FakeLLMClient(), LLMClient)


def test_fake_embedder_conforms_to_protocol():
    assert isinstance(FakeEmbedder(), Embedder)


def test_fake_llm_returns_queued_then_default_and_records_calls():
    llm = FakeLLMClient(responses=["first"], default="fallback")

    assert llm.complete(model="claude-haiku-4-5", prompt="a") == "first"
    assert llm.complete(model="claude-haiku-4-5", prompt="b", system="s") == "fallback"
    assert llm.calls[0]["prompt"] == "a"
    assert llm.calls[1]["system"] == "s"


def test_fake_embedder_is_deterministic_and_right_dimension():
    emb = FakeEmbedder(dimension_value=8)

    v1 = emb.embed(["hello"])[0]
    v2 = emb.embed(["hello"])[0]
    v3 = emb.embed(["world"])[0]

    assert v1 == v2  # deterministic
    assert v1 != v3  # different text → different vector
    assert len(v1) == emb.dimension == 8
