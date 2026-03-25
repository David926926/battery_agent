from __future__ import annotations

import base64
import importlib.util
import io
import json
import os
import sys
import zipfile
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any

import streamlit as st
from dotenv import load_dotenv
from openai import OpenAI
from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
INTERFACE_ROOT = Path(__file__).resolve().parent
WORKSPACE_ROOT = INTERFACE_ROOT / "workspace"


st.set_page_config(
    page_title="Battery Agent Interface",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed",
)


CUSTOM_CSS = """
<style>
    :root {
        --bg: #f7f2e8;
        --panel: rgba(255,255,255,0.82);
        --panel-strong: #fffdf8;
        --ink: #1f1f1a;
        --muted: #6d665c;
        --line: rgba(86, 72, 46, 0.14);
        --accent: #b4882d;
        --accent-deep: #7a5b19;
        --ok: #1d6b45;
        --warn: #a95d0a;
        --risk: #9c2f2f;
    }

    .stApp {
        background:
            radial-gradient(circle at top left, rgba(231, 198, 120, 0.30), transparent 28%),
            radial-gradient(circle at top right, rgba(157, 122, 51, 0.16), transparent 24%),
            linear-gradient(180deg, #f8f4ec 0%, #f1eadc 100%);
        color: var(--ink);
    }

    .stApp,
    .stApp p,
    .stApp span,
    .stApp label,
    .stApp div,
    .stMarkdown,
    .stMarkdown p,
    .stMarkdown span,
    .stCaption,
    .stText,
    .st-emotion-cache-10trblm,
    .st-emotion-cache-16idsys,
    .st-emotion-cache-pkbazv,
    .st-emotion-cache-q8sbsg,
    .st-emotion-cache-1vbkxwb,
    .st-emotion-cache-ue6h4q,
    .st-emotion-cache-1kyxreq,
    .st-emotion-cache-1r6slb0,
    .stTabs [role="tab"],
    .stExpander summary,
    .stRadio label,
    .stCheckbox label,
    .stSelectbox label,
    .stTextInput label,
    .stTextArea label,
    .stFileUploader label,
    .stNumberInput label,
    .stSlider label,
    .stDownloadButton label {
        color: #1f1f1a !important;
    }

    .stCaption,
    .st-emotion-cache-pkbazv,
    .st-emotion-cache-q8sbsg {
        color: #4d463d !important;
    }

    .block-container {
        padding-top: 2rem;
        padding-bottom: 2.5rem;
        max-width: 1280px;
    }

    .hero {
        padding: 2rem 2.2rem;
        border-radius: 28px;
        background: linear-gradient(135deg, rgba(245, 236, 214, 0.96), rgba(231, 214, 170, 0.92));
        color: #1f1f1a;
        border: 1px solid rgba(86, 72, 46, 0.14);
        box-shadow: 0 22px 60px rgba(56, 39, 10, 0.18);
        margin-bottom: 1.2rem;
    }

    .hero h1 {
        margin: 0;
        font-size: 3rem;
        line-height: 1;
        letter-spacing: -0.03em;
    }

    .hero p {
        margin: 0.85rem 0 0;
        color: #3d372f;
        font-size: 1rem;
        max-width: 760px;
    }

    .panel {
        background: var(--panel);
        border: 1px solid var(--line);
        border-radius: 24px;
        padding: 1.1rem 1.15rem;
        box-shadow: 0 10px 30px rgba(45, 32, 9, 0.05);
        backdrop-filter: blur(10px);
    }

    .panel-title {
        font-size: 0.95rem;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: var(--muted);
        margin-bottom: 0.5rem;
    }

    .section-head {
        display: flex;
        justify-content: space-between;
        align-items: end;
        gap: 1rem;
        margin: 1rem 0 0.7rem;
    }

    .section-head h2 {
        margin: 0;
        font-size: 1.55rem;
        color: var(--ink);
    }

    .metric-card {
        background: var(--panel-strong);
        border: 1px solid var(--line);
        border-radius: 22px;
        padding: 1rem 1.1rem;
        min-height: 122px;
    }

    .metric-label {
        color: var(--muted);
        font-size: 0.88rem;
        margin-bottom: 0.55rem;
    }

    .metric-value {
        font-size: 2.2rem;
        line-height: 1;
        font-weight: 700;
        color: var(--accent-deep);
    }

    .grade-pill {
        display: inline-block;
        border-radius: 999px;
        padding: 0.3rem 0.75rem;
        font-size: 0.82rem;
        font-weight: 700;
        margin-top: 0.6rem;
    }

    .grade-excellent {
        background: rgba(29, 107, 69, 0.12);
        color: var(--ok);
    }

    .grade-acceptable {
        background: rgba(169, 93, 10, 0.12);
        color: var(--warn);
    }

    .grade-risky {
        background: rgba(156, 47, 47, 0.12);
        color: var(--risk);
    }

    .chip-wrap {
        display: flex;
        flex-wrap: wrap;
        gap: 0.45rem;
        margin-top: 0.35rem;
    }

    .chip {
        display: inline-flex;
        align-items: center;
        border-radius: 999px;
        padding: 0.36rem 0.76rem;
        background: rgba(180, 136, 45, 0.10);
        color: var(--accent-deep);
        border: 1px solid rgba(180, 136, 45, 0.14);
        font-size: 0.84rem;
        line-height: 1.2;
    }

    .dim-card {
        background: var(--panel-strong);
        border: 1px solid var(--line);
        border-radius: 20px;
        padding: 1rem;
        margin-bottom: 0.8rem;
    }

    .dim-title {
        margin: 0 0 0.25rem;
        font-size: 1.02rem;
        font-weight: 700;
    }

    .small-muted {
        color: var(--muted);
        font-size: 0.9rem;
    }

    .nav-note {
        color: var(--muted);
        font-size: 0.92rem;
        margin: 0.25rem 0 0.8rem;
    }

    .stButton > button {
        border-radius: 999px;
        border: 1px solid rgba(122, 91, 25, 0.16);
        background: linear-gradient(180deg, #fff8e8 0%, #f2e2b4 100%);
        color: #523e13;
        font-weight: 700;
        min-height: 2.75rem;
    }

    .stDownloadButton > button {
        border-radius: 999px;
    }
</style>
"""


def bootstrap_env() -> None:
    env_candidates = [
        ROOT / ".env",
        ROOT / "Labeling Agent" / ".env",
        ROOT / "Production_Agent" / ".env",
        ROOT / "Evaluation_Agent" / ".env",
    ]
    for env_path in env_candidates:
        if env_path.exists():
            load_dotenv(env_path, override=False)


