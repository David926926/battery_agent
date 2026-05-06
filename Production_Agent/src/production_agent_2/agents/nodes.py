from __future__ import annotations

import json
from pathlib import Path
import re
from typing import Any

from production_agent_2.models.qwen_image import QwenImageClient
from production_agent_2.models.qwen_image_edit import QwenImageEditClient
from production_agent_2.models.qwen_text import QwenTextClient
from production_agent_2.schemas import CreativeDirection, GeneratedImage, PromptPlan, RunState, TaskBrief
from production_agent_2.tools.assets import assets_by_category, load_assets
from production_agent_2.tools.boards import create_reference_board
from production_agent_2.tools.composer import export_layer_bundle
from production_agent_2.tools.io import ensure_run_dirs, write_json


NEGATIVE_PROMPT = (
    "text, logo, product, battery, battery pack, packaging, watermark, chinese characters, letters, numbers, symbols, "
    "brand competitor, fake product, poster copy, CTA button, label, badge, human face, human body, mascot, cartoon, "
    "cyberpunk overload, cluttered foreground, low quality, blurry, duplicated object, unusable blank area"
)


def mark_running(state: RunState) -> RunState:
    state.status = "running"
    _emit_progress(state, {"stage": "running", "message": "生产任务开始。"})
    return state


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    results: list[str] = []
    for item in items:
        value = str(item or "").strip()
        if not value or value in seen:
            continue
        seen.add(value)
        results.append(value)
    return results


def _emit_progress(state: RunState, payload: dict[str, Any]) -> None:
    callback = state.progress_callback
    if callable(callback):
        callback(payload)


def _normalize_string_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return _dedupe([str(item).strip() for item in value if str(item).strip()])
    if isinstance(value, str):
        raw = value.strip()
        if not raw:
            return []
        if raw.startswith("[") and raw.endswith("]"):
            try:
                parsed = json.loads(raw)
                if isinstance(parsed, list):
                    return _normalize_string_list(parsed)
            except Exception:
                pass
        grouped_parts = re.split(r"(?:、{2,}|；{2,}|;{2,}|，{2,}|,{2,})", raw)
        grouped_parts = [re.sub(r"[、；;，,]", "", item).strip() for item in grouped_parts if item.strip()]
        if len(grouped_parts) > 1:
            return _dedupe(grouped_parts)
        parts = re.split(r"[\n,，;；]+", raw)
        parts = [item.strip() for item in parts if item.strip()]
        if parts and all(len(item) == 1 for item in parts) and len(parts) > 3:
            return ["".join(parts)]
        if len(parts) == 1 and "、" in raw:
            single_parts = [item.strip() for item in raw.split("、") if item.strip()]
            if single_parts and all(len(item) == 1 for item in single_parts) and len(single_parts) > 3:
                return ["".join(single_parts)]
            return _dedupe(single_parts)
        return _dedupe(parts)
    return []


def _tone_labels(tones: list[str]) -> list[str]:
    mapping = {
        "reliable": "可靠",
        "warm": "温暖",
        "professional": "专业",
        "tech": "科技",
        "young": "年轻",
    }
    return [mapping.get(item, item) for item in tones]


def _use_case_label(use_case: str) -> str:
    return {
        "main_detail": "主图/商详",
        "media_ad": "媒介投放素材",
    }.get(use_case, use_case)


def _build_source_summary(state: RunState) -> str:
    if state.request.generation_mode == "image_to_background":
        grouped = assets_by_category(state.assets)
        count = len(grouped.get("background", []))
        return f"用户上传了 {count} 张成品参考图，目标是清除前景后得到可继续设计的纯背景。"
    parts = [state.request.scene.strip(), state.request.background_prompt.strip()]
    return "；".join([item for item in parts if item]) or "用户希望生成一张可直接使用的纯背景底图。"


