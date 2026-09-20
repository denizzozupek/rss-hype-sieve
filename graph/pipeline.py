from graph.nodes import (
    ingest_node,
    preprocess_text_node,
    judge_node,
    save_node,
    report_node,
)
from core.state import PipelineGraphState
from langgraph.graph import END, START
from langgraph.graph.state import StateGraph, CompiledStateGraph

def create_pipeline_graph() -> CompiledStateGraph:
    """Create a directed acyclic graph representing the pipeline workflow."""
    workflow = StateGraph(PipelineGraphState)

    workflow.add_node("ingest", ingest_node)
    workflow.add_node("preprocess_text", preprocess_text_node)
    workflow.add_node("judge", judge_node)
    workflow.add_node("save", save_node)
    workflow.add_node("report", report_node)

    workflow.add_edge(START, "ingest")
    workflow.add_edge("ingest", "preprocess_text")
    workflow.add_edge("preprocess_text", "judge")
    workflow.add_edge("judge", "save")
    workflow.add_edge("save", "report")
    workflow.add_edge("report", END)

    graph = workflow.compile()
    return graph