@st.cache_resource
def load_modules() -> dict[str, Any]:
    bootstrap_env()

    def _load(name: str, path: Path) -> Any:
        spec = importlib.util.spec_from_file_location(name, path)
        if spec is None or spec.loader is None:
            raise RuntimeError(f"Unable to load module: {path}")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    label_module = _load("labeling_llm_service", ROOT / "Labeling Agent" / "llm_service.py")
    eval_module = _load("evaluation_qwen3_omni_api", ROOT / "Evaluation_Agent" / "qwen3_omni_api.py")
    text_module = _load("text_script_render_layers", ROOT / "Text_Script" / "scripts" / "render_text_layers.py")
    text_module.FONT_DIR = ROOT / "Text_Script" / "字体库"
    text_module.OUT_DIR = INTERFACE_ROOT / "workspace" / "text_generator"

    production_src = ROOT / "Production_Agent" / "src"
    if str(production_src) not in sys.path:
        sys.path.insert(0, str(production_src))

    from production_agent_2.models.qwen_image import QwenImageClient
    from production_agent_2.models.qwen_image_edit import QwenImageEditClient
    from production_agent_2.agents import nodes as production_nodes
    from production_agent_2.graph.workflow import SequentialWorkflow, build_workflow
    from production_agent_2.schemas import MaterialAsset, RunRequest, RunState
    from production_agent_2.tools.io import utc_timestamp
    from production_agent_2.tools.boards import create_reference_board
    import production_agent_2.paths as production_paths
    import production_agent_2.tools.assets as production_assets
    import production_agent_2.tools.io as production_io

    return {
        "label": label_module,
        "eval": eval_module,
        "text": text_module,
        "QwenImageClient": QwenImageClient,
        "QwenImageEditClient": QwenImageEditClient,
        "build_workflow": build_workflow,
        "SequentialWorkflow": SequentialWorkflow,
        "MaterialAsset": MaterialAsset,
        "RunRequest": RunRequest,
        "RunState": RunState,
        "utc_timestamp": utc_timestamp,
        "create_reference_board": create_reference_board,
        "production_nodes": production_nodes,
        "production_paths": production_paths,
        "production_assets": production_assets,
        "production_io": production_io,
    }


def ensure_workspace() -> None:
    WORKSPACE_ROOT.mkdir(parents=True, exist_ok=True)


def get_session_key() -> str:
    if "interface_session_id" not in st.session_state:
        st.session_state["interface_session_id"] = datetime.now().strftime("%Y%m%d%H%M%S")
    return st.session_state["interface_session_id"]