def collect_assets(state: RunState) -> RunState:
    assets = load_assets()
    state.assets = assets
    grouped = assets_by_category(assets)
    required = {"background"} if state.request.generation_mode == "image_to_background" else set()
    missing = sorted(required - set(grouped))
    if missing:
        state.errors.append(f"Missing source categories: {', '.join(missing)}")
    run_dirs = ensure_run_dirs(state.run_id)
    manifest = {
        "run_id": state.run_id,
        "asset_count": len(assets),
        "assets": [asset.model_dump() for asset in assets],
    }
    manifest_path = run_dirs["artifacts"] / "asset_manifest.json"
    write_json(manifest_path, manifest)
    state.artifacts["asset_manifest"] = str(manifest_path)
    _emit_progress(state, {"stage": "assets_collected", "asset_count": len(assets)})
    return state


def build_task_brief(state: RunState) -> RunState:
    request = state.request
    image_sample_count = max(1, int(request.direction_count or 1)) * max(1, int(request.variants_per_direction or 1))
    base_must_have = list(request.must_have)
    if request.key_appliances:
        base_must_have.append(f"关键用电器：{'、'.join(request.key_appliances)}")
    if request.reserve_component_space:
        base_must_have.append("预留干净可用的组件摆放空间")
    base_must_have.extend(["无文字", "无Logo", "无产品主体"])
    hard_constraints = [
        "只生成背景，不出现文字、Logo、品牌标识、水印或伪产品。",
        "不出现电池主体、包装、竞品元素或任何可单独识别的商品主体。",
        "画面必须可用于后续设计，保留自然空间和清晰层次。",
    ]
    if request.generation_mode == "image_to_background":
        hard_constraints.insert(0, "必须清除原海报中的人物、产品、促销条、按钮、角标和残影。")

    quality_constraints = [
        "保持高分辨率和完整空间透视。",
        f"视觉密度控制为 {request.visual_density}，中景不过度拥挤。",
    ]
    if request.background_prompt.strip():
        quality_constraints.append(f"补充描述：{request.background_prompt.strip()}")
    if request.target_market.strip():
        quality_constraints.append(f"目标国家/市场：{request.target_market.strip()}，场景元素、住宅环境、人物气质和用电器表达需要符合当地语境。")

    negative_constraints = _dedupe(
        list(request.must_avoid)
        + [
            "文字",
            "Logo",
            "产品主体",
            "包装",
            "水印",
            "伪产品",
            "竞品元素",
            "过强科技感",
            "卡通化",
        ]
    )
    brief = TaskBrief(
        generation_mode=request.generation_mode,
        use_case=request.use_case,
        workflow_type=request.workflow_type,
        audience=request.audience.strip() or "电商消费者",
        scene=request.scene.strip() or (request.background_prompt.strip() if request.generation_mode == "text_to_background" else "基于参考图提取背景"),
        key_appliances=_dedupe(list(request.key_appliances)),
        style=request.style.strip(),
        must_have=_dedupe(base_must_have),
        must_avoid=negative_constraints,
        selling_points=_dedupe(list(request.selling_points)),
        reserve_component_space=request.reserve_component_space,
        realism_level=request.realism_level,
        brand_tone_priority=request.brand_tone_priority,
        brand_tone="、".join(_tone_labels(request.brand_tone_priority)),
        visual_density=request.visual_density,
        aspect_ratio=request.aspect_ratio,
        output_size=request.output_size,
        direction_count=request.direction_count if request.generation_mode == "text_to_background" else 1,
        variants_per_direction=request.variants_per_direction if request.generation_mode == "text_to_background" else image_sample_count,
        source_summary=_build_source_summary(state),
        prompt_context=request.background_prompt.strip(),
        target_market=request.target_market.strip(),
        hard_constraints=hard_constraints,
        quality_constraints=quality_constraints,
        negative_constraints=negative_constraints,
    )
    state.task_brief = brief
    run_dirs = ensure_run_dirs(state.run_id)
    brief_path = run_dirs["artifacts"] / "task_brief.json"
    write_json(brief_path, brief.model_dump())
    state.artifacts["task_brief"] = str(brief_path)
    if request.generation_mode == "image_to_background":
        state.artifacts["image_to_background_sample_count"] = str(brief.variants_per_direction)
    _emit_progress(state, {"stage": "task_brief_ready", "task_brief": brief.model_dump()})
    return state


