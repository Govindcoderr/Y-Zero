# backend/agents/responder.py
"""
Responder Agent — Y-Zero

Mirrors Y-Zero's ResponderAgent pattern:
  - Reads coordination log for builder and configurator outputs
  - Reads discovery context for nodes found
  - Builds an [Internal Context] message so the LLM can synthesise a clean user response
  - Applies strict communication style (no emojis, concise, action-oriented)
  - Handles error entries from the coordination log prominently
  - Handles state-management entries (compact / clear)
"""

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import SystemMessage, HumanMessage
from typing import Dict, Any, List, Optional

from backend.prompt.agents.responder_prompt import get_responder_prompt
from backend.types.coordination import CoordinationLogEntry
from backend.types.workflow import SimpleWorkflow


# ── Coordination log helpers (mirrors n8n's coordination-log.ts) ──────────────

def _get_phase_entry(log: List[CoordinationLogEntry], phase: str) -> Optional[CoordinationLogEntry]:
    """Return the most recent completed entry for a given phase."""
    for entry in reversed(log):
        if entry.phase == phase and entry.status == "completed":
            return entry
    return None


def _get_error_entry(log: List[CoordinationLogEntry]) -> Optional[CoordinationLogEntry]:
    """Return the first error entry in the log, if any."""
    for entry in log:
        if entry.status == "error":
            return entry
    return None


def _get_builder_output(log: List[CoordinationLogEntry]) -> Optional[str]:
    entry = _get_phase_entry(log, "builder")
    return entry.output if entry and entry.output else None


def _get_configurator_output(log: List[CoordinationLogEntry]) -> Optional[str]:
    entry = _get_phase_entry(log, "configurator")
    return entry.output if entry and entry.output else None


def _get_discovery_summary(log: List[CoordinationLogEntry]) -> Optional[str]:
    """Extract discovery metadata (nodes found) from the coordination log."""
    entry = _get_phase_entry(log, "discovery")
    if not entry:
        return None
    meta = entry.metadata or {}
    techniques = meta.get("techniques", [])
    confidence = meta.get("confidence", 0)
    if techniques:
        return f"Identified techniques: {', '.join(techniques)} (confidence: {confidence:.0%})"
    return entry.summary or None


# ── Context message builder (mirrors n8n's buildContextMessage) ───────────────

def _build_context_message(
    coordination_log: List[CoordinationLogEntry],
    workflow: SimpleWorkflow,
    previous_summary: Optional[str] = None,
    categorization=None,
) -> Optional[HumanMessage]:
    """
    Assemble [Internal Context] that the responder LLM reads to craft its reply.

    Priority order (same as n8n):
      1. Previous conversation summary (from compaction)
      2. State management actions (compact/clear)
      3. Error entries — surface prominently
      4. Discovery context (nodes found, techniques)
      5. Builder output (workflow structure summary)
      6. Configurator output (setup instructions)
    """
    parts: List[str] = []

    # 1. Previous conversation summary
    if previous_summary:
        parts.append(
            f"**Previous Conversation Summary:**\n{previous_summary}"
        )

    # 2. State management actions
    state_mgmt = _get_phase_entry(coordination_log, "state_management")
    if state_mgmt:
        parts.append(f"**State Management:** {state_mgmt.summary}")

    # 3. Error entries — show prominently
    error_entry = _get_error_entry(coordination_log)
    if error_entry:
        parts.append(
            f"**Error:** An error occurred in the {error_entry.phase} phase: {error_entry.summary}"
        )
        parts.append(
            "Please apologise to the user and explain that something went wrong "
            "while building their workflow."
        )

    # 4. Discovery context
    discovery_summary = _get_discovery_summary(coordination_log)
    if discovery_summary:
        parts.append(f"**Discovery:** {discovery_summary}")

    # Also mention categorization techniques if available
    if categorization and hasattr(categorization, "techniques") and categorization.techniques:
        technique_names = [
            t.value if hasattr(t, "value") else str(t)
            for t in categorization.techniques
        ]
        parts.append(f"**Workflow type:** {', '.join(technique_names)}")

    # 5. Builder output
    builder_output = _get_builder_output(coordination_log)
    if builder_output:
        parts.append(f"**Builder:** {builder_output}")
    elif workflow.nodes:
        # Fallback — describe nodes if builder left no explicit output
        node_list = " → ".join(
            f"{n.name} ({n.type})" for n in workflow.nodes
        )
        parts.append(
            f"**Workflow:** {len(workflow.nodes)} nodes created\n{node_list}"
        )

    # 6. Configurator output (setup instructions)
    configurator_output = _get_configurator_output(coordination_log)
    if configurator_output:
        parts.append(f"**Configuration:**\n{configurator_output}")

    if not parts:
        return None

    content = "[Internal Context — use this to craft your response]\n\n" + "\n\n".join(parts)
    return HumanMessage(content=content)