def section_button(label: str, target: str, description: str, key: str) -> None:
    with st.container():
        st.markdown(
            f"""
            <div class="panel">
                <div class="panel-title">{label}</div>
                <div class="small-muted">{description}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button(f"进入 {label}", key=key, use_container_width=True):
            st.session_state["active_section"] = target
            st.rerun()


def render_home_selector() -> None:
    active = st.session_state.get("active_section", "evaluation")
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)
    st.markdown(
        """
        <div class="hero">
            <h1>Battery Agent Interface</h1>
            <p>统一入口整合评估智能体、生产智能体与素材库智能体，先在本地 Streamlit 跑通交互，再继续上线部署。</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        section_button("评估智能体", "evaluation", "上传单张图片，选择主图商详或媒介投放素材 checklist，展示模型评分与输出。", "nav_eval")
    with col2:
        section_button("生产智能体", "production", "输入四类参考素材和文案信息，生成主图商详，并支持基于最新结果继续 edit。", "nav_prod")
    with col3:
        section_button("素材库智能体", "labeling", "上传图片后只做标签识别，不包含评分模块。", "nav_label")
    with col4:
        section_button("文字图片生成器", "text_generator", "输入 headline，选择模板和字体，生成透明文字图层 PNG、预览图和元数据。", "nav_text")

    st.caption(f"当前页面：{active}")


def make_run_dir(prefix: str) -> Path:
    ensure_workspace()
    session_id = get_session_key()
    run_id = f"{prefix}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    run_dir = WORKSPACE_ROOT / session_id / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir


def save_upload(uploaded_file: Any, target_dir: Path) -> Path:
    target_dir.mkdir(parents=True, exist_ok=True)
    target_path = target_dir / uploaded_file.name
    target_path.write_bytes(uploaded_file.getvalue())
    return target_path


def render_chip_list(items: list[str], empty_text: str = "暂无") -> None:
    if not items:
        st.caption(empty_text)
        return
    chips = "".join(f'<span class="chip">{item}</span>' for item in items)
    st.markdown(f'<div class="chip-wrap">{chips}</div>', unsafe_allow_html=True)


def render_image(image: Any, caption: str | None = None) -> None:
    try:
        st.image(image, caption=caption, use_container_width=True)
    except TypeError:
        try:
            st.image(image, caption=caption, use_column_width=True)
        except TypeError:
            st.image(image, caption=caption)


def grade_class(grade: str) -> str:
    mapping = {
        "Excellent": "grade-excellent",
        "Acceptable": "grade-acceptable",
        "Risky": "grade-risky",
    }
    return mapping.get(grade, "grade-acceptable")


def render_checklist_panel(checklist_cfg: dict[str, Any]) -> None:
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.markdown(f"### {checklist_cfg['title']}")
    for dim_name, dim_cfg in checklist_cfg["dimensions"].items():
        with st.expander(dim_name, expanded=False):
            st.markdown("`Issue tags`")
            render_chip_list(dim_cfg.get("issue_tags", []))
            st.markdown("`Severe`")
            render_chip_list(dim_cfg.get("severe", []))
            st.markdown("`Minor`")
            render_chip_list(dim_cfg.get("minor", []), empty_text="无")
    st.markdown("</div>", unsafe_allow_html=True)


def build_eval_result_ui(result: dict[str, Any]) -> None:
    top1, top2, top3 = st.columns(3)
    with top1:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-label">Overall Score</div>
                <div class="metric-value">{result.get('overall_score', 0):.2f}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with top2:
        grade = result.get("overall_grade", "")
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-label">Overall Grade</div>
                <div class="metric-value" style="font-size:1.55rem;">{grade}</div>
                <div class="grade-pill {grade_class(grade)}">{grade}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with top3:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-label">Checklist Type</div>
                <div class="metric-value" style="font-size:1.2rem;">{result.get('checklist_type', '')}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    left, right = st.columns([1.1, 1])
    with left:
        st.markdown("#### 模型输出")
        st.markdown(
            f"""
            <div class="panel">
                <div class="panel-title">素材摘要</div>
                <div>{result.get('material_summary', '') or '无'}</div>
                <div class="panel-title" style="margin-top:1rem;">总体判断</div>
                <div>{result.get('rationale', '') or '无'}</div>
                <div class="panel-title" style="margin-top:1rem;">不确定点</div>
                <div>{result.get('assumptions', '') or '无'}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with right:
        st.markdown("#### 原始 JSON")
        st.json(result)

    st.markdown("#### 分维度结果")
    cols = st.columns(2)
    for idx, (dim_name, dim_result) in enumerate(result.get("dimensions", {}).items()):
        with cols[idx % 2]:
            grade = dim_result.get("grade", "")
            st.markdown(
                f"""
                <div class="dim-card">
                    <p class="dim-title">{dim_name}</p>
                    <div class="small-muted">Score {dim_result.get('score', 0)} | Severe {dim_result.get('severe_count', 0)} | Minor {dim_result.get('minor_count', 0)}</div>
                    <div class="grade-pill {grade_class(grade)}">{grade}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            st.markdown("Issue tags")
            render_chip_list(dim_result.get("issue_tags", []))
            if dim_result.get("other_tags"):
                st.markdown("Other tags")
                render_chip_list(dim_result.get("other_tags", []))
            st.markdown("Evidence")
            for item in dim_result.get("evidence", []):
                st.markdown(f"- {item}")


def run_evaluation(eval_module: Any, uploaded_file: Any, checklist_type: str, content_text: str) -> dict[str, Any]:
    api_key = os.getenv("DASHSCOPE_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("DASHSCOPE_API_KEY 未配置。")

    run_dir = make_run_dir("evaluation")
    input_path = save_upload(uploaded_file, run_dir / "inputs")
    media_block = eval_module.file_to_media_block(str(input_path))
    prompt = eval_module.build_prompt(content_text, checklist_type=checklist_type)
    client = OpenAI(api_key=api_key, base_url=eval_module.BASE_URL)
    completion = client.chat.completions.create(
        model=eval_module.MODEL_NAME,
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    media_block,
                ],
            }
        ],
        stream=True,
        stream_options={"include_usage": True},
    )
    text_buf = ""
    for chunk in completion:
        if chunk.choices and getattr(chunk.choices[0].delta, "content", None):
            text_buf += chunk.choices[0].delta.content

    result = eval_module.normalize_result(
        eval_module.extract_first_json(text_buf),
        checklist_type=checklist_type,
    )
    output_path = run_dir / "result.json"
    output_path.write_text(
        __import__("json").dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    result["_artifact_path"] = str(output_path)
    return result


def init_dashscope_upload() -> Any:
    try:
        from dashscope import File
        if hasattr(File, "upload"):
            return lambda p: File.upload(p)
    except Exception:
        pass
    try:
        from dashscope import File
        if hasattr(File, "call_upload"):
            def _upload(path: str) -> Any:
                resp = File.call_upload(path)
                if hasattr(resp, "output") and isinstance(resp.output, dict) and resp.output.get("url"):
                    return resp.output["url"]
                if hasattr(resp, "url"):
                    return resp.url
                return None
            return _upload
    except Exception:
        pass
    try:
        from dashscope import FileUploader
        return lambda p: FileUploader().upload(p)
    except Exception:
        return None


def upload_to_cloud_if_needed(local_path: Path) -> str | None:
    upload_fn = init_dashscope_upload()
    if not upload_fn:
        return None
    result = upload_fn(str(local_path))
    if isinstance(result, str):
        return result
    if hasattr(result, "url") and result.url:
        return result.url
    if isinstance(result, dict):
        return result.get("url") or result.get("file_url")
    return None


def run_labeling(label_module: Any, uploaded_file: Any) -> dict[str, Any]:
    run_dir = make_run_dir("labeling")
    input_path = save_upload(uploaded_file, run_dir / "inputs")
    file_bytes = input_path.read_bytes()
    is_image = True

    result = None
    file_size_mb = len(file_bytes) / (1024 * 1024)
    if file_size_mb > 10:
        file_url = upload_to_cloud_if_needed(input_path)
        if not file_url:
            raise RuntimeError("当前大图上传需要 dashscope 文件上传支持；请安装 dashscope 或改用 10MB 以下图片。")
        result = label_module.analyze_media_for_tags_by_url(file_url=file_url, is_image=is_image)
    else:
        result = label_module.analyze_media_for_tags(
            file_bytes=file_bytes,
            filename=uploaded_file.name,
            is_image=is_image,
        )
    if not result:
        raise RuntimeError("模型没有返回可解析的标签结果。")
    return result


def image_info(path: Path) -> tuple[int, int, str]:
    with Image.open(path) as image:
        return image.width, image.height, image.mode


def save_many_uploads(files: list[Any], target_dir: Path) -> list[Path]:
    saved: list[Path] = []
    for item in files:
        saved.append(save_upload(item, target_dir))
    return saved


@contextmanager
def patched_production_paths(
    modules: dict[str, Any],
    materials_root: Path,
    runs_root: Path,
):
    production_paths = modules["production_paths"]
    production_assets = modules["production_assets"]
    production_io = modules["production_io"]

    original = {
        "paths_materials_root": production_paths.MATERIALS_ROOT,
        "paths_category_dirs": production_paths.CATEGORY_DIRS,
        "paths_runs_root": production_paths.RUNS_ROOT,
        "assets_materials_root": production_assets.MATERIALS_ROOT,
        "assets_category_dirs": production_assets.CATEGORY_DIRS,
        "io_runs_root": production_io.RUNS_ROOT,
    }
    category_dirs = {
        "background": materials_root / "Background",
        "layout": materials_root / "Layout",
        "object": materials_root / "Object",
        "text": materials_root / "Text",
    }
    try:
        production_paths.MATERIALS_ROOT = materials_root
        production_paths.CATEGORY_DIRS = category_dirs
        production_paths.RUNS_ROOT = runs_root
        production_assets.MATERIALS_ROOT = materials_root
        production_assets.CATEGORY_DIRS = category_dirs
        production_io.RUNS_ROOT = runs_root
        yield
    finally:
        production_paths.MATERIALS_ROOT = original["paths_materials_root"]
        production_paths.CATEGORY_DIRS = original["paths_category_dirs"]
        production_paths.RUNS_ROOT = original["paths_runs_root"]
        production_assets.MATERIALS_ROOT = original["assets_materials_root"]
        production_assets.CATEGORY_DIRS = original["assets_category_dirs"]
        production_io.RUNS_ROOT = original["io_runs_root"]


def run_generation(
    modules: dict[str, Any],
    grouped_paths: dict[str, list[Path]],
    primary_copy: str,
    secondary_copy: str,
    selling_points: list[str],
    background_note: str,
    object_note: str,
    layout_note: str,
    text_note: str,
    variants: int,
    seed: int,
    size: str,
) -> dict[str, Any]:
    if not any(grouped_paths.values()):
        raise RuntimeError("至少需要上传一类参考图。")

    workspace_dir = make_run_dir("production_workflow")
    materials_root = workspace_dir / "materials"
    runs_root = workspace_dir / "runs"
    for folder in ("Background", "Layout", "Object", "Text"):
        (materials_root / folder).mkdir(parents=True, exist_ok=True)
    runs_root.mkdir(parents=True, exist_ok=True)

    category_map = {
        "background": "Background",
        "layout": "Layout",
        "object": "Object",
        "text": "Text",
    }
    for category, paths in grouped_paths.items():
        target_dir = materials_root / category_map[category]
        for path in paths:
            target_path = target_dir / path.name
            target_path.write_bytes(path.read_bytes())

    if any(
        item.strip()
        for item in [background_note, object_note, layout_note, text_note]
    ):
        notes_path = workspace_dir / "upload_notes.txt"
        notes_path.write_text(
            "\n".join(
                [
                    f"Background: {background_note.strip()}",
                    f"Object: {object_note.strip()}",
                    f"Layout: {layout_note.strip()}",
                    f"Text: {text_note.strip()}",
                ]
            ),
            encoding="utf-8",
        )

    sequential_workflow_cls = modules["SequentialWorkflow"]
    production_nodes = modules["production_nodes"]
    run_request_cls = modules["RunRequest"]
    run_state_cls = modules["RunState"]
    run_id = modules["utc_timestamp"]()

    request = run_request_cls(
        workflow_type="主图商详",
        primary_copy=primary_copy,
        secondary_copy=secondary_copy,
        selling_points=selling_points or ["聚能环科技"],
        variants=variants,
        seed=seed,
        output_size=size,
    )
    state = run_state_cls(run_id=run_id, request=request)

    with patched_production_paths(modules, materials_root=materials_root, runs_root=runs_root):
        workflow = sequential_workflow_cls(
            [
                production_nodes.mark_running,
                production_nodes.collect_assets,
                production_nodes.build_reference_boards,
                production_nodes.build_creative_brief,
                production_nodes.plan_prompt,
                production_nodes.generate_background,
                production_nodes.generate_main_visual,
                production_nodes.export_component_layers,
                production_nodes.mark_completed,
            ]
        )
        final_state = workflow.invoke(state)
        if isinstance(final_state, dict):
            final_state = run_state_cls.model_validate(final_state)

    if not final_state.generated_images and not final_state.selected_image:
        errors = "\n".join(final_state.errors) if final_state.errors else "模型没有返回图片。"
        raise RuntimeError(errors)

    boards = [
        {"name": board.board_id, "path": board.path, "note": board.note}
        for board in final_state.reference_boards
    ]
    outputs = [
        {"index": str(item.index), "path": item.path, "source_url": item.source_url}
        for item in final_state.generated_images
    ]
    prompt = final_state.prompt_plan.prompt if final_state.prompt_plan else ""
    latest_image = final_state.selected_image or (outputs[0]["path"] if outputs else "")
    return {
        "run_dir": str(runs_root / run_id),
        "workspace_dir": str(workspace_dir),
        "boards": boards,
        "outputs": outputs,
        "prompt": prompt,
        "latest_image": latest_image,
        "edit_history": [],
        "warnings": list(final_state.warnings),
        "errors": list(final_state.errors),
        "artifacts": dict(final_state.artifacts),
    }


def run_edit(modules: dict[str, Any], latest_image: str, instruction: str) -> dict[str, str]:
    edit_client = modules["QwenImageEditClient"]()
    if not edit_client.is_enabled():
        raise RuntimeError("DASHSCOPE_API_KEY 未配置，无法调用编辑模型。")
    image_path = Path(latest_image)
    edit_dir = image_path.parent.parent / "edits"
    edit_dir.mkdir(parents=True, exist_ok=True)
    output_path = edit_dir / f"edit_{datetime.now().strftime('%H%M%S')}.png"
    return edit_client.retouch(str(image_path), instruction, str(output_path))


def save_uploaded_edit_source(uploaded_file: Any, production_result: dict[str, Any]) -> str:
    base_dir = Path(production_result["workspace_dir"]) / "edit_uploads"
    base_dir.mkdir(parents=True, exist_ok=True)
    target_path = base_dir / uploaded_file.name
    target_path.write_bytes(uploaded_file.getvalue())
    return str(target_path)


def get_decomposition_specs() -> list[dict[str, str]]:
    return [
        {
            "key": "background_clean",
            "filename": "background_clean.png",
            "label": "干净背景",
            "mode": "retouch",
            "instruction": """
任务：从这张海报中移除所有前景元素，只保留并补全原图背景。

必须删除的内容：
- 所有人物与身体部位，包括脸、头发、手、衣服、皮肤、影子、倒影
- 所有产品、包装、电池、彩盒、道具、按钮、标签、logo、文字、数字
- 所有附着在人物或产品上的局部特效、边缘辉光、贴边闪电、贴边能量环

必须保留的内容：
- 原图背景本身已有的颜色关系、明暗层次、雾气、烟雾、云层、空间感、远景光感
- 原图背景已有的整体构图、光源方向、透视关系、氛围感

严格禁止：
- 禁止保留任何人物、产品、文字、logo 或其轮廓残影
- 禁止重新生成一个全新的背景
- 禁止把背景改成摄影棚、舞台、纯渐变、纯空白、几何灯光背景
- 禁止改变原图背景的主色调、光影方向和整体气质

执行方式：
- 先彻底删除前景
- 再只对被前景遮挡的位置做自然补全
- 补全区域必须和原背景连续、统一、无拼接感

最终输出标准：
- 结果里只能剩下背景
- 画面中绝对不能出现任何字、人、产品、物体或可识别的前景痕迹
- 结果必须看起来像“原图背景被完整恢复”，而不是新做了一张背景
""".strip(),
        },
        {
            "key": "effects_overlay",
            "filename": "effects_overlay_black.png",
            "label": "特效层",
            "mode": "retouch",
            "instruction": """
任务：从这张海报中单独抽离“围绕主体存在的特效层”。

只允许保留这些内容：
- 电光、闪电、能量环、辉光、发光边缘、光束、雾化发光、能量拖尾
- 必须是原图里本来就存在、并且围绕主体分布的特效

必须删除的内容：
- 所有人物、身体、手、脸、头发、衣服
- 所有产品、电池、彩盒、道具
- 所有文字、logo、按钮、标签、数字
- 所有主体本身及其实体轮廓

严格禁止：
- 禁止保留人物或产品的可识别轮廓
- 禁止重新生成新的主体、新的手、新的人脸、新的产品
- 禁止额外设计原图中不存在的大块新特效
- 禁止输出带场景的背景

输出要求：
- 最终结果只能剩下特效
- 背景必须是纯黑色
- 特效的位置、方向、密度应尽量贴近原图，不要改构图
- 最终图必须适合在 Photoshop 中直接以 Screen / 滤色模式叠加使用
""".strip(),
        },
    ]


def save_uploaded_decomposition_source(uploaded_file: Any, production_result: dict[str, Any]) -> str:
    base_dir = Path(production_result["workspace_dir"]) / "decomposition_uploads"
    base_dir.mkdir(parents=True, exist_ok=True)
    target_path = base_dir / uploaded_file.name
    target_path.write_bytes(uploaded_file.getvalue())
    return str(target_path)


def run_decomposition(
    modules: dict[str, Any],
    production_result: dict[str, Any],
    source_image_path: str,
) -> dict[str, Any]:
    edit_client = modules["QwenImageEditClient"]()
    if not edit_client.is_enabled():
        raise RuntimeError("DASHSCOPE_API_KEY 未配置，无法调用拆解模型。")

    source_path = Path(source_image_path)
    if not source_path.exists():
        raise RuntimeError("拆解输入图不存在。")

    export_dir = Path(production_result["workspace_dir"]) / "decomposition"
    export_dir.mkdir(parents=True, exist_ok=True)

    layers: dict[str, dict[str, str]] = {}
    for spec in get_decomposition_specs():
        output_path = export_dir / spec["filename"]
        result = edit_client.retouch(
            image_path=str(source_path),
            instruction=spec["instruction"],
            output_path=str(output_path),
        )
        layers[spec["key"]] = {"label": spec["label"], "path": result.get("path", str(output_path))}

    manifest = {
        "source_image": str(source_path),
        "generated_at": datetime.now().isoformat(),
        "layers": layers,
    }
    manifest_path = export_dir / "decomposition_manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return {
        "source_image": str(source_path),
        "layers": layers,
        "manifest_path": str(manifest_path),
    }