def build_reference_boards(state: RunState) -> RunState:
    run_dirs = ensure_run_dirs(state.run_id)
    if state.request.generation_mode != "image_to_background":
        boards_path = run_dirs["artifacts"] / "reference_boards.json"
        write_json(boards_path, [])
        state.artifacts["reference_boards"] = str(boards_path)
        state.reference_boards = []
        return state
    grouped = assets_by_category(state.assets)
    boards = []
    background_assets = grouped.get("background", [])
    if background_assets:
        boards.append(
            create_reference_board(
                board_id="background_board",
                category="background",
                assets=background_assets,
                output_path=run_dirs["boards"] / "style_board.png",
                note="将用户上传的成品参考图拼成参考板（无字幕），供模型学习风格与留白节奏。",
                with_captions=False,
            )
        )
    state.reference_boards = boards
    boards_path = run_dirs["artifacts"] / "reference_boards.json"
    write_json(boards_path, [board.model_dump() for board in boards])
    state.artifacts["reference_boards"] = str(boards_path)
    _emit_progress(state, {"stage": "reference_boards_ready", "board_count": len(boards)})
    return state


def _fallback_directions(brief: TaskBrief) -> list[CreativeDirection]:
    total = max(1, brief.direction_count)
    if brief.generation_mode == "image_to_background":
        return [
            CreativeDirection(
                direction_id="direction_01",
                title="提取背景",
                summary="基于上传图片清理前景并补全为可继续设计的纯背景。",
                visual_theme="背景提取",
                primary_palette=[],
                scene_elements=[],
                composition="",
                space_reservation="",
                fit_for_use_case="",
                risk_points=[],
                recommendation_reason="",
            )
        ]

    scene_elements = _dedupe(
        [brief.scene, brief.style]
        + brief.key_appliances[:3]
        + brief.selling_points[:2]
    )
    directions: list[CreativeDirection] = []
    palette_by_idx = [
        ["暖金色", "深棕色", "柔和琥珀光"],
        ["米白色", "浅木色", "暖灰色"],
        ["深蓝灰", "钨丝暖光", "柔和阴影"],
    ]
    themes = [
        "稳重留白型",
        "生活化层次型",
        "氛围光感型",
    ]
    for idx in range(total):
        direction_id = f"direction_{idx + 1:02d}"
        palette = palette_by_idx[idx % len(palette_by_idx)]
        theme = themes[idx % len(themes)]
        directions.append(
            CreativeDirection(
                direction_id=direction_id,
                title=f"{theme}{idx + 1}",
                summary=f"围绕{brief.scene}构建可直接商用的纯背景，强调{brief.brand_tone or '可靠、温暖、专业'}调性。",
                visual_theme=f"{theme}，突出商用背景质感与可后期摆放的空间感。",
                primary_palette=palette,
                scene_elements=scene_elements or ["纯背景空间感", "柔和光影层次"],
                composition="主体视觉重心偏中后景，保留一个干净区域供后续组件摆放，前中后景层次明确。",
                space_reservation="画面保留一块干净、不被装饰物打断的区域，用于后续产品、Logo 或文案组件摆放。",
                fit_for_use_case=f"适合{_use_case_label(brief.use_case)}，兼顾留白和转化导向。",
                risk_points=["留白不足会影响后续组件摆放", "装饰元素过多会削弱商用稳定性"],
                recommendation_reason="该方向保守稳妥，便于先把可用底图跑通，再继续细化视觉个性。",
            )
        )
    return directions


def _coerce_creative_directions(payload: dict[str, Any], brief: TaskBrief) -> list[CreativeDirection]:
    raw_directions = payload.get("creative_directions")
    if not isinstance(raw_directions, list):
        raise ValueError("creative_directions is missing")
    directions: list[CreativeDirection] = []
    for idx, item in enumerate(raw_directions[: max(1, brief.direction_count)], start=1):
        if not isinstance(item, dict):
            continue
        direction = CreativeDirection(
            direction_id=str(item.get("direction_id") or f"direction_{idx:02d}"),
            title=str(item.get("title") or f"创意方向{idx}"),
            summary=str(item.get("summary") or ""),
            visual_theme=str(item.get("visual_theme") or ""),
            primary_palette=_normalize_string_list(item.get("primary_palette")),
            scene_elements=_normalize_string_list(item.get("scene_elements")),
            composition=str(item.get("composition") or ""),
            space_reservation=str(item.get("space_reservation") or ""),
            fit_for_use_case=str(item.get("fit_for_use_case") or ""),
            risk_points=_normalize_string_list(item.get("risk_points")),
            recommendation_reason=str(item.get("recommendation_reason") or ""),
        )
        directions.append(direction)
    if not directions:
        raise ValueError("no valid creative directions")
    return directions


