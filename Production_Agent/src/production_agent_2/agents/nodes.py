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
    required = {"background", "layout", "object", "text"}
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
    grouped = assets_by_category(state.assets)
    boards = []
    layout_assets = grouped.get("layout", [])
    background_assets = grouped.get("background", [])
    style_assets = layout_assets + background_assets
    if style_assets:
        boards.append(
            create_reference_board(
                board_id="style_board",
                category="style",
                assets=style_assets,
                output_path=run_dirs["boards"] / "style_board.png",
                note="融合 Layout 与 Background 参考，提供整体构图、机位、景深和氛围。",
            )
        )
    if grouped.get("object"):
        boards.append(
            create_reference_board(
                board_id="object_board",
                category="object",
                assets=grouped["object"],
                output_path=run_dirs["boards"] / "object_board.png",
                note="保留产品主体、包装、角度与细节表现。",
            )
        )
    if grouped.get("text"):
        boards.append(
            create_reference_board(
                board_id="text_board",
                category="text",
                assets=grouped["text"],
                output_path=run_dirs["boards"] / "text_board.png",
                note="提供字体、文案层级和电商主图信息节奏。",
            )
        )
    state.reference_boards = boards
    boards_path = run_dirs["artifacts"] / "reference_boards.json"
    write_json(boards_path, [board.model_dump() for board in boards])
    state.artifacts["reference_boards"] = str(boards_path)
    return state


def build_creative_brief(state: RunState) -> RunState:
    brief = CreativeBrief(
        product_focus="以南孚电池包装与电池本体为绝对主角，生成一张可直接用于电商主图商详的方图。",
        visual_tone=[
            "高质感电商广告",
            "金色与黑色的品牌高级感",
            "蓝色能量光效",
            "干净、强对比、清晰层级",
        ],
        composition_rules=[
            "主体居中偏下或居中偏右，保留清晰文案区。",
            "背景必须服务于产品，不要喧宾夺主。",
            "画面只保留一个主场景，不拼贴，不出现多余产品。",
            "最终图像适配 1:1 电商封面，信息一眼可读。",
        ],
        text_rules=[
            f"主标题使用中文并保持可读，默认主标题为“{state.request.primary_copy}”。",
            f"副标题或卖点文案默认为“{state.request.secondary_copy}”。",
            "允许补充 2-3 个短卖点标签，但不要堆砌大段文字。",
            "文字与主体不要重叠，不要出现错别字或乱码。",
        ],
        must_include=[
            "真实可信的南孚电池包装细节",
            "可商用的电商主图排版",
            "明确的品牌感与购买引导气质",
        ],
        avoid=[
            "低清晰度",
            "产品数量错误",
            "包装文字模糊",
            "多余手臂、额外物体、畸形反光",
            "错误中文、扭曲字体、强烈 AI 拼贴痕迹",
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
    board_paths = [board.path for board in state.reference_boards][:3]
    prompt = f"""
你是一名顶级电商海报设计师。请严格参考输入的三张素材参考板，生成一张可直接交付的“主图商详”成图。

输入图职责：
- Image 1 是 layout + background 参考：决定版式结构、信息分区、留白、背景氛围和第一眼视觉节奏
- Image 2 是 object 参考：必须使用其中的产品主体、彩盒、人物或产品相关物料，不能替换成别的产品
- Image 3 是 text 参考：必须沿用其中的中文标题、卖点标签、文字风格和层级关系，禁止乱改字

硬性要求：
- 最终图必须是一张完整的电商主图商详，不是拼贴参考板
- 必须明显用上我提供的 object、layout、text、background 素材语义
- 构图优先服从 layout 参考，layout 非常重要，决定整体美感
- 产品主体必须清晰、占比高、具有商业广告质感
- 文字必须清晰可读，不能错字、乱码、胡乱生成新字
- 必须保留南孚品牌感，不能改成别的品牌
- 允许对背景光影、质感、空间感做高级化处理，但不能破坏版式

内容要求：
- 主标题文案：{state.request.primary_copy}
- 副标题文案：{state.request.secondary_copy}
- 卖点关键词：{'、'.join(state.request.selling_points)}
- 只有上面明确给出的主标题、副标题、卖点关键词可以出现在画面文字里
- 不要把“高颜值主图”“信息层级清晰”这类控制要求直接渲染成图片文字

风格要求：
- {state.brief.product_focus}
- 风格关键词：{'、'.join(state.brief.visual_tone)}
- 构图规则：{'；'.join(state.brief.composition_rules)}
- 文字规则：{'；'.join(state.brief.text_rules)}

请输出一张 1:1、适合电商首屏、第一眼高级且清楚的主图商详海报。
""".strip()
    negative_prompt = (
        "wrong brand, wrong product, replace supplied assets, weak layout, unreadable chinese text, typo, garbled text, "
        "messy composition, collage board, low quality, duplicate product, extra objects, deformed battery, watermark"
    )
    plan = PromptPlan(
        model="qwen-image-2.0-pro",
        prompt=prompt,
        negative_prompt=negative_prompt,
        reference_board_paths=board_paths,
        size=state.request.output_size,
        variants=state.request.variants,
        base_seed=state.request.seed,
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
    client = QwenImageClient()
    if state.request.dry_run:
        state.warnings.append("Dry-run enabled, skipped remote image generation.")
    elif not client.is_enabled():
        state.warnings.append(
            "DASHSCOPE_API_KEY is missing, skipped remote image generation. Configure the key and rerun."
        )
    elif not state.prompt_plan.reference_board_paths:
        state.errors.append("No reference boards available for generation.")
    else:
        try:
            outputs = client.generate(
                reference_images=state.prompt_plan.reference_board_paths,
                prompt=state.prompt_plan.prompt,
                negative_prompt=state.prompt_plan.negative_prompt,
                size=state.prompt_plan.size,
                variants=state.prompt_plan.variants,
                base_seed=state.prompt_plan.base_seed,
                output_dir=str(run_dirs["outputs"]),
            )
            for idx, item in enumerate(outputs, start=1):
                state.generated_images.append(
                    GeneratedImage(index=idx, path=item["path"], source_url=item.get("source_url"))
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