def build_layered_package(production_result: dict[str, Any]) -> tuple[bytes, str]:
    decomposition = production_result.get("decomposition") or {}
    manifest = {
        "run_dir": production_result.get("run_dir", ""),
        "workspace_dir": production_result.get("workspace_dir", ""),
        "prompt": production_result.get("prompt", ""),
        "warnings": production_result.get("warnings", []),
        "errors": production_result.get("errors", []),
        "latest_image": production_result.get("latest_image", ""),
        "package_type": "post_edit_decomposition",
        "files": [],
    }

    candidates = [
        ("final_composite", production_result.get("latest_image")),
        ("prompt_plan_json", production_result.get("artifacts", {}).get("prompt_plan")),
        ("decomposition_manifest_json", decomposition.get("manifest_path")),
    ]

    memory = io.BytesIO()
    with zipfile.ZipFile(memory, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for logical_name, file_path in candidates:
            if not file_path:
                continue
            path = Path(file_path)
            if not path.exists() or not path.is_file():
                continue
            arcname = f"assets/{logical_name}{path.suffix.lower()}" if path.suffix else f"assets/{logical_name}"
            zf.write(path, arcname)
            manifest["files"].append(
                {
                    "name": logical_name,
                    "source_path": str(path),
                    "archive_path": arcname,
                }
            )

        for key, item in (decomposition.get("layers") or {}).items():
            path = Path(item["path"])
            if path.exists():
                arcname = f"layers/{path.name}"
                zf.write(path, arcname)
                manifest["files"].append(
                    {
                        "name": key,
                        "source_path": str(path),
                        "archive_path": arcname,
                    }
                )

        if production_result.get("boards"):
            for index, board in enumerate(production_result["boards"], start=1):
                board_path = Path(board["path"])
                if board_path.exists():
                    arcname = f"boards/{index:02d}_{board_path.name}"
                    zf.write(board_path, arcname)
                    manifest["files"].append(
                        {
                            "name": board["name"],
                            "source_path": str(board_path),
                            "archive_path": arcname,
                        }
                    )

        zf.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))

    filename = f"layered_package_{Path(production_result['run_dir']).name}.zip"
    return memory.getvalue(), filename