def generate_creative_directions(state: RunState) -> RunState:
    if not state.task_brief:
        state.errors.append("Task brief is missing")
        return state

    brief = state.task_brief
    directions: list[CreativeDirection]
    if state.request.generation_mode != "text_to_background":
        directions = _fallback_directions(brief)[:1]
    else:
        client = QwenTextClient()
        if not client.is_enabled():
            state.warnings.append("DASHSCOPE_API_KEY is missing, used fallback creative directions.")
            directions = _fallback_directions(brief)
        else:
            system_prompt = (
                "你是一名电商背景创意策划。你必须只输出 JSON，且 creative_directions 数量必须等于输入里的 direction_count。"
                "不要写 prompt，不要生成最终图像描述，只生成结构化创意方向。"
            )
            user_prompt = (
                "请基于下面的 task_brief，输出一个 JSON 对象，格式如下："
                '{"creative_directions":[{"direction_id":"direction_01","title":"","summary":"","visual_theme":"","primary_palette":[""],'
                '"scene_elements":[""],"composition":"","space_reservation":"","fit_for_use_case":"","risk_points":[""],"recommendation_reason":""}]}\n'
                f"task_brief={json.dumps(brief.model_dump(), ensure_ascii=False)}"
            )
            try:
                payload, resolved_model, attempts = client.generate_json(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    preferred_model=state.request.preferred_text_model,
                )
                directions = _coerce_creative_directions(payload, brief)
                state.artifacts["creative_direction_model"] = resolved_model
                write_json(
                    ensure_run_dirs(state.run_id)["artifacts"] / "creative_direction_model_attempts.json",
                    {"resolved_model": resolved_model, "attempted_models": attempts},
                )
            except Exception as exc:  # pragma: no cover
                state.warnings.append(f"Creative direction generation fell back to defaults: {exc}")
                directions = _fallback_directions(brief)

    state.creative_directions = directions
    run_dirs = ensure_run_dirs(state.run_id)
    directions_path = run_dirs["artifacts"] / "creative_directions.json"
    write_json(directions_path, [item.model_dump() for item in directions])
    state.artifacts["creative_directions"] = str(directions_path)
    _emit_progress(
        state,
        {
            "stage": "creative_directions_ready",
            "direction_count": len(directions),
            "creative_directions": [item.model_dump() for item in directions],
        },
    )
    return state


def _build_prompt_sections(brief: TaskBrief, direction: CreativeDirection) -> dict[str, str]:
    if brief.generation_mode == "image_to_background":
        bans = "；".join(brief.hard_constraints + [f"避免项：{'、'.join(brief.negative_constraints)}"])
        return {
            "输出规格": f"输出比例为{brief.aspect_ratio}，输出尺寸为{brief.output_size}。",
            "禁止项": bans,
        }

    task_goal = (
        f"为{_use_case_label(brief.use_case)}生成一张{brief.aspect_ratio}比例、尺寸为{brief.output_size}的纯背景底图。"
        "结果必须可直接进入后续排版或组件摆放。"
    )
    scene_description = (
        f"围绕“{brief.scene}”展开，目标人群是{brief.audience}。"
        f"关键用电器包括：{'、'.join(brief.key_appliances) or '未指定'}。"
        f"目标国家/市场：{brief.target_market or '未指定'}。"
        f"视觉主题为{direction.visual_theme}，优先体现的场景元素包括：{'、'.join(direction.scene_elements) or '空间层次、光影和环境氛围'}。"
    )
    structure = (
        f"{direction.composition} {direction.space_reservation}"
        if direction.space_reservation
        else direction.composition
    )
    style_and_light = (
        f"整体风格为{brief.style or '稳定、干净、适合商业后期的背景风格'}，"
        f"品牌调性优先级是{brief.brand_tone or '可靠、温暖、专业'}，"
        f"主色调参考：{'、'.join(direction.primary_palette) or '克制、商用、稳定'}。"
    )
    quality = "；".join(brief.quality_constraints + [f"适用说明：{direction.fit_for_use_case}", f"推荐理由：{direction.recommendation_reason}"])
    bans = "；".join(brief.hard_constraints + [f"避免项：{'、'.join(brief.negative_constraints)}"] + ([f"风险提醒：{'、'.join(direction.risk_points)}"] if direction.risk_points else []))
    return {
        "任务目标": task_goal,
        "主体场景描述": scene_description,
        "画面结构与空间预留": structure,
        "风格与光线": style_and_light,
        "质量约束": quality,
        "禁止项": bans,
    }


