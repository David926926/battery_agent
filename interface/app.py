from __future__ import annotations

import base64
import importlib.util
import json
import mimetypes
import os
import sys
import warnings
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any

import streamlit as st
from dotenv import load_dotenv
from openai import OpenAI
from PIL import Image

warnings.filterwarnings("ignore")


ROOT = Path(__file__).resolve().parents[1]
INTERFACE_ROOT = Path(__file__).resolve().parent
WORKSPACE_ROOT = INTERFACE_ROOT / "workspace"


st.set_page_config(
    page_title="南孚智能体",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed",
)


CUSTOM_CSS = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@500;600;700;800&display=swap');

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

    .stTextInput input,
    .stTextArea textarea,
    .stNumberInput input,
    .stSelectbox [data-baseweb="select"] > div,
    .stMultiSelect [data-baseweb="select"] > div,
    .stFileUploader section,
    .stRadio [role="radiogroup"],
    .stSlider,
    .stExpander,
    .stCodeBlock,
    pre,
    code {
        background: rgba(255, 252, 245, 0.96) !important;
        color: #1f1f1a !important;
        border-color: rgba(86, 72, 46, 0.18) !important;
    }

    .stTextInput input,
    .stNumberInput input,
    .stTextArea textarea {
        caret-color: #1f1f1a !important;
    }

    .stTextInput input::placeholder,
    .stTextArea textarea::placeholder {
        color: #6d665c !important;
        opacity: 1 !important;
    }

    .stSelectbox [data-baseweb="select"] *,
    .stMultiSelect [data-baseweb="select"] *,
    .stFileUploader section *,
    .stFileUploader [data-testid="stFileUploaderDropzoneInstructions"] small,
    .stExpander summary *,
    .stCodeBlock *,
    pre *,
    code * {
        color: #1f1f1a !important;
    }

    .stFileUploader [data-testid="stFileUploaderDropzoneInstructions"] small {
        display: none !important;
    }

    .stDownloadButton button,
    .stButton button {
        background: linear-gradient(180deg, #fffaf0, #f2e6ca) !important;
        color: #2d2418 !important;
        border: 1px solid rgba(122, 91, 25, 0.28) !important;
    }

    .stDownloadButton button:hover,
    .stButton button:hover {
        background: linear-gradient(180deg, #f8f0db, #ecdcb5) !important;
        color: #2d2418 !important;
    }

    .stAlert {
        background: rgba(255, 252, 245, 0.97) !important;
        color: #1f1f1a !important;
        border: 1px solid rgba(86, 72, 46, 0.18) !important;
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
        font-size: 3.4rem;
        line-height: 1;
        letter-spacing: -0.04em;
        font-family: 'Inter', 'Helvetica Neue', Arial, sans-serif;
        font-weight: 800;
    }

    .hero p {
        margin: 0.85rem 0 0;
        color: #3d372f;
        font-size: 1rem;
        max-width: 760px;
    }

    .section-card {
        border-radius: 28px;
        overflow: hidden;
        margin-bottom: 1rem;
        box-shadow: 0 18px 40px rgba(56, 39, 10, 0.09);
        border: 1px solid rgba(139, 118, 78, 0.18);
    }

    .section-card-title-box,
    .section-card-desc-box {
        padding: 1rem 1rem 0.9rem;
        background: rgba(255, 255, 255, 0.98);
    }

    .section-card-title-box {
        background: linear-gradient(180deg, rgba(255, 255, 255, 0.96), rgba(244, 236, 209, 0.95));
    }

    .section-card-title {
        font-size: 1.2rem;
        font-weight: 800;
        color: #2d2418;
        margin: 0;
    }

    .section-card-desc-box {
        border-top: 1px solid rgba(86, 72, 46, 0.08);
    }

    .section-card-desc {
        color: #534a3e;
        font-size: 0.96rem;
        font-weight: 400;
        line-height: 1.7;
        margin: 0;
    }

    .section-card-action {
        padding: 0.9rem 1rem 1.1rem;
        background: rgba(255, 255, 255, 0.97);
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
        font-size: 1.4rem;
        font-weight: bold;
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
        font-size: 1rem;
        font-weight: 500;
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
    production_src = ROOT / "Production_Agent" / "src"
    if str(production_src) not in sys.path:
        sys.path.insert(0, str(production_src))

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

    from production_agent_2.models import (
        get_default_model,
        get_family_models,
        run_with_model_fallback,
    )
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
        "get_family_models": get_family_models,
        "get_default_model": get_default_model,
        "run_with_model_fallback": run_with_model_fallback,
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
            <div class="section-card">
                <div class="section-card-title-box">
                    <div class="section-card-title">{label}</div>
                </div>
                <div class="section-card-desc-box">
                    <div class="section-card-desc">{description}</div>
                </div>
                <div class="section-card-action"></div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button(f"进入 {label}", key=key):
            st.session_state["active_section"] = target
            st.rerun()


def render_home_selector() -> None:
    active = st.session_state.get("active_section", "evaluation")
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)
    st.markdown(
        """
        <div class="hero">
            <h1>南孚智能体</h1>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col1, col2, col3 = st.columns(3)
    with col1:
        section_button("评估智能体", "evaluation", "上传图片，评估主图或素材质量，查看评分和建议。", "nav_eval")
    with col2:
        section_button(
            "生产智能体",
            "production",
            "生成背景图，支持提取或文字生成，可继续编辑。",
            "nav_prod",
        )
    with col3:
        section_button("素材库智能体", "labeling", "上传图片，进行标签识别和分类。", "nav_label")

    st.caption(f"当前页面：{active}")


def make_run_dir(prefix: str) -> Path:
    ensure_workspace()
    session_id = get_session_key()
    run_id = f"{prefix}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    run_dir = WORKSPACE_ROOT / session_id / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


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


def checklist_item_name(item: Any) -> str:
    if isinstance(item, dict):
        return str(item.get("name", "")).strip()
    return str(item).strip()


def render_checklist_items(items: list[Any], empty_text: str = "暂无") -> None:
    valid_items = [item for item in items if checklist_item_name(item)]
    if not valid_items:
        st.caption(empty_text)
        return
    for item in valid_items:
        name = checklist_item_name(item)
        st.markdown(f"- {name}")
        if isinstance(item, dict) and item.get("description"):
            st.caption(str(item["description"]).strip())


def render_image(image: Any, caption: str | None = None) -> None:
    try:
        st.image(image, caption=caption, use_container_width=True)
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
            render_checklist_items(dim_cfg.get("issue_tags", []))
            st.markdown("`Severe`")
            render_checklist_items(dim_cfg.get("severe", []))
            st.markdown("`Minor`")
            render_checklist_items(dim_cfg.get("minor", []), empty_text="无")
    st.markdown("</div>", unsafe_allow_html=True)


def build_eval_overall_ui(result: dict[str, Any]) -> None:
    grade = result.get("overall_grade", "")
    st.markdown("#### 整体评级")
    st.markdown(
        f"""
        <div class="dim-card">
            <p class="dim-title">整体评级</p>
            <div class="grade-pill {grade_class(grade)}">{grade}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def build_eval_dimensions_ui(result: dict[str, Any]) -> None:
    st.markdown("#### 分维度结果")
    cols = st.columns(2)
    for idx, (dim_name, dim_result) in enumerate(result.get("dimensions", {}).items()):
        with cols[idx % 2]:
            grade = dim_result.get("grade", "")
            st.markdown(
                f"""
                <div class="dim-card">
                    <p class="dim-title">{dim_name}</p>
                    <div class="small-muted">Severe {dim_result.get('severe_count', 0)} | Minor {dim_result.get('minor_count', 0)}</div>
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


def _compact_eval_for_summary(result: dict[str, Any]) -> dict[str, Any]:
    dims: dict[str, dict[str, Any]] = {}
    for name, dim in (result.get("dimensions") or {}).items():
        dims[name] = {
            "grade": dim.get("grade"),
            "score": dim.get("score"),
            "severe_count": dim.get("severe_count"),
            "minor_count": dim.get("minor_count"),
            "issue_tags": dim.get("issue_tags") or [],
            "other_tags": dim.get("other_tags") or [],
            "evidence": dim.get("evidence") or [],
        }

    return {
        "checklist_type": result.get("checklist_type"),
        "overall_score": result.get("overall_score"),
        "overall_grade": result.get("overall_grade"),
        "material_summary": result.get("material_summary") or "",
        "assumptions": result.get("assumptions") or "",
        "rationale": result.get("rationale") or "",
        "dimensions": dims,
    }


def generate_eval_summary(
    modules: dict[str, Any],
    eval_module: Any,
    result: dict[str, Any],
    preferred_model: str | None = None,
) -> str:
    api_key = os.getenv("DASHSCOPE_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("DASHSCOPE_API_KEY 未配置，无法生成总结。")

    compact = _compact_eval_for_summary(result)

    base_url = getattr(eval_module, "BASE_URL", None) or "https://dashscope.aliyuncs.com/compatible-mode/v1"
    client = OpenAI(api_key=api_key, base_url=base_url)
    image_path = str(result.get("_input_path") or "").strip()

    system_prompt = (
        "你是一名电商创意审核专家，请基于 checklist 的结构化评估结果，总结这张素材的主要风险与优劣。"
        "你会同时收到评估 JSON 和素材图片。"
        "所有关于“是否存在问题/风险”“是否适合直接投放”的判断，必须严格依据 JSON 中各个评分维度里的等级、分数和列出的具体问题/证据，"
        "不能把 JSON 中未出现的具体问题当成已发生的事实。"
        "图片只用于帮助你把总结写得更具体、更贴近实际画面，让描述更生动，但不能推翻或覆盖 JSON 里的结论。"
        "输出时不要出现具体的维度、“issue_tags”、“other_tags”等技术性术语，也不要直接照搬字段名，而是用自然、口语化但专业的中文来描述。"
        "整体语气要像给同事写评审意见：简洁、真诚、专业。"
    )

    user_text = (
        "下面是对一张电商品牌素材的结构化评估结果(JSON)：\n"
        f"{json.dumps(compact, ensure_ascii=False, indent=2)}\n\n"
        "我还会附上对应素材图片，请你结合画面做表达优化，但必须严格遵守以下要求：\n"
        "1）先用一两句话说明“基于当前 checklist 是否发现明显问题”，以及整体风险感受和是否适合直接投放；\n"
        "2）如果评分里确实有问题或扣分，只挑 1~3 个最关键的点，用日常说话方式概括出来，并结合 JSON 中已经给出的证据举例，不要发明新的具体问题；\n"
        "3）允许引用图片里肉眼可见的主体、配色、版式氛围、产品呈现方式，让总结更具体、更像真正在看这张图，但这些视觉描述不能替代 JSON 证据去新增缺陷结论；\n"
        "4）如果所有评分都很高且没有列出任何问题，可以说明“基于当前 checklist 暂未看到明显硬伤”，"
        "但允许在最后补充 1 句话作为额外建议，并明确这只是建议而不是已经发现的缺陷。这个额外建议仍然必须聚焦图片本身可见的内容，例如构图、主体呈现、色彩、信息组织或画面氛围，不要延伸到图片之外的营销策略、投放计划、用户人群、渠道玩法等画面外话题；\n"
        "5）除最后这 1 句“额外建议”外，不要自由引入 JSON 中未出现的具体问题点。\n"
        "不要输出 JSON 或 Markdown，只输出一段连续的自然语言。"
    )

    user_message: dict[str, Any] = {
        "role": "user",
        "content": [{"type": "text", "text": user_text}],
    }
    if image_path:
        user_message["content"].append(eval_module.file_to_media_block(image_path))

    completion, resolved_model, attempts = modules["run_with_model_fallback"](
        family="vision_chat",
        preferred_model=preferred_model or getattr(eval_module, "MODEL_NAME", "qwen3-omni-flash"),
        call=lambda model_name: client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": system_prompt},
                user_message,
            ],
        ),
    )

    text = completion.choices[0].message.content or ""
    result["_summary_resolved_model"] = resolved_model
    result["_summary_attempted_models"] = attempts
    return text.strip()


def run_evaluation(
    modules: dict[str, Any],
    eval_module: Any,
    uploaded_file: Any,
    checklist_type: str,
    content_text: str,
    preferred_model: str | None = None,
) -> dict[str, Any]:
    api_key = os.getenv("DASHSCOPE_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("DASHSCOPE_API_KEY 未配置。")

    run_dir = make_run_dir("evaluation")
    input_path = save_upload(uploaded_file, run_dir / "inputs")
    media_block = eval_module.file_to_media_block(str(input_path))
    prompt = eval_module.build_prompt(content_text, checklist_type=checklist_type)
    client = OpenAI(api_key=api_key, base_url=eval_module.BASE_URL)
    completion, resolved_model, attempts = modules["run_with_model_fallback"](
        family="vision_chat",
        preferred_model=preferred_model or eval_module.MODEL_NAME,
        call=lambda model_name: client.chat.completions.create(
            model=model_name,
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
        ),
    )
    text_buf = ""
    for chunk in completion:
        if chunk.choices and getattr(chunk.choices[0].delta, "content", None):
            text_buf += chunk.choices[0].delta.content

    result = eval_module.normalize_result(
        eval_module.extract_first_json(text_buf),
        checklist_type=checklist_type,
    )
    result["_resolved_model"] = resolved_model
    result["_attempted_models"] = attempts
    output_path = run_dir / "result.json"
    output_path.write_text(
        __import__("json").dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    result["_artifact_path"] = str(output_path)
    result["_input_path"] = str(input_path)
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


def run_labeling(modules: dict[str, Any], label_module: Any, uploaded_file: Any, preferred_model: str | None = None) -> dict[str, Any]:
    run_dir = make_run_dir("labeling")
    input_path = save_upload(uploaded_file, run_dir / "inputs")
    file_bytes = input_path.read_bytes()
    is_image = True

    result = None
    file_size_mb = len(file_bytes) / (1024 * 1024)
    if file_size_mb > 10:
        file_url = upload_to_cloud_if_needed(input_path)
        if not file_url:
            raise RuntimeError("当前大图上传需要 dashscope 文件上传支持；请安装 dashscope，或改用更小的图片。")
        result = label_module.analyze_media_for_tags_by_url(
            file_url=file_url,
            is_image=is_image,
            preferred_model=preferred_model or modules["get_default_model"]("vision_chat"),
        )
    else:
        result = label_module.analyze_media_for_tags(
            file_bytes=file_bytes,
            filename=uploaded_file.name,
            is_image=is_image,
            preferred_model=preferred_model or modules["get_default_model"]("vision_chat"),
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
    generation_mode: str,
    background_prompt: str,
    size: str,
    *,
    use_case: str = "main_detail",
    audience: str = "电商消费者",
    scene: str = "",
    style: str = "",
    must_have: list[str] | None = None,
    must_avoid: list[str] | None = None,
    selling_points: list[str] | None = None,
    reserve_component_space: bool = True,
    realism_level: str = "realistic",
    brand_tone_priority: list[str] | None = None,
    visual_density: str = "medium",
    direction_count: int = 3,
    variants_per_direction: int = 2,
    aspect_ratio: str = "1:1",
    preferred_text_model: str = "qwen-plus",
    preferred_image_generation_model: str = "qwen-image-2.0-pro",
    preferred_image_edit_model: str = "qwen-image-edit-max",
    progress_callback: Any | None = None,
) -> dict[str, Any]:
    if generation_mode == "image_to_background" and not any(grouped_paths.values()):
        raise RuntimeError("至少需要上传一类参考图。")
    if generation_mode == "text_to_background" and not (background_prompt.strip() or scene.strip()):
        raise RuntimeError("请输入场景或补充描述。")

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

    sequential_workflow_cls = modules["SequentialWorkflow"]
    production_nodes = modules["production_nodes"]
    run_request_cls = modules["RunRequest"]
    run_state_cls = modules["RunState"]
    run_id = modules["utc_timestamp"]()

    request = run_request_cls(
        workflow_type="主图商详" if use_case == "main_detail" else "媒介投放素材",
        generation_mode=generation_mode,
        use_case=use_case,
        audience=audience.strip() or "电商消费者",
        scene=scene.strip(),
        style=style.strip(),
        must_have=must_have or [],
        must_avoid=must_avoid or [],
        selling_points=selling_points or [],
        reserve_component_space=reserve_component_space,
        realism_level=realism_level,
        brand_tone_priority=brand_tone_priority or ["reliable", "warm", "professional"],
        visual_density=visual_density,
        preferred_text_model=preferred_text_model,
        preferred_image_generation_model=preferred_image_generation_model,
        preferred_image_edit_model=preferred_image_edit_model,
        direction_count=int(direction_count),
        variants_per_direction=int(variants_per_direction),
        variants=int(variants_per_direction),
        aspect_ratio=aspect_ratio,
        background_prompt=background_prompt.strip(),
        output_size=size,
    )
    state = run_state_cls(run_id=run_id, request=request, progress_callback=progress_callback)

    with patched_production_paths(modules, materials_root=materials_root, runs_root=runs_root):
        workflow = sequential_workflow_cls(
            [
                production_nodes.mark_running,
                production_nodes.collect_assets,
                production_nodes.build_task_brief,
                production_nodes.build_reference_boards,
                production_nodes.generate_creative_directions,
                production_nodes.build_prompt_plans,
                production_nodes.generate_backgrounds,
                production_nodes.select_primary_output,
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
        {
            "index": str(item.index),
            "path": item.path,
            "source_url": item.source_url,
            "direction_id": item.direction_id,
            "direction_title": item.direction_title,
            "variant_index": item.variant_index,
            "seed": item.seed,
            "resolved_model": item.resolved_model,
            "attempted_models": item.attempted_models,
            "prompt_plan_path": item.prompt_plan_path,
        }
        for item in final_state.generated_images
    ]
    prompt_plans = [item.model_dump() for item in final_state.prompt_plans]
    direction_meta = {item.direction_id: item.model_dump() for item in final_state.creative_directions}
    prompt_plan_by_direction = {item.direction_id: item.model_dump() for item in final_state.prompt_plans}
    direction_groups: list[dict[str, Any]] = []
    for direction in final_state.creative_directions:
        group_outputs = [item for item in outputs if item["direction_id"] == direction.direction_id]
        direction_groups.append(
            {
                "direction": direction.model_dump(),
                "outputs": group_outputs,
                "prompt_plan": prompt_plan_by_direction.get(direction.direction_id),
            }
        )
    prompt = final_state.prompt_plans[0].prompt if final_state.prompt_plans else ""
    latest_image = final_state.selected_image or (outputs[0]["path"] if outputs else "")
    return {
        "run_dir": str(runs_root / run_id),
        "workspace_dir": str(workspace_dir),
        "boards": boards,
        "outputs": outputs,
        "direction_groups": direction_groups,
        "creative_directions": [item.model_dump() for item in final_state.creative_directions],
        "prompt_plans": prompt_plans,
        "task_brief": final_state.task_brief.model_dump() if final_state.task_brief else None,
        "preferred_models": {
            "text_chat": request.preferred_text_model,
            "image_generation": request.preferred_image_generation_model,
            "image_edit": request.preferred_image_edit_model,
        },
        "prompt": prompt,
        "latest_image": latest_image,
        "selected_image": final_state.selected_image,
        "edit_history": [],
        "edit_rounds": [],
        "current_candidates": outputs,
        "current_candidate_groups": direction_groups,
        "latest_batch_id": str(runs_root / run_id),
        "warnings": list(final_state.warnings),
        "errors": list(final_state.errors),
        "artifacts": dict(final_state.artifacts),
        "direction_meta": direction_meta,
    }


def run_edit(
    modules: dict[str, Any],
    base_image: str,
    instruction: str,
    reference_images: list[str] | None = None,
    preferred_model: str | None = None,
) -> dict[str, str]:
    edit_client = modules["QwenImageEditClient"]()
    if not edit_client.is_enabled():
        raise RuntimeError("DASHSCOPE_API_KEY 未配置，无法调用编辑模型。")
    image_path = Path(base_image)
    edit_dir = image_path.parent.parent / "edits"
    edit_dir.mkdir(parents=True, exist_ok=True)
    output_path = edit_dir / f"edit_{datetime.now().strftime('%H%M%S')}.png"
    return edit_client.retouch(
        str(image_path),
        instruction,
        str(output_path),
        reference_images=reference_images or [],
        preferred_model=preferred_model,
    )


def save_uploaded_edit_source(uploaded_file: Any, production_result: dict[str, Any]) -> str:
    base_dir = Path(production_result["workspace_dir"]) / "edit_uploads"
    base_dir.mkdir(parents=True, exist_ok=True)
    target_path = base_dir / uploaded_file.name
    target_path.write_bytes(uploaded_file.getvalue())
    return str(target_path)


def save_uploaded_edit_sources(uploaded_files: list[Any], production_result: dict[str, Any]) -> list[str]:
    saved_paths: list[str] = []
    for uploaded_file in uploaded_files:
        saved_paths.append(save_uploaded_edit_source(uploaded_file, production_result))
    return saved_paths


def parse_multiline_list(value: str) -> list[str]:
    items: list[str] = []
    normalized_value = (
        (value or "")
        .replace("；", "\n")
        .replace("，", "\n")
        .replace(";", "\n")
        .replace(",", "\n")
    )
    for raw in normalized_value.splitlines():
        normalized = raw.strip().strip("-").strip()
        if normalized:
            items.append(normalized)
    return items


def model_options(modules: dict[str, Any], family: str) -> list[str]:
    return [str(item["id"]) for item in modules["get_family_models"](family)]


def model_label_map(modules: dict[str, Any], family: str) -> dict[str, str]:
    return {str(item["id"]): str(item["label"]) for item in modules["get_family_models"](family)}


def render_model_selectbox(
    modules: dict[str, Any],
    *,
    family: str,
    label: str,
    key: str,
    default_model: str | None = None,
) -> str:
    options = model_options(modules, family)
    labels = model_label_map(modules, family)
    selected = default_model or modules["get_default_model"](family)
    if selected not in options:
        options = [selected] + options
    selected_index = options.index(selected)
    chosen = st.selectbox(
        label,
        options=options,
        index=selected_index,
        format_func=lambda model_id: f"{labels.get(model_id, model_id)} ({model_id})",
        key=key,
    )
    st.caption("若首选模型限流或繁忙，系统会自动按性能顺序降级。")
    return chosen


def render_partial_production_preview(partial_groups: dict[str, dict[str, Any]]) -> None:
    if not partial_groups:
        return
    st.markdown("#### 已生成结果")
    for group in partial_groups.values():
        st.markdown(f"##### {group['title']}")
        outputs = group.get("outputs", [])
        if not outputs:
            st.caption("该方向尚未产出图片。")
            continue
        cols = st.columns(min(len(outputs), 3))
        for idx, output in enumerate(outputs):
            with cols[idx % len(cols)]:
                caption = f"{group['title']} · 第 {output['variant_index']} 张"
                render_image(output["path"], caption=caption)
                if output.get("resolved_model"):
                    st.caption(f"实际模型：{output['resolved_model']}")


def set_edit_loop_selected_base(path: str) -> None:
    st.session_state["edit_loop_selected_base_path"] = path


def uploader_key(base: str) -> str:
    version = int(st.session_state.get(f"{base}_version", 0))
    return f"{base}_{version}"


def reset_uploader(base: str, state_keys_to_clear: list[str] | None = None) -> None:
    st.session_state[f"{base}_version"] = int(st.session_state.get(f"{base}_version", 0)) + 1
    for key in state_keys_to_clear or []:
        st.session_state.pop(key, None)


def request_edit_loop_base_source(value: str) -> None:
    st.session_state["_pending_edit_loop_base_source"] = value


def ensure_production_result_shape(result: dict[str, Any] | None) -> dict[str, Any]:
    if not result:
        return {
            "workspace_dir": "",
            "outputs": [],
            "direction_groups": [],
            "edit_history": [],
            "edit_rounds": [],
            "current_candidates": [],
            "current_candidate_groups": [],
            "latest_batch_id": None,
            "latest_image": "",
            "preferred_models": {},
        }
    result.setdefault("outputs", [])
    result.setdefault("direction_groups", [])
    result.setdefault("edit_history", [])
    result.setdefault("edit_rounds", [])
    result.setdefault("current_candidates", list(result.get("outputs", [])))
    result.setdefault("current_candidate_groups", list(result.get("direction_groups", [])))
    result.setdefault("latest_batch_id", result.get("run_dir") or result.get("workspace_dir"))
    result.setdefault("latest_image", result.get("selected_image") or (result["outputs"][0]["path"] if result.get("outputs") else ""))
    result.setdefault("preferred_models", {})
    return result


def ensure_edit_workspace(result: dict[str, Any]) -> Path:
    workspace_dir = str(result.get("workspace_dir") or "").strip()
    if not workspace_dir:
        base_dir = make_run_dir("edit_loop_seed")
        result["workspace_dir"] = str(base_dir)
        workspace_dir = str(base_dir)
    edit_root = Path(workspace_dir) / "edit_loop"
    edit_root.mkdir(parents=True, exist_ok=True)
    return edit_root


def save_uploaded_base_image(uploaded_file: Any, result: dict[str, Any]) -> str:
    edit_root = ensure_edit_workspace(result)
    base_dir = edit_root / "uploaded_base"
    base_dir.mkdir(parents=True, exist_ok=True)
    path = base_dir / uploaded_file.name
    path.write_bytes(uploaded_file.getvalue())
    return str(path)


def save_uploaded_components(uploaded_files: list[Any], result: dict[str, Any]) -> list[str]:
    edit_root = ensure_edit_workspace(result)
    component_dir = edit_root / "uploaded_components"
    component_dir.mkdir(parents=True, exist_ok=True)
    saved_paths: list[str] = []
    for uploaded_file in uploaded_files[:2]:
        path = component_dir / uploaded_file.name
        path.write_bytes(uploaded_file.getvalue())
        saved_paths.append(str(path))
    return saved_paths


def prepare_image_for_model(path: str, output_dir: Path, max_side: int = 1600, jpeg_quality: int = 85) -> str:
    source = Path(path)
    output_dir.mkdir(parents=True, exist_ok=True)
    target = output_dir / f"{source.stem}_for_model.jpg"
    with Image.open(source) as image:
        working = image.convert("RGB")
        width, height = working.size
        longest = max(width, height)
        if longest > max_side:
            scale = max_side / longest
            resized = working.resize((max(1, int(width * scale)), max(1, int(height * scale))), Image.LANCZOS)
        else:
            resized = working
        resized.save(target, format="JPEG", quality=jpeg_quality, optimize=True)
    return str(target)


def _image_to_data_url(path: str) -> str:
    mime = mimetypes.guess_type(path)[0] or "image/jpeg"
    return f"data:{mime};base64,{base64.b64encode(Path(path).read_bytes()).decode('utf-8')}"


def build_edit_prompt_sections(
    *,
    direction: dict[str, Any],
    components: list[dict[str, str]],
    change_request: str,
    lock_request: str,
) -> dict[str, str]:
    component_lines = []
    for item in components:
        component_lines.append(
            f"- 组件：{item['label']}；期望位置：{item['position'] or '由模型判断最合理的位置'}"
        )
    component_block = "\n".join(component_lines) if component_lines else "本轮不新增组件，只针对背景图做编辑。"
    return {
        "编辑目标": str(direction.get("summary") or ""),
        "对 Base 图的理解": str(direction.get("base_understanding") or ""),
        "组件加入与位置要求": component_block,
        "需要变化的部分": change_request.strip() or "无额外变化要求，按创意方向自然优化。",
        "需要保持不变的部分": lock_request.strip() or "除本轮明确要求变化的部分外，尽量保持原图已有可用氛围与结构。",
        "禁止项与质量约束": str(direction.get("constraints") or ""),
    }


def plan_edit_directions(
    modules: dict[str, Any],
    *,
    base_image_path: str,
    component_refs: list[dict[str, str]],
    change_request: str,
    lock_request: str,
    direction_count: int,
    preferred_model: str,
    working_dir: Path,
) -> tuple[dict[str, Any], list[dict[str, Any]], str, list[dict[str, Any]]]:
    api_key = os.getenv("DASHSCOPE_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("DASHSCOPE_API_KEY 未配置，无法进行 Edit 规划。")
    client = OpenAI(api_key=api_key, base_url="https://dashscope.aliyuncs.com/compatible-mode/v1")

    brief = {
        "base_image_path": base_image_path,
        "component_refs": component_refs,
        "change_request": change_request.strip(),
        "lock_request": lock_request.strip(),
        "direction_count": max(1, int(direction_count)),
    }
    def _build_content(image_paths: list[str]) -> list[dict[str, Any]]:
        content: list[dict[str, Any]] = [
            {
                "type": "text",
                "text": (
                    "你是一名电商视觉后期策划。你会同时看到 base 图与最多 2 个组件图，请先理解画面，再输出 edit 创意方向的 JSON。"
                    "输出格式必须是一个 JSON 对象："
                    '{"brief_summary":"","creative_directions":[{"direction_id":"edit_direction_01","title":"","summary":"","base_understanding":"","composition_strategy":"","component_layout_strategy":"","what_changes":"","what_stays":"","constraints":"","risk_points":[""],"recommendation_reason":""}]}.'
                    "creative_directions 数量必须等于 direction_count。不要输出 markdown。"
                    f"\n输入 brief：{json.dumps(brief, ensure_ascii=False)}"
                ),
            }
        ]
        for image_path in image_paths:
            content.append({"type": "image_url", "image_url": {"url": _image_to_data_url(image_path)}})
        return content

    original_paths = [base_image_path] + [item["path"] for item in component_refs[:2]]

    def _call_with_paths(image_paths: list[str]) -> tuple[Any, str, list[dict[str, Any]]]:
        content = _build_content(image_paths)
        return modules["run_with_model_fallback"](
            family="vision_chat",
            preferred_model=preferred_model,
            call=lambda model_name: client.chat.completions.create(
                model=model_name,
                messages=[{"role": "user", "content": content}],
                response_format={"type": "json_object"},
            ),
        )

    try:
        completion, resolved_model, attempts = _call_with_paths(original_paths)
    except Exception as exc:
        message = str(exc)
        size_error_markers = [
            "Exceeded limit on max bytes per data-uri item",
            "Multimodal file size is too large",
            "file size is too large",
        ]
        if not any(marker in message for marker in size_error_markers):
            raise
        compressed_dir = working_dir / "compressed_for_planner"
        compressed_paths = [prepare_image_for_model(path, compressed_dir) for path in original_paths]
        completion, resolved_model, attempts = _call_with_paths(compressed_paths)
        attempts.append(
            {
                "model": "local_preprocess",
                "status": "fallback_compression_applied",
                "error": message,
            }
        )
    raw_text = completion.choices[0].message.content or "{}"
    payload = json.loads(raw_text)
    directions = payload.get("creative_directions")
    if not isinstance(directions, list) or not directions:
        raise RuntimeError("Edit 规划模型没有返回有效的 creative_directions。")
    normalized: list[dict[str, Any]] = []
    for idx, item in enumerate(directions[: max(1, int(direction_count))], start=1):
        if not isinstance(item, dict):
            continue
        normalized.append(
            {
                "direction_id": str(item.get("direction_id") or f"edit_direction_{idx:02d}"),
                "title": str(item.get("title") or f"Edit 方向 {idx}"),
                "summary": str(item.get("summary") or ""),
                "base_understanding": str(item.get("base_understanding") or ""),
                "composition_strategy": str(item.get("composition_strategy") or ""),
                "component_layout_strategy": str(item.get("component_layout_strategy") or ""),
                "what_changes": str(item.get("what_changes") or ""),
                "what_stays": str(item.get("what_stays") or ""),
                "constraints": str(item.get("constraints") or ""),
                "risk_points": item.get("risk_points") if isinstance(item.get("risk_points"), list) else [],
                "recommendation_reason": str(item.get("recommendation_reason") or ""),
            }
        )
    if not normalized:
        raise RuntimeError("Edit 规划模型返回的方向内容为空。")
    return brief, normalized, resolved_model, attempts


def run_edit_loop(
    modules: dict[str, Any],
    result: dict[str, Any],
    *,
    base_image_path: str,
    component_refs: list[dict[str, str]],
    change_request: str,
    lock_request: str,
    direction_count: int,
    variants_per_direction: int,
    preferred_planner_model: str,
    preferred_image_edit_model: str,
    progress_callback: Any | None = None,
) -> dict[str, Any]:
    edit_root = ensure_edit_workspace(result)
    round_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    round_dir = edit_root / f"round_{round_id}"
    round_dir.mkdir(parents=True, exist_ok=True)

    def emit(payload: dict[str, Any]) -> None:
        if callable(progress_callback):
            progress_callback(payload)

    emit({"stage": "edit_loop_running", "message": "正在理解图片并规划 Edit 方向。"})
    brief, directions, planner_model, planner_attempts = plan_edit_directions(
        modules,
        base_image_path=base_image_path,
        component_refs=component_refs,
        change_request=change_request,
        lock_request=lock_request,
        direction_count=direction_count,
        preferred_model=preferred_planner_model,
        working_dir=round_dir,
    )
    write_json(round_dir / "edit_brief.json", brief)
    write_json(round_dir / "edit_creative_directions.json", directions)
    write_json(
        round_dir / "edit_planner_trace.json",
        {"resolved_model": planner_model, "attempted_models": planner_attempts},
    )
    emit({"stage": "edit_directions_ready", "direction_count": len(directions), "creative_directions": directions})

    edit_client = modules["QwenImageEditClient"]()
    if not edit_client.is_enabled():
        raise RuntimeError("DASHSCOPE_API_KEY 未配置，无法调用编辑模型。")

    prompt_plans: list[dict[str, Any]] = []
    outputs: list[dict[str, Any]] = []
    direction_groups: list[dict[str, Any]] = []
    flat_component_paths = [item["path"] for item in component_refs]
    running_index = 0
    emit({"stage": "edit_prompt_ready", "message": "Edit prompts 已准备完成，开始出图。"})
    for direction in directions:
        sections = build_edit_prompt_sections(
            direction=direction,
            components=component_refs,
            change_request=change_request,
            lock_request=lock_request,
        )
        prompt = "\n\n".join(f"{title}\n{content}" for title, content in sections.items()).strip()
        prompt_plan = {
            "direction_id": direction["direction_id"],
            "direction_title": direction["title"],
            "prompt": prompt,
            "sections": sections,
            "preferred_model": preferred_image_edit_model,
        }
        prompt_plans.append(prompt_plan)
        direction_outputs: list[dict[str, Any]] = []
        for variant_index in range(1, max(1, int(variants_per_direction)) + 1):
            running_index += 1
            seed_label = datetime.now().strftime("%H%M%S")
            output_path = round_dir / "outputs" / f"{direction['direction_id']}_variant_{variant_index:02d}_{seed_label}.png"
            output_path.parent.mkdir(parents=True, exist_ok=True)
            edit_result = edit_client.retouch(
                image_path=base_image_path,
                instruction=prompt,
                output_path=str(output_path),
                reference_images=flat_component_paths,
                preferred_model=preferred_image_edit_model,
            )
            output = {
                "index": str(running_index),
                "path": edit_result["path"],
                "source_url": edit_result.get("source_url"),
                "direction_id": direction["direction_id"],
                "direction_title": direction["title"],
                "variant_index": variant_index,
                "resolved_model": edit_result.get("model"),
                "attempted_models": edit_result.get("attempted_models", []),
                "prompt": prompt,
            }
            outputs.append(output)
            direction_outputs.append(output)
            emit(
                {
                    "stage": "edit_image_generated",
                    "direction_id": direction["direction_id"],
                    "direction_title": direction["title"],
                    "variant_index": variant_index,
                    "path": edit_result["path"],
                    "resolved_model": edit_result.get("model"),
                }
            )
        direction_groups.append(
            {
                "direction": direction,
                "outputs": direction_outputs,
                "prompt_plan": prompt_plan,
            }
        )

    write_json(round_dir / "edit_prompt_plans.json", prompt_plans)
    write_json(
        round_dir / "edit_generation_result.json",
        {
            "brief": brief,
            "creative_directions": directions,
            "prompt_plans": prompt_plans,
            "outputs": outputs,
            "planner_model": planner_model,
        },
    )
    emit({"stage": "edit_loop_completed", "generated_count": len(outputs)})

    batch_id = f"edit_round_{round_id}"
    round_record = {
        "round_id": round_id,
        "batch_id": batch_id,
        "base_image_path": base_image_path,
        "brief": brief,
        "creative_directions": directions,
        "prompt_plans": prompt_plans,
        "direction_groups": direction_groups,
        "outputs": outputs,
        "planner_model": planner_model,
        "planner_attempted_models": planner_attempts,
        "component_refs": component_refs,
        "change_request": change_request,
        "lock_request": lock_request,
        "run_dir": str(round_dir),
    }
    result.setdefault("edit_rounds", []).append(round_record)
    result.setdefault("edit_history", []).append(
        {
            "prompt": change_request.strip() or "组件摆放 / 局部调整",
            "path": outputs[0]["path"] if outputs else base_image_path,
            "base_image_label": Path(base_image_path).name,
            "base_image_path": base_image_path,
            "reference_image_paths": flat_component_paths,
        }
    )
    result["current_candidates"] = outputs
    result["current_candidate_groups"] = direction_groups
    result["latest_batch_id"] = batch_id
    result["latest_image"] = outputs[0]["path"] if outputs else base_image_path
    return result


def render_evaluation_page(modules: dict[str, Any]) -> None:
    eval_module = modules["eval"]
    st.markdown('<div class="section-head"><h2>评估智能体</h2></div>', unsafe_allow_html=True)

    left, right = st.columns([0.95, 1.05])
    with left:
        eval_model = render_model_selectbox(
            modules,
            family="vision_chat",
            label="首选模型",
            key="eval_preferred_model",
            default_model=getattr(eval_module, "MODEL_NAME", modules["get_default_model"]("vision_chat")),
        )
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
        if uploaded:
            render_image(uploaded.getvalue())
        if st.button("开始评估", type="primary", use_container_width=True, key="eval_submit"):
            if not uploaded:
                st.error("请先上传一张图片。")
            else:
                with st.spinner("模型评估中..."):
                    try:
                        result = run_evaluation(modules, eval_module, uploaded, checklist_type, "", preferred_model=eval_model)
                        st.session_state["evaluation_result"] = result
                        st.session_state["evaluation_summary"] = ""
                        st.session_state.pop("evaluation_error", None)
                    except Exception as exc:
                        st.session_state["evaluation_error"] = str(exc)
                        st.session_state.pop("evaluation_result", None)
    with right:
        render_checklist_panel(eval_module.CHECKLISTS["main_detail" if option == "主图商详" else "media_ad"])

    if st.session_state.get("evaluation_error"):
        st.error(st.session_state["evaluation_error"])

    if st.session_state.get("evaluation_result"):
        build_eval_overall_ui(st.session_state["evaluation_result"])
        artifact_path = st.session_state["evaluation_result"].get("_artifact_path")
        if artifact_path and Path(artifact_path).exists():
            st.download_button(
                "下载评估 JSON",
                Path(artifact_path).read_text(encoding="utf-8"),
                file_name=Path(artifact_path).name,
                mime="application/json",
                use_container_width=False,
            )

        if "evaluation_summary" not in st.session_state:
            st.session_state["evaluation_summary"] = ""

        st.markdown("#### 基于 Checklist 的文字总结")
        if st.button("生成总结段", key="eval_summary_btn", use_container_width=True):
            with st.spinner("大模型生成总结中..."):
                try:
                    summary = generate_eval_summary(
                        modules,
                        eval_module,
                        st.session_state["evaluation_result"],
                        preferred_model=eval_model,
                    )
                    st.session_state["evaluation_summary"] = summary
                except Exception as exc:
                    st.error(f"生成总结失败：{exc}")

        if st.session_state["evaluation_result"].get("_resolved_model"):
            st.caption(f"评估模型：{st.session_state['evaluation_result']['_resolved_model']}")
        if st.session_state["evaluation_result"].get("_summary_resolved_model"):
            st.caption(f"总结模型：{st.session_state['evaluation_result']['_summary_resolved_model']}")

        if st.session_state["evaluation_summary"]:
            st.markdown(st.session_state["evaluation_summary"])
        else:
            st.caption("点击上方按钮，让模型基于当前评估结果生成一段文字总结。")

        build_eval_dimensions_ui(st.session_state["evaluation_result"])


def render_production_page(modules: dict[str, Any]) -> None:
    st.markdown('<div class="section-head"><h2>生产智能体</h2></div>', unsafe_allow_html=True)

    left, right = st.columns([1.02, 0.98])
    with left:
        generation_mode = st.radio(
            "背景生成方式",
            options=["图片提取背景", "文字生成背景"],
            horizontal=True,
            key="prod_generation_mode",
        )
        is_image_mode = generation_mode == "图片提取背景"

        bg_files = []
        background_prompt = ""
        use_case = "main_detail"
        audience = "电商消费者"
        scene = ""
        style = ""
        must_avoid: list[str] = []
        selling_points: list[str] = []
        reserve_component_space = True
        realism_level = "realistic"
        brand_tone_priority = ["reliable", "warm", "professional"]
        visual_density = "medium"
        direction_count = 3
        variants_per_direction = 2
        aspect_ratio = "1:1"
        must_have: list[str] = []
        preferred_text_model = modules["get_default_model"]("text_chat")
        preferred_image_generation_model = modules["get_default_model"]("image_generation")
        preferred_image_edit_model = modules["get_default_model"]("image_edit")
        if is_image_mode:
            preferred_image_edit_model = render_model_selectbox(
                modules,
                family="image_edit",
                label="提取背景首选模型",
                key="prod_preferred_image_edit_model_extract",
                default_model="qwen-image-edit-max",
            )
            bg_files = st.file_uploader(
                "成品参考图（主图/海报，用于提取背景）",
                type=["png", "jpg", "jpeg", "webp", "bmp"],
                accept_multiple_files=True,
                key=uploader_key("prod_bg"),
            )
            if st.button("清空已上传参考图", key="prod_bg_clear", use_container_width=False):
                reset_uploader("prod_bg")
                st.rerun()
        else:
            preferred_text_model = render_model_selectbox(
                modules,
                family="text_chat",
                label="创意方向首选模型",
                key="prod_preferred_text_model",
                default_model="qwen-plus",
            )
            preferred_image_generation_model = render_model_selectbox(
                modules,
                family="image_generation",
                label="背景生成首选模型",
                key="prod_preferred_image_generation_model",
                default_model="qwen-image-2.0-pro",
            )
            preferred_image_edit_model = render_model_selectbox(
                modules,
                family="image_edit",
                label="后续 Edit 首选模型",
                key="prod_preferred_image_edit_model_text",
                default_model="qwen-image-edit-max",
            )
            use_case_label = st.radio(
                "用途",
                options=["主图/商详", "媒介投放素材"],
                horizontal=True,
                key="prod_use_case",
            )
            use_case = "main_detail" if use_case_label == "主图/商详" else "media_ad"
            audience = st.text_input(
                "目标群体",
                value="年轻家庭",
                key="prod_audience",
            )
            scene = st.text_input(
                "场景",
                value="冬季居家夜间收纳场景",
                key="prod_scene",
            )
            style = st.text_input(
                "风格描述",
                value="高级写实，暖色照明",
                key="prod_style",
            )
            background_prompt = st.text_area(
                "补充描述",
                placeholder="例如：右侧希望更干净，整体带一点高级广告棚拍氛围，但不要出现任何人物、产品和文字。",
                height=120,
                key="prod_background_prompt",
            )
            col_a, col_b = st.columns(2)
            with col_a:
                aspect_ratio = st.selectbox(
                    "输出比例",
                    options=["1:1", "4:5", "16:9", "9:16"],
                    index=0,
                    key="prod_aspect_ratio",
                )
            size_options = {
                "1:1": ["1328*1328", "1024*1024"],
                "4:5": ["1080*1350"],
                "16:9": ["1600*900"],
                "9:16": ["900*1600"],
            }
            with col_b:
                size = st.selectbox(
                    "输出尺寸",
                    options=size_options[aspect_ratio],
                    index=0,
                    key="prod_size_text",
                )

            col_c, col_d = st.columns(2)
            with col_c:
                direction_count = st.slider("创意方向数", 1, 4, 3, key="prod_direction_count")
            with col_d:
                variants_per_direction = st.slider("每方向张数", 1, 4, 2, key="prod_variants_per_direction")

            reserve_component_space = st.checkbox(
                "预留组件摆放空间",
                value=True,
                key="prod_reserve_component_space",
            )
            realism_label = st.selectbox(
                "真实感程度",
                options=["写实", "半写实", "偏概念"],
                index=0,
                key="prod_realism_level",
            )
            realism_level = {
                "写实": "realistic",
                "半写实": "semi_realistic",
                "偏概念": "conceptual",
            }[realism_label]
            visual_density_label = st.selectbox(
                "视觉密度",
                options=["低", "中", "高"],
                index=1,
                key="prod_visual_density",
            )
            visual_density = {"低": "low", "中": "medium", "高": "high"}[visual_density_label]
            tone_labels = st.multiselect(
                "品牌调性优先级",
                options=["可靠", "温暖", "专业", "科技", "年轻"],
                default=["可靠", "温暖", "专业"],
                key="prod_brand_tone_priority",
            )
            tone_map = {
                "可靠": "reliable",
                "温暖": "warm",
                "专业": "professional",
                "科技": "tech",
                "年轻": "young",
            }
            brand_tone_priority = [tone_map[item] for item in tone_labels] or ["reliable", "warm", "professional"]
            must_avoid = parse_multiline_list(
                st.text_area(
                    "禁忌元素",
                    placeholder="每行一个，例如：\n不要出现人物正脸\n不要科技感过强\n不要卡通",
                    height=110,
                    key="prod_must_avoid",
                )
            )
            selling_points = parse_multiline_list(
                st.text_area(
                    "想突出的卖点",
                    placeholder="每行一个，例如：\n家庭安心\n可靠耐用",
                    height=100,
                    key="prod_selling_points",
                )
            )
            must_have = []
            if reserve_component_space:
                must_have.append("留出干净区域供后续摆放组件")
        if is_image_mode:
            col_a, col_b, col_c = st.columns(3)
            with col_a:
                aspect_ratio = st.selectbox(
                    "输出比例",
                    options=["1:1", "4:5", "16:9", "9:16"],
                    index=0,
                    key="prod_aspect_ratio_image",
                )
            image_size_options = {
                "1:1": ["1328*1328", "1024*1024"],
                "4:5": ["1080*1350"],
                "16:9": ["1600*900"],
                "9:16": ["900*1600"],
            }
            with col_b:
                size = st.selectbox(
                    "输出尺寸",
                    options=image_size_options[aspect_ratio],
                    index=0,
                    key="prod_size_image",
                )
            with col_c:
                image_sample_count = st.slider("提取次数", 1, 6, 3, key="prod_image_sample_count")
            direction_count = 1
            variants_per_direction = int(image_sample_count)
        button_label = "提取背景" if is_image_mode else "生成背景"
        progress_status = st.empty()
        progress_preview = st.empty()
        if st.button(button_label, type="primary", use_container_width=True, key="prod_generate"):
            if is_image_mode and not bg_files:
                st.error("请至少上传一张成品参考图。")
            elif not is_image_mode and (not audience.strip() or not scene.strip()):
                st.error("请至少填写目标群体和场景。")
            else:
                spinner_text = "正在提取背景..." if is_image_mode else "正在生成背景..."
                with st.spinner(spinner_text):
                    try:
                        partial_groups: dict[str, dict[str, Any]] = {}

                        def _progress(event: dict[str, Any]) -> None:
                            stage = event.get("stage")
                            if stage == "running":
                                progress_status.info("任务已开始，正在准备生产链路。")
                            elif stage == "task_brief_ready":
                                progress_status.info("已整理 task brief，正在生成创意方向。")
                            elif stage == "creative_directions_ready":
                                progress_status.info(f"已生成 {event.get('direction_count', 0)} 个创意方向，正在构建 prompts。")
                            elif stage == "prompt_plans_ready":
                                progress_status.info("模板化 prompts 已准备完成，开始调用生图模型。")
                            elif stage == "image_generated":
                                direction_id = str(event.get("direction_id") or "unknown")
                                direction_title = str(event.get("direction_title") or direction_id)
                                group = partial_groups.setdefault(
                                    direction_id,
                                    {"title": direction_title, "outputs": []},
                                )
                                group["title"] = direction_title
                                group["outputs"].append(
                                    {
                                        "path": event.get("path"),
                                        "variant_index": event.get("variant_index"),
                                        "resolved_model": event.get("resolved_model"),
                                    }
                                )
                                progress_status.info(
                                    f"已生成 {direction_title} 第 {event.get('variant_index')} 张，继续处理中。"
                                )
                                with progress_preview.container():
                                    render_partial_production_preview(partial_groups)
                            elif stage == "generation_completed":
                                progress_status.success(
                                    f"生成完成，共产出 {event.get('generated_count', 0)} 张结果。"
                                )

                        run_dir = make_run_dir("production_inputs")
                        grouped_paths = {
                            "background": save_many_uploads(bg_files or [], run_dir / "inputs" / "Background"),
                        }
                        result = run_generation(
                            modules=modules,
                            grouped_paths=grouped_paths,
                            generation_mode="image_to_background" if is_image_mode else "text_to_background",
                            background_prompt=background_prompt,
                            size=size,
                            use_case=use_case,
                            audience=audience,
                            scene=scene,
                            style=style,
                            must_have=must_have,
                            must_avoid=must_avoid,
                            selling_points=selling_points,
                            reserve_component_space=reserve_component_space,
                            realism_level=realism_level,
                            brand_tone_priority=brand_tone_priority,
                            visual_density=visual_density,
                            direction_count=int(direction_count),
                            variants_per_direction=int(variants_per_direction),
                            aspect_ratio=aspect_ratio,
                            preferred_text_model=preferred_text_model,
                            preferred_image_generation_model=preferred_image_generation_model,
                            preferred_image_edit_model=preferred_image_edit_model,
                            progress_callback=_progress,
                        )
                        st.session_state["production_result"] = result
                        st.session_state.pop("production_error", None)
                    except Exception as exc:
                        st.session_state["production_error"] = str(exc)
                        st.session_state.pop("production_result", None)

    if st.session_state.get("production_error"):
        st.error(st.session_state["production_error"])

    result = ensure_production_result_shape(st.session_state.get("production_result"))
    if result and result.get("workspace_dir"):
        st.session_state["production_result"] = result
    if result.get("outputs") or result.get("direction_groups") or result.get("edit_rounds") or result.get("boards"):
        if result.get("warnings"):
            for item in result["warnings"]:
                st.warning(item)
        if result.get("errors"):
            for item in result["errors"]:
                st.error(item)

        if result.get("boards"):
            st.markdown("#### 参考拼板（由上传图生成，供模型看图）")
            board_cols = st.columns(max(len(result["boards"]), 1))
            for idx, board in enumerate(result["boards"]):
                with board_cols[idx]:
                    render_image(board["path"], caption=board["name"])

        if result.get("task_brief"):
            with st.expander("查看 Task Brief", expanded=False):
                st.json(result["task_brief"])
        if result.get("preferred_models"):
            st.caption(
                "首选模型："
                f"方向规划 {result['preferred_models'].get('text_chat', '-')}"
                f" | 背景生成 {result['preferred_models'].get('image_generation', '-')}"
                f" | 图片编辑 {result['preferred_models'].get('image_edit', '-')}"
            )

        st.markdown("#### 生成结果")
        direction_groups = result.get("direction_groups") or []
        if direction_groups:
            for group_idx, group in enumerate(direction_groups, start=1):
                direction = group["direction"]
                is_extraction_group = direction.get("title") == "提取背景"
                if is_extraction_group:
                    st.markdown("##### 提取背景结果")
                    if direction.get("summary"):
                        st.caption(direction["summary"])
                else:
                    st.markdown(f"##### 方向 {group_idx} · {direction['title']}")
                    st.markdown(direction.get("summary", ""))
                    meta_left, meta_right = st.columns([0.55, 0.45])
                    with meta_left:
                        if direction.get("risk_points"):
                            st.caption("风险点：" + "；".join(direction.get("risk_points", [])))
                        if direction.get("recommendation_reason"):
                            st.caption("推荐理由：" + direction["recommendation_reason"])
                    with meta_right:
                        palette = direction.get("primary_palette") or []
                        elements = direction.get("scene_elements") or []
                        if palette:
                            st.caption("主色调：" + "、".join(palette))
                        if elements:
                            st.caption("场景元素：" + "、".join(elements))

                outputs = group.get("outputs") or []
                if outputs:
                    image_cols = st.columns(min(len(outputs), 3))
                    for idx, output in enumerate(outputs):
                        label = (
                            f"提取结果 · 第 {output['variant_index']} 张"
                            if is_extraction_group
                            else f"{direction['title']} · 第 {output['variant_index']} 张"
                        )
                        with image_cols[idx % len(image_cols)]:
                            render_image(output["path"], caption=label)
                            if output.get("resolved_model"):
                                st.caption(f"实际模型：{output['resolved_model']}")
                            st.download_button(
                                f"下载 {direction['direction_id']}_{output['variant_index']}",
                                Path(output["path"]).read_bytes(),
                                file_name=Path(output["path"]).name,
                                mime="image/png",
                                key=f"download_output_{direction['direction_id']}_{idx}",
                                use_container_width=True,
                            )
                else:
                    st.caption("该方向本轮暂无图片结果。若日志里有 429 或模型报错，可重试或切换首选模型。")
                prompt_plan = group.get("prompt_plan")
                if prompt_plan:
                    expander_title = (
                        "查看提取背景 Prompt"
                        if is_extraction_group
                        else f"查看 {direction['title']} 的模板化 Prompt"
                    )
                    with st.expander(expander_title, expanded=False):
                        sections = prompt_plan.get("sections") or {}
                        for title, content in sections.items():
                            st.markdown(f"**{title}**")
                            st.code(content, language="text")
                        st.markdown("**完整 Prompt**")
                        st.code(prompt_plan.get("prompt", ""), language="text")
        else:
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

        with st.expander("可选：文字图片生成器", expanded=False):
            render_text_generator_page(modules, embedded=True)

    render_edit_loop_section(modules, result)


def render_edit_loop_section(modules: dict[str, Any], result: dict[str, Any]) -> None:
    result = ensure_production_result_shape(result)
    st.markdown("#### Edit Loop")

    current_candidates = result.get("current_candidates") or []
    current_candidate_groups = result.get("current_candidate_groups") or []
    pending_base_source = st.session_state.pop("_pending_edit_loop_base_source", None)
    if pending_base_source:
        st.session_state["edit_loop_base_source"] = pending_base_source
    if current_candidate_groups:
        st.caption("当前最新候选批次。下一轮 Edit 默认会基于这一批图片继续生成。")
        for group in current_candidate_groups:
            direction = group.get("direction") or {}
            title = direction.get("title") or "最新方向"
            st.markdown(f"##### 当前候选 · {title}")
            outputs = group.get("outputs") or []
            if outputs:
                cols = st.columns(min(len(outputs), 3))
                for idx, output in enumerate(outputs):
                    with cols[idx % len(cols)]:
                        render_image(output["path"], caption=f"{title} · 第 {output.get('variant_index', idx + 1)} 张")
                        if st.button(
                            "设为下一轮 Base",
                            key=f"set_next_base_{title}_{idx}_{Path(output['path']).name}",
                            use_container_width=True,
                        ):
                            set_edit_loop_selected_base(output["path"])
                            request_edit_loop_base_source("从最新候选中选择")
                            st.rerun()
                        st.download_button(
                            f"下载当前候选 {title}_{idx + 1}",
                            Path(output["path"]).read_bytes(),
                            file_name=Path(output["path"]).name,
                            mime="image/png",
                            key=f"download_current_candidate_{title}_{idx}",
                            use_container_width=True,
                        )

    selected_base_path = str(st.session_state.get("edit_loop_selected_base_path") or "").strip()
    has_selected_history_base = bool(
        selected_base_path
        and Path(selected_base_path).exists()
        and not any(item.get("path") == selected_base_path for item in current_candidates)
    )
    base_source_options = ["从最新候选中选择", "直接上传一张图片"]
    if has_selected_history_base:
        base_source_options.insert(1, "使用已选历史图片")
    base_source = st.radio(
        "Base 图来源",
        options=base_source_options,
        horizontal=True,
        key="edit_loop_base_source",
    )
    base_image_path = ""
    base_label = ""
    if base_source == "从最新候选中选择" and current_candidates:
        output_options = {}
        for idx, output in enumerate(current_candidates, start=1):
            label = (
                f"{output.get('direction_title', '候选')} · 第 {output.get('variant_index', idx)} 张"
                if output.get("direction_title")
                else f"候选 {idx}"
            )
            output_options[label] = output["path"]
        selected_base_path = st.session_state.get("edit_loop_selected_base_path")
        default_label = next(
            (label for label, path in output_options.items() if path == selected_base_path),
            list(output_options.keys())[0],
        )
        base_label = st.radio(
            "选择一张最新候选图作为 Base",
            options=list(output_options.keys()),
            horizontal=True,
            index=list(output_options.keys()).index(default_label),
            key="edit_loop_base_candidate",
        )
        base_image_path = output_options[base_label]
        st.session_state["edit_loop_selected_base_path"] = base_image_path
        render_image(base_image_path, caption=f"Base 背景图：{base_label}")
    elif base_source == "使用已选历史图片" and has_selected_history_base:
        base_image_path = selected_base_path
        base_label = Path(selected_base_path).name
        render_image(base_image_path, caption=f"Base 背景图：历史选择 / {base_label}")
    else:
        uploaded_base = st.file_uploader(
            "上传 Base 图",
            type=["png", "jpg", "jpeg", "webp", "bmp"],
            key=uploader_key("edit_loop_upload_base"),
        )
        if st.button("清空已上传 Base 图", key="edit_loop_clear_base_upload", use_container_width=False):
            reset_uploader("edit_loop_upload_base")
            st.session_state.pop("edit_loop_selected_base_path", None)
            st.rerun()
        if uploaded_base:
            result = ensure_production_result_shape(result)
            base_image_path = save_uploaded_base_image(uploaded_base, result)
            st.session_state["production_result"] = result
            base_label = uploaded_base.name
            render_image(uploaded_base.getvalue(), caption=f"上传的 Base 图：{uploaded_base.name}")
        elif current_candidates:
            st.caption("如果不想从当前最新候选中选，也可以改成直接上传一张 Base 图。")
        else:
            st.caption("当前还没有最新候选，请直接上传一张 Base 图开始 Edit。")

    uploaded_components = st.file_uploader(
        "上传要加入的 Components（最多 2 个）",
        type=["png", "jpg", "jpeg", "webp", "bmp"],
        accept_multiple_files=True,
        key=uploader_key("edit_loop_components_upload"),
    )
    if st.button("清空已上传 Components", key="edit_loop_clear_components_upload", use_container_width=False):
        reset_uploader(
            "edit_loop_components_upload",
            state_keys_to_clear=[key for key in list(st.session_state.keys()) if key.startswith("edit_component_position_")],
        )
        st.rerun()
    component_refs: list[dict[str, str]] = []
    saved_component_paths: list[str] = []
    if uploaded_components:
        if len(uploaded_components) > 2:
            st.warning("当前最多只支持 2 个 component，系统将只使用前 2 个。")
        saved_component_paths = save_uploaded_components(list(uploaded_components), result)
        preview_cols = st.columns(min(len(saved_component_paths), 2))
        for idx, path in enumerate(saved_component_paths):
            with preview_cols[idx % len(preview_cols)]:
                render_image(path, caption=f"Component {idx + 1}")
    for idx, path in enumerate(saved_component_paths, start=1):
        label = Path(path).name
        position = st.text_input(
            f"{label} 的期望位置",
            placeholder="例如：右下角、靠中间偏右、左上角小角标",
            key=f"edit_component_position_{idx}",
        )
        component_refs.append(
            {
                "label": label,
                "path": path,
                "group": "uploaded_component",
                "position": position.strip(),
            }
        )

    change_request = st.text_area(
        "要变的地方",
        placeholder="例如：背景更暖一些；让画面更像真实家居夜景；加入电池体并放在右下角。",
        key="edit_loop_change_request",
        height=120,
    )
    lock_request = st.text_area(
        "要不变的地方",
        placeholder="例如：整体留白结构不要变；不要出现文字和 Logo；原图的暖色灯光氛围要保留。",
        key="edit_loop_lock_request",
        height=120,
    )
    col_a, col_b = st.columns(2)
    with col_a:
        edit_direction_count = st.slider("Edit 创意方向数", 1, 4, 1, key="edit_loop_direction_count")
    with col_b:
        edit_variants_per_direction = st.slider("Edit 每方向张数", 1, 4, 2, key="edit_loop_variants_per_direction")

    planner_model = render_model_selectbox(
        modules,
        family="vision_chat",
        label="Edit 规划首选模型",
        key="edit_loop_planner_model",
        default_model=modules["get_default_model"]("vision_chat"),
    )
    edit_image_model = render_model_selectbox(
        modules,
        family="image_edit",
        label="Edit 生图首选模型",
        key="edit_loop_image_model",
        default_model=result.get("preferred_models", {}).get("image_edit") or modules["get_default_model"]("image_edit"),
    )

    progress_status = st.empty()
    progress_preview = st.empty()
    if st.button("执行 Edit Loop", use_container_width=True, key="edit_loop_submit"):
        if not base_image_path:
            st.error("请先选择或上传一张 Base 图。")
        elif not change_request.strip() and not component_refs:
            st.error("请至少填写“要变的地方”，或选择一个 component。")
        else:
            try:
                partial_groups: dict[str, dict[str, Any]] = {}

                def _progress(event: dict[str, Any]) -> None:
                    stage = event.get("stage")
                    if stage == "edit_loop_running":
                        progress_status.info("正在理解 Base 图并规划 Edit 方向。")
                    elif stage == "edit_directions_ready":
                        progress_status.info(f"Edit 方向已完成，共 {event.get('direction_count', 0)} 个，开始生成。")
                    elif stage == "edit_prompt_ready":
                        progress_status.info("Edit prompts 已完成，开始逐张生成。")
                    elif stage == "edit_image_generated":
                        direction_id = str(event.get("direction_id") or "unknown")
                        direction_title = str(event.get("direction_title") or direction_id)
                        group = partial_groups.setdefault(direction_id, {"title": direction_title, "outputs": []})
                        group["title"] = direction_title
                        group["outputs"].append(
                            {
                                "path": event.get("path"),
                                "variant_index": event.get("variant_index"),
                                "resolved_model": event.get("resolved_model"),
                            }
                        )
                        progress_status.info(
                            f"已生成 {direction_title} 第 {event.get('variant_index')} 张，继续处理中。"
                        )
                        with progress_preview.container():
                            render_partial_production_preview(partial_groups)
                    elif stage == "edit_loop_completed":
                        progress_status.success(f"Edit 完成，共产出 {event.get('generated_count', 0)} 张。")

                updated = run_edit_loop(
                    modules,
                    result,
                    base_image_path=base_image_path,
                    component_refs=component_refs,
                    change_request=change_request,
                    lock_request=lock_request,
                    direction_count=int(edit_direction_count),
                    variants_per_direction=int(edit_variants_per_direction),
                    preferred_planner_model=planner_model,
                    preferred_image_edit_model=edit_image_model,
                    progress_callback=_progress,
                )
                updated.setdefault("preferred_models", {})
                updated["preferred_models"]["image_edit"] = edit_image_model
                st.session_state["production_result"] = updated
                if updated.get("current_candidates"):
                    st.session_state["edit_loop_selected_base_path"] = updated["current_candidates"][0]["path"]
                st.session_state.pop("production_error", None)
                result = updated
            except Exception as exc:
                st.session_state["production_error"] = str(exc)
                st.error(str(exc))

    if result.get("latest_image"):
        st.markdown("#### 当前最新结果")
        render_image(result["latest_image"])
        st.download_button(
            "下载当前最新结果",
            Path(result["latest_image"]).read_bytes(),
            file_name=Path(result["latest_image"]).name,
            mime="image/png",
            key="download_latest_edit_image",
            use_container_width=False,
        )

    if result.get("edit_rounds"):
        st.markdown("#### Edit 历史轮次")
        for round_idx, round_item in enumerate(reversed(result["edit_rounds"]), start=1):
            title = f"第 {len(result['edit_rounds']) - round_idx + 1} 轮 Edit"
            with st.expander(title, expanded=False):
                st.caption(f"Base：{Path(round_item.get('base_image_path', '')).name}")
                if round_item.get("component_refs"):
                    st.caption(
                        "Components："
                        + "；".join(
                            f"{item.get('label')} @ {item.get('position') or '自动判断'}"
                            for item in round_item.get("component_refs", [])
                        )
                    )
                if round_item.get("change_request"):
                    st.caption(f"要变的地方：{round_item['change_request']}")
                if round_item.get("lock_request"):
                    st.caption(f"要不变的地方：{round_item['lock_request']}")
                for group in round_item.get("direction_groups", []):
                    direction = group.get("direction") or {}
                    st.markdown(f"**{direction.get('title', 'Edit 方向')}**")
                    outputs = group.get("outputs") or []
                    cols = st.columns(min(len(outputs), 3)) if outputs else []
                    for idx, output in enumerate(outputs):
                        with cols[idx % len(cols)]:
                            render_image(output["path"], caption=f"第 {output.get('variant_index', idx + 1)} 张")
                            if st.button(
                                "设为下一轮 Base",
                                key=f"set_history_base_{round_item['round_id']}_{direction.get('direction_id', 'edit')}_{idx}",
                                use_container_width=True,
                            ):
                                set_edit_loop_selected_base(output["path"])
                                request_edit_loop_base_source("使用已选历史图片")
                                st.rerun()
                            st.download_button(
                                f"下载历史 {direction.get('direction_id', 'edit')}_{idx}",
                                Path(output["path"]).read_bytes(),
                                file_name=Path(output["path"]).name,
                                mime="image/png",
                                key=f"download_edit_history_{round_item['round_id']}_{direction.get('direction_id', 'edit')}_{idx}",
                                use_container_width=True,
                            )


def render_labeling_page(modules: dict[str, Any]) -> None:
    label_module = modules["label"]
    st.markdown('<div class="section-head"><h2>素材库智能体</h2></div>', unsafe_allow_html=True)
    st.markdown('<p class="nav-note">这一页只做标签识别，评分模块已移除。</p>', unsafe_allow_html=True)

    left, right = st.columns([0.92, 1.08])
    with left:
        labeling_model = render_model_selectbox(
            modules,
            family="vision_chat",
            label="首选模型",
            key="label_preferred_model",
            default_model=modules["get_default_model"]("vision_chat"),
        )
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
                        result = run_labeling(modules, label_module, uploaded, preferred_model=labeling_model)
                        st.session_state["labeling_result"] = result
                        st.session_state.pop("labeling_error", None)
                    except Exception as exc:
                        st.session_state["labeling_error"] = str(exc)
                        st.session_state.pop("labeling_result", None)

    if st.session_state.get("labeling_error"):
        st.error(st.session_state["labeling_error"])

    result = st.session_state.get("labeling_result")
    if result:
        if result.get("_resolved_model"):
            st.caption(f"实际模型：{result['_resolved_model']}")
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


def render_text_generator_page(modules: dict[str, Any], embedded: bool = False) -> None:
    text_module = modules["text"]
    if embedded:
        st.markdown("#### 文字图片生成器")
        st.caption("可选小功能：输入 headline，生成透明文字图层 PNG、预览图和元数据。")
    else:
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
    else:
        render_labeling_page(modules)

    st.markdown("---")


if __name__ == "__main__":
    main()
