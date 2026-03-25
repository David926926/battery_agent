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
                nodes.build_reference_boards,
                nodes.build_creative_brief,
                nodes.plan_prompt,
                nodes.generate_background,
                nodes.generate_main_visual,
                nodes.export_component_layers,
                nodes.extract_background_layer,
                nodes.extract_effects_layer,
                nodes.mark_completed,
            ]
        )

    graph = StateGraph(RunState)
    graph.add_node("mark_running", nodes.mark_running)
    graph.add_node("collect_assets", nodes.collect_assets)
    graph.add_node("build_reference_boards", nodes.build_reference_boards)
    graph.add_node("build_creative_brief", nodes.build_creative_brief)
    graph.add_node("plan_prompt", nodes.plan_prompt)
    graph.add_node("generate_background", nodes.generate_background)
    graph.add_node("generate_main_visual", nodes.generate_main_visual)
    graph.add_node("export_component_layers", nodes.export_component_layers)
    graph.add_node("extract_background_layer", nodes.extract_background_layer)
    graph.add_node("extract_effects_layer", nodes.extract_effects_layer)
    graph.add_node("mark_completed", nodes.mark_completed)

    graph.add_edge(START, "mark_running")
    graph.add_edge("mark_running", "collect_assets")
    graph.add_edge("collect_assets", "build_reference_boards")
    graph.add_edge("build_reference_boards", "build_creative_brief")
    graph.add_edge("build_creative_brief", "plan_prompt")
    graph.add_edge("plan_prompt", "generate_background")
    graph.add_edge("generate_background", "generate_main_visual")
    graph.add_edge("generate_main_visual", "export_component_layers")
    graph.add_edge("export_component_layers", "extract_background_layer")
    graph.add_edge("extract_background_layer", "extract_effects_layer")
    graph.add_edge("extract_effects_layer", "mark_completed")
    graph.add_edge("mark_completed", END)
    return graph.compile()