def build_prompt_plans(state: RunState) -> RunState:
    if not state.task_brief:
        state.errors.append("Task brief is missing")
        return state
    if not state.creative_directions:
        state.errors.append("Creative directions are missing")
        return state

    run_dirs = ensure_run_dirs(state.run_id)
    plans: list[PromptPlan] = []
    reference_paths = [item.path for item in state.reference_boards]
    model = (
        state.request.preferred_image_generation_model
        if state.request.generation_mode == "text_to_background"
        else state.request.preferred_image_edit_model
    )
    for direction in state.creative_directions:
        sections = _build_prompt_sections(state.task_brief, direction)
        prompt = "\n\n".join([f"{title}\n{content}" for title, content in sections.items()]).strip()
        plan = PromptPlan(
            direction_id=direction.direction_id,
            direction_title=direction.title,
            model=model,
            prompt=prompt,
            negative_prompt=NEGATIVE_PROMPT,
            reference_board_paths=reference_paths,
            size=state.task_brief.output_size,
            variants=state.task_brief.variants_per_direction,
            preferred_model=model,
            sections=sections,
        )
        plan_path = run_dirs["artifacts"] / f"prompt_plan_{direction.direction_id}.json"
        write_json(plan_path, plan.model_dump())
        plan.prompt_plan_path = str(plan_path)
        write_json(plan_path, plan.model_dump())
        plans.append(plan)

    state.prompt_plans = plans
    if plans:
        state.artifacts["prompt_plan"] = plans[0].prompt_plan_path or ""
    plans_path = run_dirs["artifacts"] / "prompt_plans.json"
    write_json(plans_path, [item.model_dump() for item in plans])
    state.artifacts["prompt_plans"] = str(plans_path)
    _emit_progress(
        state,
        {
            "stage": "prompt_plans_ready",
            "prompt_plan_count": len(plans),
            "prompt_plans": [item.model_dump() for item in plans],
        },
    )
    return state


