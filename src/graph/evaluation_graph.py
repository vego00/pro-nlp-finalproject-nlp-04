from langgraph.graph import END, StateGraph

from agents.evaluation import evaluation_node
from state.base import GlobalState

evaluation_graph = StateGraph(GlobalState)
evaluation_graph.add_node("evaluate_document", evaluation_node)
evaluation_graph.set_entry_point("evaluate_document")
evaluation_graph.add_edge("evaluate_document", END)
evaluation_subgraph = evaluation_graph.compile()
