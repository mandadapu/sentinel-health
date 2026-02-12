import logging
from typing import Any

from src.graph.state import AgentState
from src.services.embedding_service import EmbeddingService
from src.services.protocol_store import ProtocolStore

logger = logging.getLogger(__name__)


async def rag_retriever_node(
    state: AgentState,
    *,
    protocol_store: ProtocolStore | None = None,
    embedding_service: EmbeddingService | None = None,
    top_k: int = 5,
) -> dict[str, Any]:
    """Retrieve similar clinical protocols to augment the reasoner's context.

    If protocol_store is None (Cloud SQL not configured), returns empty
    rag_context and the pipeline proceeds without RAG augmentation.
    """
    if protocol_store is None or embedding_service is None:
        logger.debug("RAG retrieval skipped — protocol_store or embedding_service not available")
        return {"rag_context": []}

    # Build query from extracted clinical data
    clinical_context = state.get("clinical_context", {})
    chief_complaint = clinical_context.get("chief_complaint", "")
    symptoms = clinical_context.get("symptoms", [])
    symptom_text = ", ".join(s.get("description", "") for s in symptoms if isinstance(s, dict))

    query_text = f"{chief_complaint}. Symptoms: {symptom_text}" if symptom_text else chief_complaint

    if not query_text.strip():
        return {"rag_context": []}

    # Generate embedding
    try:
        embedding = await embedding_service.embed(query_text)
    except Exception:
        logger.warning("Embedding generation failed — skipping RAG retrieval", exc_info=True)
        return {"rag_context": []}

    # Retrieve similar protocols
    try:
        protocols = await protocol_store.retrieve(embedding, top_k=top_k)
    except Exception:
        logger.warning("Protocol retrieval failed — skipping RAG", exc_info=True)
        return {"rag_context": []}

    logger.info(
        "RAG retrieved %d protocols for encounter %s",
        len(protocols),
        state.get("encounter_id", "unknown"),
    )

    return {"rag_context": protocols}