def generate_backgrounds(state: RunState) -> RunState:
    if not state.prompt_plans:
        state.errors.append("Prompt plans are missing")
        return state

    run_dirs = ensure_run_dirs(state.run_id)
    if state.request.dry_run:
        state.warnings.append("Dry-run enabled, skipped background generation.")
        return state

    if state.request.generation_mode == "text_to_background":
        client = QwenImageClient()
        if not client.is_enabled():
            state.warnings.append(
                "DASHSCOPE_API_KEY is missing, skipped background generation. Configure the key and rerun."
            )
            return state

        output_index = 0
        for direction_idx, plan in enumerate(state.prompt_plans):
            try:
                items = client.generate(
                    reference_images=[],
                    prompt=plan.prompt,
                    negative_prompt=plan.negative_prompt,
                    size=plan.size,
                    variants=plan.variants,
                    base_seed=42 + direction_idx * 100,
                    output_dir=str(run_dirs["outputs"]),
                    filename_prefix=f"{plan.direction_id}_variant",
                    preferred_model=plan.preferred_model,
                )
                for item in items:
                    output_index += 1
                    state.generated_images.append(
                        GeneratedImage(
                            index=output_index,
                            direction_id=plan.direction_id,
                            direction_title=plan.direction_title,
                            variant_index=int(item["index"]),
                            seed=int(item["seed"]),
                            resolved_model=item.get("model"),
                            attempted_models=item.get("attempted_models", []),
                            prompt_plan_path=plan.prompt_plan_path,
                            path=item["path"],
                            source_url=item.get("source_url"),
                        )
                    )
                    _emit_progress(
                        state,
                        {
                            "stage": "image_generated",
                            "direction_id": plan.direction_id,
                            "direction_title": plan.direction_title,
                            "variant_index": int(item["index"]),
                            "path": item["path"],
                            "resolved_model": item.get("model"),
                        },
                    )
            except Exception as exc:  # pragma: no cover
                state.errors.append(f"{plan.direction_id}: {exc}")
        return state

    client = QwenImageEditClient()
    grouped = assets_by_category(state.assets)
    background_assets = grouped.get("background", [])
    if not client.is_enabled():
        state.warnings.append(
            "DASHSCOPE_API_KEY is missing, skipped background extraction. Configure the key and rerun."
        )
        return state
    if not background_assets:
        state.errors.append("No background reference images available for extraction.")
        return state

    source_asset = background_assets[0]
    if len(background_assets) > 1:
        state.warnings.append(
            f"Uploaded {len(background_assets)} reference image(s); currently using the first one for extraction."
        )
    output_index = 0
    for direction_idx, plan in enumerate(state.prompt_plans):
        total = max(1, plan.variants)
        for variant_idx in range(1, total + 1):
            output_index += 1
            seed = 42 + direction_idx * 100 + variant_idx - 1
            output_path = run_dirs["outputs"] / f"{plan.direction_id}_variant_{variant_idx:02d}_seed_{seed}.png"
            try:
                result = client.retouch(
                    image_path=source_asset.path,
                    instruction=plan.prompt,
                    output_path=str(output_path),
                    negative_prompt=plan.negative_prompt,
                    preferred_model=plan.preferred_model,
                )
                state.generated_images.append(
                    GeneratedImage(
                        index=output_index,
                        direction_id=plan.direction_id,
                        direction_title=plan.direction_title,
                        variant_index=variant_idx,
                        seed=seed,
                        resolved_model=result.get("model"),
                        attempted_models=result.get("attempted_models", []),
                        prompt_plan_path=plan.prompt_plan_path,
                        path=result.get("path", str(output_path)),
                        source_url=result.get("source_url"),
                    )
                )
                _emit_progress(
                    state,
                    {
                        "stage": "image_generated",
                        "direction_id": plan.direction_id,
                        "direction_title": plan.direction_title,
                        "variant_index": variant_idx,
                        "path": result.get("path", str(output_path)),
                        "resolved_model": result.get("model"),
                    },
                )
            except Exception as exc:  # pragma: no cover
                state.errors.append(f"{plan.direction_id} variant {variant_idx}: {exc}")
    return state


def select_primary_output(state: RunState) -> RunState:
    if not state.generated_images:
        state.selected_image = state.reference_boards[0].path if state.reference_boards else None
    else:
        state.selected_image = state.generated_images[0].path
    run_dirs = ensure_run_dirs(state.run_id)
    result_path = run_dirs["artifacts"] / "generation_result.json"
    write_json(
        result_path,
        {
            "task_brief": state.task_brief.model_dump() if state.task_brief else None,
            "creative_directions": [item.model_dump() for item in state.creative_directions],
            "prompt_plans": [item.model_dump() for item in state.prompt_plans],
            "selected_image": state.selected_image,
            "generated_images": [item.model_dump() for item in state.generated_images],
            "warnings": state.warnings,
            "errors": state.errors,
        },
    )
    state.artifacts["generation_result"] = str(result_path)
    _emit_progress(
        state,
        {
            "stage": "generation_completed",
            "selected_image": state.selected_image,
            "generated_count": len(state.generated_images),
        },
    )
    return state


def export_component_layers(state: RunState) -> RunState:
    run_dirs = ensure_run_dirs(state.run_id)
    grouped = assets_by_category(state.assets)
    export_dir = run_dirs["artifacts"] / "layers"
    bundle = export_layer_bundle(grouped, export_dir)
    layout_plan_path = run_dirs["artifacts"] / "layout_plan.json"
    write_json(layout_plan_path, bundle)
    state.artifacts["background_base"] = bundle["background_base"]
    state.artifacts["layout_hint"] = bundle["layout_hint"]
    state.artifacts["object_cluster"] = bundle["object_cluster"]
    state.artifacts["text_cluster"] = bundle["text_cluster"]
    state.artifacts["final_preview"] = bundle["final_preview"]
    state.artifacts["layout_plan"] = str(layout_plan_path)
    return state


