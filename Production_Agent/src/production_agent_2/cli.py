from __future__ import annotations

import argparse

from production_agent_2.graph.workflow import build_workflow
from production_agent_2.schemas import RunRequest, RunState
from production_agent_2.tools.io import utc_timestamp


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Production_Agent_2.0")
    parser.add_argument("--variants", type=int, default=5)
    parser.add_argument("--size", default="1328*1328")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    state = RunState(
        run_id=utc_timestamp(),
        request=RunRequest(
            variants=args.variants,
            output_size=args.size,
            dry_run=args.dry_run,
        ),
    )
    workflow = build_workflow()
    final_state = workflow.invoke(state)
    if isinstance(final_state, dict):
        final_state = RunState.model_validate(final_state)
    print(f"Run ID: {final_state.run_id}")
    print(f"Status: {final_state.status}")
    print(f"Assets: {len(final_state.assets)}")
    print(f"Boards: {len(final_state.reference_boards)}")
    print(f"Selected output: {final_state.selected_image}")
    if final_state.errors:
        print("Errors:")
        for item in final_state.errors:
            print(f"- {item}")
    if final_state.warnings:
        print("Warnings:")
        for item in final_state.warnings:
            print(f"- {item}")


if __name__ == "__main__":
    main()
