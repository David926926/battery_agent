from __future__ import annotations

from production_agent_2.models.qwen_image import QwenImageClient
from production_agent_2.models.qwen_image_edit import QwenImageEditClient
from production_agent_2.schemas import CreativeBrief, GeneratedImage, PromptPlan, RunState
from production_agent_2.tools.assets import assets_by_category, load_assets
from production_agent_2.tools.boards import create_reference_board
from production_agent_2.tools.composer import export_layer_bundle
from production_agent_2.tools.io import ensure_run_dirs, write_json


def mark_running(state: RunState) -> RunState:
    state.status = "running"
    return state


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
    return state


def build_creative_brief(state: RunState) -> RunState:
    if state.request.generation_mode == "text_to_background":
        brief = CreativeBrief(
            product_focus="根据用户提供的文字描述，直接生成一张可用的纯背景底图。",
            visual_tone=[
                "高质感背景氛围",
                "光影、色彩和空间感围绕文字描述展开",
            ],
            composition_rules=[
                "只生成背景，不出现人物、产品、电池、包装、文字、logo 或其他 component。",
                "画面要有完整空间感和后期可用性，避免空洞或过度装饰。",
                "严格围绕用户输入的场景、材质、氛围和色彩要求来生成。",
            ],
            text_rules=["结果图中不得出现任何真实文字、数字、字母或 logo。"],
            must_include=["与用户描述一致的背景氛围", "干净、完整、可直接使用的纯背景"],
            avoid=[
                "低清晰度",
                "出现文字/数字/字母/符号",
                "出现人物、产品、电池、包装、logo 或装饰主体",
                "和用户描述明显无关的场景元素",
            ],
        )
    else:
        brief = CreativeBrief(
            product_focus="基于输入的完整电商主图/海报，删除所有前景内容并补全遮挡区域，只保留干净的纯背景底图。",
            visual_tone=[
                "保留原图的色彩氛围、光影方向和空间层次",
                "背景补全自然干净，不带任何前景主体残影",
            ],
            composition_rules=[
                "删除人物、产品、电池、包装、文字、logo、促销条、按钮、标签、角标等所有前景元素。",
                "对被遮挡区域做连续、自然的背景补全，不留下轮廓、阴影、残字或主体痕迹。",
                "输出只允许包含背景本身，不为后期组件预留占位框，也不叠加任何组件。",
            ],
            text_rules=["输出图中不得出现任何真实文字、数字、字母或可识别符号。"],
            must_include=["完整、干净、可直接使用的纯背景", "与原图一致的环境光影和氛围连续性"],
            avoid=[
                "低清晰度",
                "出现文字/数字/字母/符号",
                "出现 logo 或品牌标识",
                "出现产品、电池、人物/脸/手/身体、包装或按钮标签",
                "出现前景残影、人物轮廓、商品边缘或局部未擦除区域",
            ],
        )
    state.brief = brief
    run_dirs = ensure_run_dirs(state.run_id)
    brief_path = run_dirs["artifacts"] / "creative_brief.json"
    write_json(brief_path, brief.model_dump())
    state.artifacts["creative_brief"] = str(brief_path)
    return state


