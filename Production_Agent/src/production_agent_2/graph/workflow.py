from __future__ import annotations

from collections.abc import Callable

from production_agent_2.agents import nodes
from production_agent_2.schemas import RunState


NodeFn = Callable[[RunState], RunState]


class SequentialWorkflow:
    def __init__(self, steps: list[NodeFn]) -> None:
        self._steps = steps

    def invoke(self, state: RunState) -> RunState:
        current = state
        for step in self._steps:
            current = step(current)
        return current


def build_workflow() -> SequentialWorkflow:
    try:
        from langgraph.graph import END, START, StateGraph
    except ImportError:
        return SequentialWorkflow(
            [
                nodes.mark_running,
                nodes.collect_assets,
                nodes.build_task_brief,
                nodes.build_reference_boards,
                nodes.generate_creative_directions,
                nodes.build_prompt_plans,
                nodes.generate_backgrounds,
                nodes.select_primary_output,
                nodes.mark_completed,
            ]
        )

    graph = StateGraph(RunState)
    graph.add_node("mark_running", nodes.mark_running)
    graph.add_node("collect_assets", nodes.collect_assets)
    graph.add_node("build_task_brief", nodes.build_task_brief)
    graph.add_node("build_reference_boards", nodes.build_reference_boards)
    graph.add_node("generate_creative_directions", nodes.generate_creative_directions)
    graph.add_node("build_prompt_plans", nodes.build_prompt_plans)
    graph.add_node("generate_backgrounds", nodes.generate_backgrounds)
    graph.add_node("select_primary_output", nodes.select_primary_output)
    graph.add_node("mark_completed", nodes.mark_completed)

    graph.add_edge(START, "mark_running")
    graph.add_edge("mark_running", "collect_assets")
    graph.add_edge("collect_assets", "build_task_brief")
    graph.add_edge("build_task_brief", "build_reference_boards")
    graph.add_edge("build_reference_boards", "generate_creative_directions")
    graph.add_edge("generate_creative_directions", "build_prompt_plans")
    graph.add_edge("build_prompt_plans", "generate_backgrounds")
    graph.add_edge("generate_backgrounds", "select_primary_output")
    graph.add_edge("select_primary_output", "mark_completed")
    graph.add_edge("mark_completed", END)
    return graph.compile()
