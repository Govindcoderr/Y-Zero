# backend/utils/coordination_log.py
"""
Coordination log utilities — Y-Zero
Provides helper functions to read and summarize the coordination log, which tracks the outputs of each subgraph phase (discovery, builder, configurator) and any errors that occur. 
This allows the Supervisor agent to make informed decisions about routing and to provide context to the Responder agent for generating user-facing responses.
Provides deterministic routing helpers so the Supervisor doesn't need an
LLM call — it just reads the log to decide what runs next.
"""

from typing import List, Optional, Literal
from backend.types.coordination import CoordinationLogEntry, SubgraphPhase

RoutingDecision = Literal["discovery", "builder", "configurator", "responder"]


# ── Log query helpers ─────────────────────────────────────────────────────────

def get_last_completed_phase(log: List[CoordinationLogEntry]) -> Optional[SubgraphPhase]:
    """Return the phase of the most recent completed entry."""
    if not log:
        return None
    for entry in reversed(log):
        if entry.status == "completed":
            return entry.phase
    return None


def get_phase_entry(
    log: List[CoordinationLogEntry],
    phase: SubgraphPhase,
) -> Optional[CoordinationLogEntry]:
    """Return the completed entry for a specific phase (first match)."""
    for entry in log:
        if entry.phase == phase and entry.status == "completed":
            return entry
    return None


def has_phase_completed(
    log: List[CoordinationLogEntry],
    phase: SubgraphPhase,
) -> bool:
    return get_phase_entry(log, phase) is not None


def has_error_in_log(log: List[CoordinationLogEntry]) -> bool:
    return any(e.status == "error" for e in log)


def get_error_entry(log: List[CoordinationLogEntry]) -> Optional[CoordinationLogEntry]:
    for entry in log:
        if entry.status == "error":
            return entry
    return None


def get_builder_output(log: List[CoordinationLogEntry]) -> Optional[str]:
    """Return builder's output text (human-readable workflow description)."""
    entry = get_phase_entry(log, "builder")
    return entry.output if entry and entry.output else None


def get_configurator_output(log: List[CoordinationLogEntry]) -> Optional[str]:
    """Return configurator's output text (setup instructions)."""
    entry = get_phase_entry(log, "configurator")
    return entry.output if entry and entry.output else None


# ── Deterministic routing ─────────────────────────────────────────────────────

def get_next_phase_from_log(log: List[CoordinationLogEntry]) -> RoutingDecision:
    """
    Deterministic routing after a subgraph completes.
    Mirrors n8n's getNextPhaseFromLog().

    Sequence: discovery → builder → configurator → responder
    Errors always route to responder so the user gets feedback.
    """
    if has_error_in_log(log):
        return "responder"

    last_phase = get_last_completed_phase(log)

    if last_phase == "discovery":
        return "builder"
    if last_phase == "builder":
        return "configurator"
    if last_phase == "configurator":
        return "responder"

    # No phases completed yet — supervisor decides
    return "responder"


def summarize_coordination_log(log: List[CoordinationLogEntry]) -> str:
    """Human-readable summary of completed phases (for debugging)."""
    if not log:
        return "No phases completed"
    completed = [e for e in log if e.status == "completed"]
    return " → ".join(f"{e.phase}: {e.summary}" for e in completed)