def render_evaluation_page(modules: dict[str, Any]) -> None:
    eval_module = modules["eval"]
    st.markdown('<div class="section-head"><h2>评估智能体</h2></div>', unsafe_allow_html=True)
    st.markdown('<p class="nav-note">上传单张图片，选择评估维度，展示 checklist、模型结论和得分。</p>', unsafe_allow_html=True)

    left, right = st.columns([0.95, 1.05])
    with left:
        uploaded = st.file_uploader(
            "上传待评估图片",
            type=["png", "jpg", "jpeg", "webp", "bmp"],
            key="eval_upload",
        )
        option = st.radio(
            "评估模式",
            options=["主图商详", "媒介投放素材"],
            horizontal=True,
        )
        checklist_type = "main_detail" if option == "主图商详" else "media_ad"
        content_text = st.text_area(
            "补充说明",
            placeholder="可选。补充素材背景、投放语境或需要模型重点留意的点。",
            key="eval_content_text",
        )
        if uploaded:
            render_image(uploaded.getvalue())
        if st.button("开始评估", type="primary", use_container_width=True, key="eval_submit"):
            if not uploaded:
                st.error("请先上传一张图片。")
            else:
                with st.spinner("模型评估中..."):
                    try:
                        result = run_evaluation(eval_module, uploaded, checklist_type, content_text)
                        st.session_state["evaluation_result"] = result
                    except Exception as exc:
                        st.session_state["evaluation_error"] = str(exc)
                        st.session_state.pop("evaluation_result", None)
    with right:
        render_checklist_panel(eval_module.CHECKLISTS["main_detail" if option == "主图商详" else "media_ad"])

    if st.session_state.get("evaluation_error"):
        st.error(st.session_state["evaluation_error"])

    if st.session_state.get("evaluation_result"):
        build_eval_result_ui(st.session_state["evaluation_result"])
        artifact_path = st.session_state["evaluation_result"].get("_artifact_path")
        if artifact_path and Path(artifact_path).exists():
            st.download_button(
                "下载评估 JSON",
                Path(artifact_path).read_text(encoding="utf-8"),
                file_name=Path(artifact_path).name,
                mime="application/json",
                use_container_width=False,
            )


