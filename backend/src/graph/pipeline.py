import functools

from langgraph.graph import END, StateGraph

from src.audit.writer import AuditWriter
from src.config import Settings
from src.graph.nodes.extractor import extractor_node
from src.graph.nodes.rag_retriever import rag_retriever_node
from src.graph.nodes.reasoner import reasoner_node
from src.graph.nodes.sentinel import sentinel_node
from src.graph.state import AgentState
from src.routing.classifier import ClinicalClassifier
from src.routing.router import ModelRouter
from src.services.anthropic_client import AnthropicClient
from src.services.protocol_store import ProtocolStore
from src.services.sidecar_client import SidecarClient


def build_pipeline(
    anthropic_client: AnthropicClient,
    audit_writer: AuditWriter,
    classifier: ClinicalClassifier,
    router: ModelRouter,
    settings: Settings,
    sidecar_client: SidecarClient | None = None,
    protocol_store: ProtocolStore | None = None,
):
    """Build and compile the LangGraph triage pipeline."""

    bound_extractor = functools.partial(
        extractor_node,
        anthropic_client=anthropic_client,
        audit_writer=audit_writer,
        sidecar_client=sidecar_client,
    )
    bound_rag_retriever = functools.partial(
        rag_retriever_node,
        protocol_store=protocol_store,
        anthropic_client=anthropic_client,
    )
    bound_reasoner = functools.partial(
        reasoner_node,
        anthropic_client=anthropic_client,
        audit_writer=audit_writer,
        sidecar_client=sidecar_client,
    )
    bound_sentinel = functools.partial(
        sentinel_node,
        anthropic_client=anthropic_client,
        audit_writer=audit_writer,
        settings=settings,
        sidecar_client=sidecar_client,
    )

    async def classify_and_route(state: AgentState) -> dict:
        classification = await classifier.classify(state["raw_input"])
        routing = router.route(state["raw_input"], classification)
        return {"routing_metadata": routing}

    graph = StateGraph(AgentState)

    graph.add_node("classify_and_route", classify_and_route)
    graph.add_node("extractor", bound_extractor)
    graph.add_node("rag_retriever", bound_rag_retriever)
    graph.add_node("reasoner", bound_reasoner)
    graph.add_node("sentinel", bound_sentinel)

    graph.set_entry_point("classify_and_route")
    graph.add_edge("classify_and_route", "extractor")
    graph.add_edge("extractor", "rag_retriever")
    graph.add_edge("rag_retriever", "reasoner")
    graph.add_edge("reasoner", "sentinel")
    graph.add_edge("sentinel", END)

    return graph.compile()