def extract_background_layer(state: RunState) -> RunState:
    if not state.generated_images:
        return state
    run_dirs = ensure_run_dirs(state.run_id)
    client = QwenImageEditClient()
    if state.request.dry_run:
        state.warnings.append("Dry-run enabled, skipped background extraction.")
        return state
    if not client.is_enabled():
        state.warnings.append("DASHSCOPE_API_KEY is missing, skipped background extraction.")
        return state

    instruction = """
请基于输入海报，提取一张可用于后期继续设计的干净背景层。

硬性要求：
- 删除所有产品、电池、彩盒、人物、文字、logo、按钮、标签
- 删除额外电光、能量环、发光边缘、烟雾、镜头光斑等辅助特效
- 只保留完整、自然、可继续设计的背景空间
- 需要把被前景遮挡的区域合理补全
- 输出结果必须是一张干净的背景底图
""".strip()
    background_layers: dict[str, str] = {}
    for item in state.generated_images:
        output_path = run_dirs["artifacts"] / "layers" / f"background_clean_{item.index}.png"
        try:
            result = client.retouch(
                image_path=item.path,
                instruction=instruction,
                output_path=str(output_path),
            )
            background_layers[str(item.index)] = result.get("path", str(output_path))
        except Exception as exc:  # pragma: no cover
            state.errors.append(f"background extraction candidate {item.index}: {exc}")
    if background_layers:
        state.artifacts["background_clean"] = background_layers.get("1", next(iter(background_layers.values())))
        state.artifacts["background_clean_all"] = str(run_dirs["artifacts"] / "background_clean_map.json")
        write_json(run_dirs["artifacts"] / "background_clean_map.json", background_layers)
    return state


def extract_effects_layer(state: RunState) -> RunState:
    if not state.generated_images:
        return state
    run_dirs = ensure_run_dirs(state.run_id)
    client = QwenImageEditClient()
    if state.request.dry_run:
        state.warnings.append("Dry-run enabled, skipped effects extraction.")
        return state
    if not client.is_enabled():
        state.warnings.append("DASHSCOPE_API_KEY is missing, skipped effects extraction.")
        return state

    instruction = """
请基于输入海报，提取单独的辅助特效层。

硬性要求：
- 只保留电光、辉光、能量环、体积光、雾气、光束、边缘发光等辅助特效
- 删除所有人物、产品、电池、彩盒、文字、logo、按钮、标签
- 背景必须是纯黑色，方便后期用 Screen 或滤色模式叠加
- 输出结果是一张特效覆盖层，不要包含主体内容
""".strip()
    effects_layers: dict[str, str] = {}
    for item in state.generated_images:
        output_path = run_dirs["artifacts"] / "layers" / f"effects_overlay_black_{item.index}.png"
        try:
            result = client.retouch(
                image_path=item.path,
                instruction=instruction,
                output_path=str(output_path),
            )
            effects_layers[str(item.index)] = result.get("path", str(output_path))
        except Exception as exc:  # pragma: no cover
            state.errors.append(f"effects extraction candidate {item.index}: {exc}")
    if effects_layers:
        state.artifacts["effects_overlay"] = effects_layers.get("1", next(iter(effects_layers.values())))
        state.artifacts["effects_overlay_all"] = str(run_dirs["artifacts"] / "effects_overlay_map.json")
        write_json(run_dirs["artifacts"] / "effects_overlay_map.json", effects_layers)
    return state


def mark_completed(state: RunState) -> RunState:
    state.status = "completed" if not state.errors else "completed_with_errors"
    run_dirs = ensure_run_dirs(state.run_id)
    final_state_path = run_dirs["state"] / "final_state.json"
    state.artifacts["final_state"] = str(final_state_path)
    write_json(final_state_path, state.model_dump())
    return state


# Compatibility aliases for older imports / call sites.
build_creative_brief = build_task_brief
plan_prompt = build_prompt_plans
generate_background = generate_backgrounds
generate_main_visual = select_primary_output