def plan_prompt(state: RunState) -> RunState:
    if not state.brief:
        state.errors.append("Creative brief is missing")
        return state
    if state.request.generation_mode == "text_to_background":
        prompt = f"""
你是一名顶级电商背景设计师。请根据用户提供的文字需求，生成一张可直接使用的纯背景底图。

用户需求：
{state.request.background_prompt.strip()}

必须严格遵守：
- 只生成背景，不出现任何人物、产品、电池、包装、文字、数字、logo、按钮、标签或可单独识别的 component
- 画面需要具备完整的色彩、光影、空间层次和氛围感，不能只是空白渐变
- 背景风格、材质、场景、冷暖和情绪必须围绕用户描述展开
- 输出是 1:1 电商可用背景底图，允许高级质感，但不要出现主体或文案

补充要求：
- {state.brief.product_focus}
- 风格关键词：{'、'.join(state.brief.visual_tone)}
- 构图规则：{'；'.join(state.brief.composition_rules)}

请直接输出纯背景底图。
""".strip()
        negative_prompt = (
            "text, logo, product, battery, human, face, hand, body, packaging, chinese characters, letters, numbers, "
            "symbols, watermark, button, label, signage, extra props, foreground object, poster layout, headline, low quality"
        )
        model = "qwen-image-2.0-pro"
    else:
        prompt = f"""
你是一名电商海报后期修图师。输入图是一张完整海报，请你执行“前景清除 + 背景补全”，只输出纯背景。

必须严格遵守：
- 删除画面中的所有人物、产品、电池、包装、文字、数字、logo、按钮、标签、促销条、角标、徽章、发光主体和其他可识别前景元素
- 将被这些前景遮挡的区域补全成自然连续的背景，不能留下任何轮廓、阴影、边缘、残字或主体痕迹
- 保留原图的背景色彩、光感、景深、空间透视和氛围，不要新增新的主体或装饰组件
- 最终结果必须是一张干净的空背景，除了背景本身之外不能出现任何可单独识别的 component

补充要求：
- {state.brief.product_focus}
- 风格关键词：{'、'.join(state.brief.visual_tone)}
- 构图规则：{'；'.join(state.brief.composition_rules)}

请直接输出可用的纯背景底图。
""".strip()
        negative_prompt = (
            "text, logo, product, battery, human, face, hand, body, packaging, chinese characters, letters, numbers, symbols, "
            "watermark, button, label, signage, unreadable text, garbled text, promo banner, badge, extra props, object outline, "
            "subject silhouette, foreground residue, duplicate object, collage board, low quality"
        )
        model = "qwen-image-edit-max"
    plan = PromptPlan(
        model=model,
        prompt=prompt,
        negative_prompt=negative_prompt,
        reference_board_paths=[],
        size=state.request.output_size,
        variants=state.request.variants,
    )
    state.prompt_plan = plan
    run_dirs = ensure_run_dirs(state.run_id)
    plan_path = run_dirs["artifacts"] / "prompt_plan.json"
    write_json(plan_path, plan.model_dump())
    state.artifacts["prompt_plan"] = str(plan_path)
    return state


def generate_background(state: RunState) -> RunState:
    if not state.prompt_plan:
        state.errors.append("Prompt plan is missing")
        return state
    run_dirs = ensure_run_dirs(state.run_id)
    if state.request.dry_run:
        state.warnings.append("Dry-run enabled, skipped background extraction.")
    elif state.request.generation_mode == "text_to_background":
        client = QwenImageClient()
        if not client.is_enabled():
            state.warnings.append(
                "DASHSCOPE_API_KEY is missing, skipped background generation. Configure the key and rerun."
            )
        else:
            try:
                outputs = client.generate(
                    reference_images=[],
                    prompt=state.prompt_plan.prompt,
                    negative_prompt=state.prompt_plan.negative_prompt,
                    size=state.prompt_plan.size,
                    variants=state.prompt_plan.variants,
                    base_seed=42,
                    output_dir=str(run_dirs["outputs"]),
                )
                for idx, item in enumerate(outputs, start=1):
                    state.generated_images.append(
                        GeneratedImage(index=idx, path=item["path"], source_url=item.get("source_url"))
                    )
            except Exception as exc:  # pragma: no cover
                state.errors.append(str(exc))
    else:
        client = QwenImageEditClient()
        grouped = assets_by_category(state.assets)
        background_assets = grouped.get("background", [])
        if not client.is_enabled():
            state.warnings.append(
                "DASHSCOPE_API_KEY is missing, skipped background extraction. Configure the key and rerun."
            )
        elif not background_assets:
            state.errors.append("No background reference images available for extraction.")
        else:
            try:
                total = max(1, state.request.variants)
                source_asset = background_assets[0]
                if len(background_assets) > 1:
                    state.warnings.append(
                        f"Uploaded {len(background_assets)} reference image(s); currently using the first one to generate {total} background variant(s)."
                    )
                for idx in range(1, total + 1):
                    output_path = run_dirs["outputs"] / f"background_clean_{idx}.png"
                    result = client.retouch(
                        image_path=source_asset.path,
                        instruction=state.prompt_plan.prompt,
                        output_path=str(output_path),
                        negative_prompt=state.prompt_plan.negative_prompt,
                    )
                    state.generated_images.append(
                        GeneratedImage(index=idx, path=result.get("path", str(output_path)), source_url=result.get("source_url"))
                    )
            except Exception as exc:  # pragma: no cover
                state.errors.append(str(exc))
    return state


def generate_main_visual(state: RunState) -> RunState:
    if not state.generated_images:
        state.selected_image = state.reference_boards[0].path if state.reference_boards else None
    else:
        state.selected_image = state.generated_images[0].path
    run_dirs = ensure_run_dirs(state.run_id)
    result_path = run_dirs["artifacts"] / "generation_result.json"
    write_json(
        result_path,
        {
            "selected_image": state.selected_image,
            "generated_images": [item.model_dump() for item in state.generated_images],
            "warnings": state.warnings,
            "errors": state.errors,
        },
    )
    state.artifacts["generation_result"] = str(result_path)
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
