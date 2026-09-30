from __future__ import annotations

import time

from .incidents import STATE
from .pii import summarize_text
from .tracing import get_langfuse_client, observe

CORPUS = {
    "refund": ["Refunds are available within 7 days with proof of purchase."],
    "monitoring": ["Metrics detect incidents, logs identify affected requests, traces localize the root cause."],
    "policy": ["Do not expose PII in logs. Use sanitized summaries only."],
}


@observe(name="retrieval", as_type="retriever", capture_input=False, capture_output=False)
def retrieve(message: str) -> list[str]:
    client = get_langfuse_client()
    if hasattr(client, "update_current_span"):
        try:
            client.update_current_span(
                input={"query": summarize_text(message)},
            )
        except Exception:
            pass

    if STATE["tool_fail"]:
        raise RuntimeError("Vector store timeout")
    if STATE["rag_slow"]:
        time.sleep(2.5)
    lowered = message.lower()
    for key, docs in CORPUS.items():
        if key in lowered:
            if hasattr(client, "update_current_span"):
                try:
                    client.update_current_span(
                        output={"docs": docs, "count": len(docs)},
                        metadata={"doc_count": len(docs)},
                    )
                except Exception:
                    pass
            return docs
    fallback_docs = ["No domain document matched. Use general fallback answer."]
    if hasattr(client, "update_current_span"):
        try:
            client.update_current_span(
                output={"docs": fallback_docs, "count": len(fallback_docs)},
                metadata={"doc_count": len(fallback_docs)},
            )
        except Exception:
            pass
    return fallback_docs