def render_production_page(modules: dict[str, Any]) -> None:
    st.markdown('<div class="section-head"><h2>生产智能体</h2></div>', unsafe_allow_html=True)
    st.markdown('<p class="nav-note">当前先支持主图商详。上传四类参考素材，并输入文案，再生成图片；生成后可继续基于最新结果 edit。</p>', unsafe_allow_html=True)

    left, right = st.columns([1.02, 0.98])
    with left:
        bg_files = st.file_uploader("Background 参考图", type=["png", "jpg", "jpeg", "webp", "bmp"], accept_multiple_files=True, key="prod_bg")
        obj_files = st.file_uploader("Object 参考图", type=["png", "jpg", "jpeg", "webp", "bmp"], accept_multiple_files=True, key="prod_obj")
        layout_files = st.file_uploader("Layout 参考图", type=["png", "jpg", "jpeg", "webp", "bmp"], accept_multiple_files=True, key="prod_layout")
        text_files = st.file_uploader("Text 参考图", type=["png", "jpg", "jpeg", "webp", "bmp"], accept_multiple_files=True, key="prod_text")

        primary_copy = st.text_input("主标题", value="南孚电池")
        secondary_copy = st.text_input("副标题", value="持久电力 稳定输出")
        selling_points_raw = st.text_input("卖点关键词", value="聚能环科技,高效续航")
        background_note = st.text_area("Background 文字补充", placeholder="例如：空间更开阔、金色逆光、科技感。")
        object_note = st.text_area("Object 文字补充", placeholder="例如：产品更靠前、包装更清晰、突出电池金属质感。")
        layout_note = st.text_area("Layout 文字补充", placeholder="例如：主体偏右，左上保留标题区。")
        text_note = st.text_area("Text 文字补充", placeholder="例如：主标题更大，卖点用短标签。")

        col_a, col_b, col_c = st.columns(3)
        with col_a:
            variants = st.slider("生成张数", 1, 4, 2)
        with col_b:
            seed = st.number_input("Seed", min_value=0, value=42, step=1)
        with col_c:
            size = st.selectbox("尺寸", options=["1328*1328", "1024*1024"], index=0)

        if st.button("生成主图商详", type="primary", use_container_width=True, key="prod_generate"):
            if not any([bg_files, obj_files, layout_files, text_files]):
                st.error("至少上传一类参考图。")
            else:
                with st.spinner("生产模型生成中..."):
                    try:
                        run_dir = make_run_dir("production_inputs")
                        grouped_paths = {
                            "background": save_many_uploads(bg_files or [], run_dir / "inputs" / "Background"),
                            "object": save_many_uploads(obj_files or [], run_dir / "inputs" / "Object"),
                            "layout": save_many_uploads(layout_files or [], run_dir / "inputs" / "Layout"),
                            "text": save_many_uploads(text_files or [], run_dir / "inputs" / "Text"),
                        }
                        result = run_generation(
                            modules=modules,
                            grouped_paths=grouped_paths,
                            primary_copy=primary_copy,
                            secondary_copy=secondary_copy,
                            selling_points=[item.strip() for item in selling_points_raw.split(",") if item.strip()],
                            background_note=background_note,
                            object_note=object_note,
                            layout_note=layout_note,
                            text_note=text_note,
                            variants=int(variants),
                            seed=int(seed),
                            size=size,
                        )
                        st.session_state["production_result"] = result
                        st.session_state.pop("production_error", None)
                    except Exception as exc:
                        st.session_state["production_error"] = str(exc)
                        st.session_state.pop("production_result", None)

    with right:
        st.markdown("#### 输入规范")
        st.markdown(
            """
            <div class="panel">
                <div class="panel-title">四类输入</div>
                <div>Background 控制场景与氛围，Object 控制产品主体，Layout 控制版式结构，Text 控制文案层级。</div>
                <div class="panel-title" style="margin-top:1rem;">当前限制</div>
                <div>只支持主图商详，并且这里已经切回原 Production_Agent 的生成 workflow；当前默认只做主图生成。后期拆解目前只输出背景和特效两层，并在你手动触发后单独生成，避免拖慢主图生成速度。</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    if st.session_state.get("production_error"):
        st.error(st.session_state["production_error"])

    result = st.session_state.get("production_result")
    if result:
        st.markdown("#### 参考板")
        board_cols = st.columns(max(len(result["boards"]), 1))
        for idx, board in enumerate(result["boards"]):
            with board_cols[idx]:
                render_image(board["path"], caption=board["name"])

        st.markdown("#### 生成结果")
        image_cols = st.columns(min(len(result["outputs"]), 3))
        for idx, output in enumerate(result["outputs"]):
            with image_cols[idx % len(image_cols)]:
                render_image(output["path"], caption=f"候选 {idx + 1}")
                st.download_button(
                    f"下载候选 {idx + 1}",
                    Path(output["path"]).read_bytes(),
                    file_name=Path(output["path"]).name,
                    mime="image/png",
                    key=f"download_output_{idx}",
                    use_container_width=True,
                )

        st.markdown("#### 生成 Prompt")
        st.code(result["prompt"], language="text")

        st.markdown("#### 后期拆解")
        decompose_source_mode = st.radio(
            "拆解输入源",
            options=["拆解最新生成图", "上传一张图片后拆解"],
            horizontal=True,
            key="prod_decompose_source_mode",
        )
        decomposition_target_path = result["latest_image"]
        uploaded_decompose_image = None
        if decompose_source_mode == "上传一张图片后拆解":
            uploaded_decompose_image = st.file_uploader(
                "上传需要拆解的图片",
                type=["png", "jpg", "jpeg", "webp", "bmp"],
                key="prod_decompose_upload",
            )
            if uploaded_decompose_image:
                render_image(uploaded_decompose_image.getvalue(), caption="待拆解上传图")
                decomposition_target_path = save_uploaded_decomposition_source(uploaded_decompose_image, result)
            else:
                st.caption("上传一张图片后，拆解将基于该图片执行。")
        else:
            st.caption("当前默认基于最新生成结果拆解背景和特效两层。")

        if st.button("拆解最终图", use_container_width=False, key="prod_decompose_submit"):
            if decompose_source_mode == "上传一张图片后拆解" and not uploaded_decompose_image:
                st.error("请先上传一张需要拆解的图片。")
            else:
                with st.spinner("正在基于目标图拆解后期图层..."):
                    try:
                        decomposition = run_decomposition(modules, result, decomposition_target_path)
                        result["decomposition"] = decomposition
                        st.session_state["production_result"] = result
                        st.session_state.pop("production_error", None)
                    except Exception as exc:
                        st.session_state["production_error"] = str(exc)

        decomposition = result.get("decomposition")
        if decomposition:
            layer_cols = st.columns(2)
            for idx, (key, item) in enumerate(decomposition.get("layers", {}).items()):
                with layer_cols[idx % 2]:
                    st.markdown(f"**{item['label']}**")
                    render_image(item["path"])
            package_bytes, package_name = build_layered_package(result)
            st.download_button(
                "下载后期拆解包",
                package_bytes,
                file_name=package_name,
                mime="application/zip",
                key="download_layered_package",
                use_container_width=False,
            )

        st.markdown("#### Edit 模式")
        edit_source_mode = st.radio(
            "编辑输入源",
            options=["继续 edit 最新结果", "上传一张图片后 edit"],
            horizontal=True,
            key="prod_edit_source_mode",
        )
        uploaded_edit_image = None
        edit_target_path = result["latest_image"]
        if edit_source_mode == "上传一张图片后 edit":
            uploaded_edit_image = st.file_uploader(
                "上传需要 edit 的图片",
                type=["png", "jpg", "jpeg", "webp", "bmp"],
                key="prod_edit_upload",
            )
            if uploaded_edit_image:
                render_image(uploaded_edit_image.getvalue(), caption="待编辑上传图")
                edit_target_path = save_uploaded_edit_source(uploaded_edit_image, result)
            else:
                st.caption("上传一张图片后，edit 将基于该图片执行。")
        else:
            st.caption("当前默认基于最新生成结果继续 edit。")

        edit_prompt = st.text_area(
            "编辑指令",
            placeholder="例如：让背景更高级一些，保留产品和文字不变；强化左上角卖点区层级。",
            key="prod_edit_prompt",
        )
        if st.button("对最新图片执行 Edit", use_container_width=True, key="prod_edit_submit"):
            if not edit_prompt.strip():
                st.error("请输入 edit 指令。")
            elif edit_source_mode == "上传一张图片后 edit" and not uploaded_edit_image:
                st.error("请先上传一张需要 edit 的图片。")
            else:
                with st.spinner("编辑模型处理中..."):
                    try:
                        edit_result = run_edit(modules, edit_target_path, edit_prompt.strip())
                        result["latest_image"] = edit_result["path"]
                        result.pop("decomposition", None)
                        result.setdefault("edit_history", []).append(
                            {
                                "prompt": edit_prompt.strip(),
                                "path": edit_result["path"],
                                "source_mode": edit_source_mode,
                                "source_path": edit_target_path,
                            }
                        )
                        st.session_state["production_result"] = result
                        st.session_state.pop("production_error", None)
                    except Exception as exc:
                        st.session_state["production_error"] = str(exc)

        st.markdown("#### 当前最新结果")
        render_image(result["latest_image"])
        if result.get("edit_history"):
            st.markdown("#### Edit 历史")
            for idx, item in enumerate(result["edit_history"], start=1):
                st.markdown(f"{idx}. {item['prompt']}")
                st.caption(f"来源：{item.get('source_mode', '继续 edit 最新结果')}")
                render_image(item["path"])


def render_labeling_page(modules: dict[str, Any]) -> None:
    label_module = modules["label"]
    st.markdown('<div class="section-head"><h2>素材库智能体</h2></div>', unsafe_allow_html=True)
    st.markdown('<p class="nav-note">这一页只做标签识别，评分模块已移除。</p>', unsafe_allow_html=True)

    left, right = st.columns([0.92, 1.08])
    with left:
        uploaded = st.file_uploader(
            "上传素材图片",
            type=["png", "jpg", "jpeg", "webp", "bmp"],
            key="label_upload",
        )
        if uploaded:
            render_image(uploaded.getvalue())
        if st.button("开始打标签", type="primary", use_container_width=True, key="label_submit"):
            if not uploaded:
                st.error("请先上传一张图片。")
            else:
                with st.spinner("标签识别中..."):
                    try:
                        result = run_labeling(label_module, uploaded)
                        st.session_state["labeling_result"] = result
                        st.session_state.pop("labeling_error", None)
                    except Exception as exc:
                        st.session_state["labeling_error"] = str(exc)
                        st.session_state.pop("labeling_result", None)
    with right:
        st.markdown(
            """
            <div class="panel">
                <div class="panel-title">输出维度</div>
                <div>场景、人群、卖点、内容体裁、情绪与痛点。只展示标签结果，不展示评分。</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    if st.session_state.get("labeling_error"):
        st.error(st.session_state["labeling_error"])

    result = st.session_state.get("labeling_result")
    if result:
        st.markdown("#### 标签结果")
        for category in ["场景", "人群", "卖点", "内容体裁", "情绪与痛点"]:
            st.markdown(f"**{category}**")
            render_chip_list(result.get(category, []), empty_text="暂无标签")
        st.markdown("#### 原始 JSON")
        st.json(result)


def save_uploaded_font(uploaded_file: Any) -> Path:
    font_dir = INTERFACE_ROOT / "workspace" / "uploaded_fonts"
    font_dir.mkdir(parents=True, exist_ok=True)
    font_path = font_dir / uploaded_file.name
    font_path.write_bytes(uploaded_file.getvalue())
    return font_path


def run_text_generator(
    text_module: Any,
    headline: str,
    template: str,
    font_path: Path,
    font_size: int,
    fill_hex: str,
    stroke_fill_hex: str,
    stroke_width: int,
    shadow: bool,
    shadow_color_hex: str,
    shadow_offset_x: int,
    shadow_offset_y: int,
    line_spacing: int,
    align: str,
    space_as_newline: bool,
    max_width: int,
) -> dict[str, str]:
    if not headline.strip():
        raise RuntimeError("headline 不能为空。")

    run_dir = make_run_dir("text_generator")
    out_dir = run_dir / "outputs"
    out_dir.mkdir(parents=True, exist_ok=True)

    fill = text_module.ImageColor.getrgb(fill_hex)
    stroke_fill = text_module.ImageColor.getrgb(stroke_fill_hex)
    shadow_color = text_module.ImageColor.getrgb(shadow_color_hex)

    block, meta = text_module.render_block(
        text=headline.strip(),
        font_path=font_path,
        font_size=font_size,
        max_width=max_width,
        fill=fill,
        stroke_fill=stroke_fill,
        stroke_width=stroke_width,
        shadow=shadow,
        shadow_color=shadow_color,
        shadow_offset=(shadow_offset_x, shadow_offset_y),
        line_spacing=line_spacing,
        align=align,
        space_as_newline=space_as_newline,
    )
    if block is None:
        raise RuntimeError("文字图层生成失败。")

    headline_path = out_dir / "headline.png"
    block.save(headline_path, "PNG")

    preview = text_module.Image.new("RGBA", text_module.POSTER_SIZE, (30, 30, 30, 255))
    x = (preview.width - block.width) // 2
    y = (preview.height - block.height) // 2
    preview.alpha_composite(block, (x, y))
    preview_path = out_dir / "preview.png"
    preview.save(preview_path, "PNG")

    metadata = {
        "template": template,
        "input": {"headline": headline.strip()},
        "style": {
            "font_file": font_path.name,
            "font_path": str(font_path),
            "font_size": font_size,
            "fill": fill_hex,
            "stroke_fill": stroke_fill_hex,
            "stroke_width": stroke_width,
            "shadow": shadow,
            "shadow_color": shadow_color_hex,
            "shadow_offset": [shadow_offset_x, shadow_offset_y],
            "line_spacing": line_spacing,
            "align": align,
            "space_as_newline": space_as_newline,
            "max_width": max_width,
        },
        "assets": {"headline": meta},
        "files": {
            "headline": "headline.png",
            "preview": "preview.png",
        },
    }
    meta_path = out_dir / "text_meta.json"
    meta_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")

    return {
        "run_dir": str(run_dir),
        "headline_path": str(headline_path),
        "preview_path": str(preview_path),
        "meta_path": str(meta_path),
    }


def render_text_generator_page(modules: dict[str, Any]) -> None:
    text_module = modules["text"]
    st.markdown('<div class="section-head"><h2>文字图片生成器</h2></div>', unsafe_allow_html=True)
    st.markdown('<p class="nav-note">输入主标题文案，选择字体模板或上传自定义 TTF/OTF，生成透明文字图层和预览图。</p>', unsafe_allow_html=True)

    left, right = st.columns([0.95, 1.05])
    with left:
        headline = st.text_area("Headline 文案", value="南孚聚能环5代", height=120)
        template = st.selectbox("模板", options=sorted(text_module.TEMPLATES.keys()), index=0)
        tpl = dict(text_module.TEMPLATES[template])

        font_mode = st.radio(
            "字体来源",
            options=["使用内置字体", "上传字体文件"],
            horizontal=True,
            key="text_font_mode",
        )
        font_dir = Path(text_module.FONT_DIR)
        available_fonts = sorted([p.name for p in font_dir.iterdir() if p.is_file() and p.suffix.lower() in {".ttf", ".otf"}])
        selected_font_name = tpl["font_file"]
        uploaded_font = None
        font_path = font_dir / selected_font_name
        if font_mode == "使用内置字体":
            selected_font_name = st.selectbox("内置字体", options=available_fonts, index=available_fonts.index(tpl["font_file"]) if tpl["font_file"] in available_fonts else 0)
            font_path = font_dir / selected_font_name
        else:
            uploaded_font = st.file_uploader("上传 TTF / OTF 字体", type=["ttf", "otf"], key="text_font_upload")
            if uploaded_font:
                font_path = save_uploaded_font(uploaded_font)
            st.caption("未上传时会继续使用模板默认字体。")

        col1, col2, col3 = st.columns(3)
        with col1:
            font_size = st.number_input("字号", min_value=12, value=int(tpl["font_size"]), step=1)
        with col2:
            stroke_width = st.number_input("描边宽度", min_value=0, value=int(tpl["stroke_width"]), step=1)
        with col3:
            line_spacing = st.number_input("行间距", min_value=0, value=int(tpl["line_spacing"]), step=1)

        col4, col5, col6 = st.columns(3)
        with col4:
            fill_hex = st.text_input("文字颜色", value=str(tpl["fill"]))
        with col5:
            stroke_fill_hex = st.text_input("描边颜色", value=str(tpl["stroke_fill"]))
        with col6:
            shadow_color_hex = st.text_input("阴影颜色", value=str(tpl["shadow_color"]))

        col7, col8, col9 = st.columns(3)
        with col7:
            shadow = st.checkbox("启用阴影", value=bool(tpl["shadow"]))
        with col8:
            shadow_offset_x = st.number_input("阴影 X", value=int(tpl["shadow_offset"][0]), step=1)
        with col9:
            shadow_offset_y = st.number_input("阴影 Y", value=int(tpl["shadow_offset"][1]), step=1)

        col10, col11, col12 = st.columns(3)
        with col10:
            align = st.selectbox("对齐", options=["left", "center", "right"], index=["left", "center", "right"].index(str(tpl["align"])))
        with col11:
            max_width = st.number_input("最大宽度", min_value=100, value=680, step=10)
        with col12:
            space_as_newline = st.checkbox("空格转换行", value=False)

        if st.button("生成文字图片", type="primary", use_container_width=True, key="text_generate_submit"):
            try:
                result = run_text_generator(
                    text_module=text_module,
                    headline=headline,
                    template=template,
                    font_path=font_path,
                    font_size=int(font_size),
                    fill_hex=fill_hex,
                    stroke_fill_hex=stroke_fill_hex,
                    stroke_width=int(stroke_width),
                    shadow=bool(shadow),
                    shadow_color_hex=shadow_color_hex,
                    shadow_offset_x=int(shadow_offset_x),
                    shadow_offset_y=int(shadow_offset_y),
                    line_spacing=int(line_spacing),
                    align=align,
                    space_as_newline=bool(space_as_newline),
                    max_width=int(max_width),
                )
                st.session_state["text_generator_result"] = result
                st.session_state.pop("text_generator_error", None)
            except Exception as exc:
                st.session_state["text_generator_error"] = str(exc)
                st.session_state.pop("text_generator_result", None)

    with right:
        st.markdown(
            """
            <div class="panel">
                <div class="panel-title">输出内容</div>
                <div>会生成透明文字图层 <code>headline.png</code>、居中预览图 <code>preview.png</code> 以及样式元数据 <code>text_meta.json</code>。</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    if st.session_state.get("text_generator_error"):
        st.error(st.session_state["text_generator_error"])

    result = st.session_state.get("text_generator_result")
    if result:
        st.markdown("#### 生成结果")
        preview_col, headline_col = st.columns(2)
        with preview_col:
            st.markdown("**预览图**")
            render_image(result["preview_path"])
            st.download_button(
                "下载 preview.png",
                Path(result["preview_path"]).read_bytes(),
                file_name="preview.png",
                mime="image/png",
                key="download_text_preview",
                use_container_width=True,
            )
        with headline_col:
            st.markdown("**透明文字图层**")
            render_image(result["headline_path"])
            st.download_button(
                "下载 headline.png",
                Path(result["headline_path"]).read_bytes(),
                file_name="headline.png",
                mime="image/png",
                key="download_text_headline",
                use_container_width=True,
            )

        st.download_button(
            "下载 text_meta.json",
            Path(result["meta_path"]).read_text(encoding="utf-8"),
            file_name="text_meta.json",
            mime="application/json",
            key="download_text_meta",
            use_container_width=False,
        )


def main() -> None:
    modules = load_modules()
    render_home_selector()

    active = st.session_state.get("active_section", "evaluation")
    st.markdown("---")
    if active == "evaluation":
        render_evaluation_page(modules)
    elif active == "production":
        render_production_page(modules)
    elif active == "text_generator":
        render_text_generator_page(modules)
    else:
        render_labeling_page(modules)

    st.markdown("---")
    st.caption("本地验证阶段继续使用 Streamlit 是合理的：开发快、联调成本低、适合先把流程和状态管理跑通，后续再决定是否迁移前端框架或直接部署。")


if __name__ == "__main__":
    main()