# ── ResponderAgent ─────────────────────────────────────────────────────────────

class ResponderAgent:
    """
    Responder Agent — final step in the Y-Zero pipeline.

    Reads context from the coordination log and workflow state,
    then generates a clean, user-facing response.

    Mirrors n8n's ResponderAgent:
      packages/@n8n/ai-workflow-builder.ee/src/agents/responder.agent.ts
    """

    def __init__(self, llm: BaseChatModel):
        self.llm = llm
        self._system_prompt = get_responder_prompt()

    async def generate_response(self, state: Dict[str, Any]) -> str:
        """
        Generate a user-facing response from the current pipeline state.

        Args:
            state: WorkflowState dict containing:
                - messages: conversation history
                - workflow_json: SimpleWorkflow object
                - coordination_log: list of CoordinationLogEntry
                - categorization: PromptCategorization (optional)
                - conversation_summary: previous compaction summary (optional)

        Returns:
            Plain string response to send to the user.
        """
        workflow: SimpleWorkflow = state.get("workflow_json")
        coordination_log: List[CoordinationLogEntry] = state.get("coordination_log", [])
        categorization = state.get("categorization")
        previous_summary = state.get("conversation_summary")

        # Build internal context message
        context_msg = _build_context_message(
            coordination_log=coordination_log,
            workflow=workflow,
            previous_summary=previous_summary,
            categorization=categorization,
        )

        # Build message list: system + conversation history + [Internal Context]
        messages_to_send = [SystemMessage(content=self._system_prompt)]

        # Append recent conversation messages for context
        conversation = state.get("messages", [])
        for msg in conversation:
            if isinstance(msg, dict):
                role = msg.get("role", "")
                content = msg.get("content", "")
                if role == "user":
                    messages_to_send.append(HumanMessage(content=content))
                # Skip prior assistant messages — we're generating a new one
            else:
                # LangChain message object
                msg_type = getattr(msg, "type", "")
                if msg_type == "human":
                    messages_to_send.append(msg)

        # Append the internal context (if any) as final human message
        if context_msg:
            messages_to_send.append(context_msg)

        # Invoke LLM
        try:
            response = await self.llm.ainvoke(messages_to_send)
            return response.content.strip()
        except Exception as e:
            print(f"⚠️  Responder LLM call failed: {e}")
            return self._fallback_response(workflow, coordination_log)

    def _fallback_response(
        self,
        workflow: SimpleWorkflow,
        coordination_log: List[CoordinationLogEntry],
    ) -> str:
        """Safe fallback when LLM call fails."""
        error_entry = _get_error_entry(coordination_log)
        if error_entry:
            return (
                f"Something went wrong while building your workflow "
                f"(in the {error_entry.phase} phase). "
                "Please try again or rephrase your request."
            )

        if workflow and workflow.nodes:
            node_count = len(workflow.nodes)
            connection_count = sum(
                len(arr[0]) if arr else 0
                for conns in workflow.connections.values()
                for arr in conns.values()
            )
            return (
                f"Your workflow has been built with {node_count} node(s) "
                f"and {connection_count} connection(s). "
                "Let me know if you'd like to adjust anything."
            )

        return (
            "I've finished processing your request. "
            "Let me know if you'd like to make any changes."
        )