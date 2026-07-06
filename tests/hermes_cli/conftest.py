"""Fixtures shared across hermes_cli kanban tests."""

from __future__ import annotations

import pytest


@pytest.fixture
def all_assignees_spawnable(monkeypatch):
    """Pretend every assignee maps to a real Hermes profile.

    Most dispatcher tests use synthetic assignees ("alice", "bob") that
    don't correspond to actual profile directories on disk. Without this
    patch, the dispatcher's profile-exists guard (PR #20105) routes
    those tasks into ``skipped_nonspawnable`` instead of spawning, which
    would break tests that assert spawn behavior.
    """
    from hermes_cli import profiles
    monkeypatch.setattr(profiles, "profile_exists", lambda name: True)


@pytest.fixture(autouse=True)
def _suppress_concurrent_hermes_gate(request, monkeypatch):
    """Default ``_detect_concurrent_hermes_instances`` to ``[]`` for every test.

    The Windows update path now refuses to proceed when another
    ``hermes.exe`` is detected (issue #26670). On a developer's Windows
    machine running the test suite via ``hermes`` itself, this would
    flag the running agent as a concurrent instance and abort every
    ``cmd_update`` test. Tests that want to exercise the gate explicitly
    re-patch ``_detect_concurrent_hermes_instances`` with their own
    return value — autouse here gives a clean default without touching
    the rest of the suite.

    Tests that need to call the REAL function (e.g. unit tests for the
    helper itself) opt out with ``@pytest.mark.real_concurrent_gate``.
    """
    if request.node.get_closest_marker("real_concurrent_gate"):
        return
    try:
        from hermes_cli import main as _cli_main
    except Exception:
        return
    # raising=False: under pytest's per-test spawn isolation, a concurrent
    # xdist worker importing a module that transitively touches hermes_cli.main
    # can briefly expose a partially-initialized module object here — one where
    # _detect_concurrent_hermes_instances isn't defined yet. A bare setattr
    # would raise AttributeError and error the (unrelated) test. The attribute
    # always exists once main.py finishes importing, so a no-op when it's
    # transiently absent is the correct, race-free default.
    monkeypatch.setattr(
        _cli_main,
        "_detect_concurrent_hermes_instances",
        lambda *_a, **_k: [],
        raising=False,
    )


@pytest.fixture(autouse=True)
def _suppress_live_ollama_discovery(request, monkeypatch):
    """Default ``fetch_ollama_models`` to ``[]`` for every test.

    ``list_authenticated_providers()`` probes a real local Ollama server for
    its "ollama" canonical row. On a developer machine that actually has
    ``ollama serve`` running, this makes the picker tests non-deterministic
    (the row appears/models differ depending on what's actually installed
    locally) and, when live models are found, ``_record_builtin_endpoint``
    marks ``localhost:11434`` as claimed — which then shadows any
    ``custom_providers`` fixture pointing at that same address (a realistic
    test fixture name/URL, since that's genuinely how users configure a
    custom Ollama endpoint). Autouse here keeps the suite deterministic
    regardless of the host machine's actual local servers.

    Tests that want to exercise real Ollama discovery re-patch
    ``fetch_ollama_models`` with their own return value.
    """
    try:
        from hermes_cli import models as _models_mod
    except Exception:
        return
    monkeypatch.setattr(_models_mod, "fetch_ollama_models", lambda *_a, **_k: [], raising=False)


@pytest.fixture(autouse=True)
def _suppress_live_custom_provider_discovery(request, monkeypatch):
    """Default ``fetch_api_models`` to ``None`` for every test.

    Pre-existing gap, unrelated to any one feature: ``custom_providers``
    fixtures across this suite commonly use ``http://localhost:11434/v1``
    as an example endpoint (a realistic choice — that's genuinely where
    users point a custom Ollama entry). Section 4's live-discovery-when-
    api-key-is-set behavior then calls the real ``fetch_api_models`` against
    that address; on a developer machine that actually has a local server
    reachable there, this silently replaces the fixture's synthetic model
    list with whatever's really installed, making the suite non-
    deterministic. Autouse here keeps it deterministic regardless of the
    host's local servers.

    Tests that want to exercise real discovery already re-patch
    ``fetch_api_models`` with their own fake explicitly — that local patch
    naturally overrides this default.
    """
    try:
        from hermes_cli import models as _models_mod
    except Exception:
        return
    monkeypatch.setattr(_models_mod, "fetch_api_models", lambda *_a, **_k: None, raising=False)
