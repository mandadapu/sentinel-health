import functools

from langgraph.graph import END, StateGraph

from src.audit.writer import AuditWriter
from src.config import Settings
from src.graph.nodes.extractor import extractor_node
from src.graph.nodes.reasoner import reasoner_node
from src.graph.nodes.sentinel import sentinel_node
from src.graph.state import AgentState
from src.routing.classifier import ClinicalClassifier
from src.routing.router import ModelRouter
from src.services.anthropic_client import AnthropicClient


def build_pipeline(
    anthropic_client: AnthropicClient,
    audit_writer: AuditWriter,
    classifier: ClinicalClassifier,
    router: ModelRouter,
    settings: Settings,
):
    """Build and compile the LangGraph triage pipeline."""

    bound_extractor = functools.partial(
        extractor_node,
        anthropic_client=anthropic_client,
        audit_writer=audit_writer,
    )
    bound_reasoner = functools.partial(
        reasoner_node,
        anthropic_client=anthropic_client,
        audit_writer=audit_writer,
    )
    bound_sentinel = functools.partial(
        sentinel_node,
        anthropic_client=anthropic_client,
        audit_writer=audit_writer,
        settings=settings,
    )

    async def classify_and_route(state: AgentState) -> dict:
        classification = await classifier.classify(state["raw_input"])
        routing = router.route(state["raw_input"], classification)
        return {"routing_metadata": routing}

    graph = StateGraph(AgentState)

    graph.add_node("classify_and_route", classify_and_route)
    graph.add_node("extractor", bound_extractor)
    graph.add_node("reasoner", bound_reasoner)
    graph.add_node("sentinel", bound_sentinel)

    graph.set_entry_point("classify_and_route")
    graph.add_edge("classify_and_route", "extractor")
    graph.add_edge("extractor", "reasoner")
    graph.add_edge("reasoner", "sentinel")
    graph.add_edge("sentinel", END)

    return graph.compile()
