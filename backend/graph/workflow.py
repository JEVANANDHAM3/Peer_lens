from __future__ import annotations

from typing import Any, Dict

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

import backend.graph.nodes as graph_nodes
import backend.graph.routing as graph_routing


def _parallel_specialist_reviews(state: Dict[str, Any]) -> Dict[str, Any]:
    st = dict(state)
    rigor_res = graph_nodes.run_rigor_node(dict(st))
    clarity_res = graph_nodes.run_clarity_node(dict(st))
    novelty_res = graph_nodes.run_novelty_node(dict(st))
    return {
        **st,
        "rigor_review": rigor_res.get("rigor_review"),
        "clarity_review": clarity_res.get("clarity_review"),
        "novelty_review": novelty_res.get("novelty_review"),
        "retrieved_documents": novelty_res.get("retrieved_documents", []),
        "retrieval_history": novelty_res.get("retrieval_history", []),
        "status": "reviewing",
    }


def build_review_graph(use_checkpointing: bool = False):
    builder = StateGraph(dict)

    builder.add_node("initialize_review", graph_nodes.initialize_review)
    builder.add_node("prepare_review_context", graph_nodes.prepare_review_context)
    builder.add_node("parallel_specialist_reviews", _parallel_specialist_reviews)
    builder.add_node("run_meta_review_node", graph_nodes.run_meta_review_node)
    builder.add_node("rerun_rigor", graph_nodes.rerun_specialist_node("rigor"))
    builder.add_node("rerun_clarity", graph_nodes.rerun_specialist_node("clarity"))
    builder.add_node("rerun_novelty", graph_nodes.rerun_specialist_node("novelty"))
    builder.add_node("human_feedback", graph_nodes.process_human_feedback)
    builder.add_node("finalize_review", graph_nodes.finalize_review)

    builder.add_edge(START, "initialize_review")
    builder.add_edge("initialize_review", "prepare_review_context")
    builder.add_edge("prepare_review_context", "parallel_specialist_reviews")
    builder.add_edge("parallel_specialist_reviews", "run_meta_review_node")

    builder.add_conditional_edges(
        "run_meta_review_node",
        graph_routing.route_after_meta,
        {
            "rerun_rigor": "rerun_rigor",
            "rerun_clarity": "rerun_clarity",
            "rerun_novelty": "rerun_novelty",
            "human_feedback": "human_feedback",
            "finalize_review": "finalize_review",
        },
    )

    builder.add_edge("rerun_rigor", "run_meta_review_node")
    builder.add_edge("rerun_clarity", "run_meta_review_node")
    builder.add_edge("rerun_novelty", "run_meta_review_node")

    builder.add_conditional_edges(
        "human_feedback",
        graph_routing.route_after_human_feedback,
        {
            "run_meta_review_node": "run_meta_review_node",
            "rerun_rigor": "rerun_rigor",
            "rerun_clarity": "rerun_clarity",
            "rerun_novelty": "rerun_novelty",
            "finalize_review": "finalize_review",
        },
    )

    builder.add_edge("finalize_review", END)

    if use_checkpointing:
        return builder.compile(checkpointer=MemorySaver())
    return builder.compile()


async def run_review_graph(review_id: str, paper_id: str, review_mode: str = "agentic_rag", use_checkpointing: bool = False) -> Dict[str, Any]:
    graph = build_review_graph(use_checkpointing=use_checkpointing)
    state: Dict[str, Any] = {
        "review_id": review_id,
        "paper_id": paper_id,
        "review_mode": review_mode,
    }
    if use_checkpointing:
        output = await graph.ainvoke(state, config={"configurable": {"thread_id": review_id}})
        return output
    output = await graph.ainvoke(state)
    return output


def run_review_graph_sync(review_id: str, paper_id: str, review_mode: str = "agentic_rag", use_checkpointing: bool = False) -> Dict[str, Any]:
    graph = build_review_graph(use_checkpointing=use_checkpointing)
    state: Dict[str, Any] = {
        "review_id": review_id,
        "paper_id": paper_id,
        "review_mode": review_mode,
    }
    if use_checkpointing:
        return graph.invoke(state, config={"configurable": {"thread_id": review_id}})
    return graph.invoke(state)
