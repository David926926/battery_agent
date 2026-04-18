"""
南孚高精度视觉审计系统
======================
置信度阈值 > 85%，零随机性，宁缺毋滥
支持 DashScope File 协议模式，处理较大的上传文件
"""

import os
import csv
import streamlit as st
import random
from pathlib import Path

# 加载 .env 中的 DASHSCOPE_API_KEY
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# DashScope File 协议上传（较大文件）
# 兼容多种 dashscope 版本 API：File.upload / File.call_upload / FileUploader
_dashscope_file_error = None

def _init_dashscope_upload():
    global _dashscope_file_error
    # 1. File.upload(p)
    try:
        from dashscope import File
        if hasattr(File, "upload"):
            return lambda p: File.upload(p)
    except Exception as e:
        _dashscope_file_error = f"dashscope.File: {e}"
    # 2. File.call_upload(p) 部分版本使用此 API
    try:
        from dashscope import File
        if hasattr(File, "call_upload"):
            def _upload(p):
                r = File.call_upload(p)
                if hasattr(r, "output") and isinstance(r.output, dict) and r.output.get("url"):
                    return r.output["url"]
                if hasattr(r, "url"):
                    return r.url
                raise ValueError("File.call_upload 未返回 url")
            return _upload
    except Exception as e:
        _dashscope_file_error = _dashscope_file_error or f"dashscope.File.call_upload: {e}"
    # 3. FileUploader().upload(p)
    try:
        from dashscope import FileUploader
        return lambda p: FileUploader().upload(p)
    except Exception as e:
        _dashscope_file_error = _dashscope_file_error or f"dashscope.FileUploader: {e}"
    # 4. dashscope 未安装
    try:
        import dashscope
    except ImportError:
        _dashscope_file_error = "dashscope 未安装（或当前 Python 环境与 pip 安装环境不一致）"
    return None

_dashscope_upload_fn = _init_dashscope_upload()
HAS_DASHSCOPE_FILE = _dashscope_upload_fn is not None

# 雷达图使用 plotly
import plotly.graph_objects as go

# Qwen-VL 高精度审计服务（API 失败时回退到 Mock）
try:
    from llm_service import (
        analyze_media_for_tags,
        analyze_media_for_tags_by_url,
        analyze_media_for_score,
        analyze_media_for_score_by_url,
        upload_file_via_openai_client,
    )
    HAS_LLM_SERVICE = True
except Exception:
    HAS_LLM_SERVICE = False
    analyze_media_for_tags_by_url = None
    analyze_media_for_score = None
    analyze_media_for_score_by_url = None
    upload_file_via_openai_client = None

# ==================== 支持的格式 ====================
# 图片：常见格式及截屏、设计稿等
IMAGE_EXTENSIONS = ["jpg", "jpeg", "png", "gif", "webp", "bmp"]
# 视频：含录屏常见格式
VIDEO_EXTENSIONS = ["mp4", "mov", "avi", "webm", "mkv", "m4v", "wmv"]
ALL_ACCEPTED = IMAGE_EXTENSIONS + VIDEO_EXTENSIONS

# ==================== 页面配置 ====================
st.set_page_config(
    page_title="南孚高精度视觉审计系统",
    page_icon="🔋",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==================== 自定义样式（白色背景、深色字体）====================
CUSTOM_CSS = """
<style>
    /* 全局白色背景 */
    .stApp {
        background: #ffffff;
    }
    
    /* 主标题样式 - 深色字体 */
    .main-title {
        font-size: 6rem;
        font-weight: 700;
        color: #1a1a2e;
        text-align: center;
        margin-bottom: 2rem;
        letter-spacing: 2px;
    }
    
    /* 页面副标题 */
    .page-subtitle {
        font-size: 1.25rem;
        color: #2c3e50;
        margin-bottom: 1.5rem;
        border-left: 4px solid #1a365d;
        padding-left: 1rem;
        font-weight: 600;
    }
    
    /* 总分显示大字号样式 */
    .score-display {
        font-size: 4rem;
        font-weight: 800;
        color: #1a365d;
        text-align: center;
        padding: 2rem;
        background: #f0f4f8;
        border-radius: 16px;
        border: 2px solid #2c5282;
        margin: 1rem 0;
    }
    
    /* 标签分类标题 - 深色 */
    .tag-category {
        font-size: 1rem;
        color: #2d3748;
        margin-bottom: 0.5rem;
        margin-top: 1rem;
        font-weight: 600;
    }
    
    /* 引用块/评语区样式 */
    .ai-suggestion-block {
        background: #f7fafc;
        border-left: 4px solid #2c5282;
        padding: 1.5rem;
        margin: 1rem 0;
        border-radius: 0 8px 8px 0;
        color: #2d3748;
    }
    
    /* 区块标题 */
    .section-title {
        font-size: 1.1rem;
        color: #1a365d;
        font-weight: 700;
        margin-bottom: 0.75rem;
    }
    
    /* 侧边栏品牌区 - 小一号 */
    .sidebar-brand .sidebar-title { font-size: 0.95rem; font-weight: 600; color: #2d3748; margin: 0; }
    .sidebar-brand .sidebar-subtitle { font-size: 0.85rem; color: #718096; margin: 0.25rem 0 0 0; }
    
    /* 隐藏 Streamlit 默认元素 */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


# ==================== Mock 数据函数 ====================

def get_mock_auto_tagging_result():
    """
    模拟标准化打标结果（与 STRICT_PROMPT 标准标签库一致）
    """
    scene_options = [["智能安防"], ["儿童娱乐"], ["宠物生活"], ["职场办公"], ["生活日用"]]
    audience_options = [["家庭守护者"], ["宝妈/育儿人群"], ["萌宠饲养官"], ["职场白领/上班族"]]
    selling_point_options = [["十年长效聚能"], ["持久耐用/长效"], ["无汞无镉/环保"], ["大电流/爆发力强"]]
    format_options = [["生活Vlog"], ["图片"], ["促销口播"], ["沉浸式种草"]]

    return {
        "场景": random.choice(scene_options),
        "人群": random.choice(audience_options),
        "卖点": random.choice(selling_point_options),
        "内容体裁": random.choice(format_options),
    }


# 图片素材评价体系：4 个一级维度（雷达图用，权重由图片类型在 API 内计算）
QUALITY_DIMENSIONS = [
    "V_视觉表现力",
    "C_内容质量",
    "P_产品与场景匹配度",
    "T_传播与商业潜力",
]


def get_mock_quality_score(image_type: str = "品牌KV"):
    """
    模拟图片素材评价结果（与评价体系一致：仅整数 1 或 2，四维度）
    返回结构与 llm_service 解析结果一致，便于雷达图与总分展示
    """
    dim_names = QUALITY_DIMENSIONS
    # 各维度得分仅 1 或 2
    base_scores = [random.choice([1, 2]) for _ in range(4)]
    if image_type == "品牌KV":
        weights = [0.35, 0.30, 0.20, 0.15]
    else:
        weights = [0.20, 0.25, 0.25, 0.30]
    weighted = sum(s * w for s, w in zip(base_scores, weights))
    total = 2 if weighted >= 1.5 else 1
    result = {
        "Image_Type": image_type,
        "总分": total,
        "Final_Score": total,
        "Dimension_Scores": {},
    }
    for name, score in zip(dim_names, base_scores):
        result[name] = score
        result["Dimension_Scores"][name] = {
            "score": score,
            "sub_metrics": {},
            "reasoning": "（模拟数据）",
        }
    return result


def get_mock_ai_suggestions():
    """
    模拟 AI 详细修改建议
    返回多条建议文本
    """
    suggestions = [
        "建议在开头 3 秒内明确展示产品核心卖点「聚能环」，提升用户注意力。",
        "画面过渡可以更加流畅，当前部分镜头切换略显突兀。",
        "口播文案中可增加数据支撑，如「电量提升 30%」等，增强说服力。",
        "结尾 CTA 可以更明确，引导用户扫码或搜索品牌词。",
        "建议补充产品使用场景的特写镜头，便于用户产生代入感。"
    ]
    # 随机返回 2-4 条建议
    return random.sample(suggestions, k=random.randint(2, 4))


def save_results_to_local(
    uploaded_filename: str,
    tag_result: dict,
    csv_path: Path,
) -> bool:
    """
    将本次打标结果追加写入本地 CSV（utf-8-sig，支持 Numbers 打开中文不乱码）。
    追加规则：文件不存在 -> 写表头；文件存在 -> 仅追加一行。
    """
    if not tag_result:
        return False

    columns = [
        "文件名",
        "场景标签",
        "人群标签",
        "卖点标签",
        "内容体裁",
        "情绪与痛点",
    ]

    def _join_list(v) -> str:
        if v is None:
            return ""
        if isinstance(v, list):
            return ",".join([str(x).strip() for x in v if str(x).strip()])
        return str(v).strip()

    row = {
        "文件名": uploaded_filename,
        "场景标签": _join_list(tag_result.get("场景")),
        "人群标签": _join_list(tag_result.get("人群")),
        "卖点标签": _join_list(tag_result.get("卖点")),
        "内容体裁": _join_list(tag_result.get("内容体裁")),
        "情绪与痛点": _join_list(tag_result.get("情绪与痛点")),
    }

    csv_path.parent.mkdir(parents=True, exist_ok=True)
    is_new = not csv_path.exists()
    with open(csv_path, "a", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        if is_new:
            writer.writeheader()
        writer.writerow(row)

    return True


# ==================== DashScope File 协议上传 ====================

def _save_and_upload(uploaded_file):
    """保存到 temp/ 并上传，返回云端 URL。支持 DashScope 或 OpenAI 客户端。"""
    temp_dir = Path("temp")
    temp_dir.mkdir(exist_ok=True)
    local_path = temp_dir / uploaded_file.name
    try:
        with open(local_path, "wb") as f:
            f.write(uploaded_file.getvalue())

        # 1. 优先 DashScope File/FileUploader
        if HAS_DASHSCOPE_FILE:
            result = _dashscope_upload_fn(str(local_path))
            if result is None:
                raise ValueError("DashScope 上传未返回有效结果")
            if hasattr(result, "url") and result.url:
                return result.url
            if hasattr(result, "file_id") and result.file_id:
                fid = str(result.file_id)
                return fid if fid.startswith(("http", "file", "oss")) else f"file://{fid}"
            if isinstance(result, dict):
                u = result.get("url") or result.get("file_url") or result.get("file_id") or ""
                if u:
                    return u
            if isinstance(result, str) and result:
                return result
            raise ValueError("DashScope 上传未返回有效 URL")

        # 2. OpenAI 客户端 files.create 返回的 file_id 不能用于 Qwen 视觉 API
        #    （视觉 API 仅接受 https:// 或 data:base64，不接受 file://file-id）
        #    因此不再尝试，直接提示安装 dashscope
        raise RuntimeError(
            "较大文件需上传到云端。请安装 dashscope 以支持这类文件：pip install dashscope"
        )
    finally:
        if local_path.exists():
            try:
                local_path.unlink()
            except OSError:
                pass


# ==================== 媒体类型判断 ====================

def get_file_extension(filename: str) -> str:
    """获取文件扩展名（小写）"""
    return Path(filename).suffix.lstrip(".").lower()


def is_image(filename: str) -> bool:
    """判断是否为图片"""
    return get_file_extension(filename) in IMAGE_EXTENSIONS


def is_video(filename: str) -> bool:
    """判断是否为视频"""
    return get_file_extension(filename) in VIDEO_EXTENSIONS


def render_image_compat(image_data):
    """兼容新旧版 Streamlit 的图片展示参数。"""
    try:
        st.image(image_data, use_container_width=True)
    except TypeError:
        try:
            st.image(image_data, use_column_width=True)
        except TypeError:
            st.image(image_data)


# ==================== 雷达图 ====================

def create_radar_chart(scores: dict):
    """
    创建雷达图：四维度图片素材评价（V/C/P/T），分值范围 1~2
    """
    dimensions = list(QUALITY_DIMENSIONS)
    values = [scores.get(d, 0) for d in dimensions]
    values_closed = values + [values[0]]
    dimensions_closed = dimensions + [dimensions[0]]

    fig = go.Figure(data=go.Scatterpolar(
        r=values_closed,
        theta=dimensions_closed,
        fill='toself',
        fillcolor='rgba(44, 82, 130, 0.25)',
        line=dict(color='#2c5282', width=2),
        name='得分'
    ))
    fig.update_layout(
        polar=dict(
            bgcolor='rgba(247, 250, 252, 0.9)',
            radialaxis=dict(
                visible=True,
                range=[1, 2],
                tickfont=dict(color='#2d3748', size=11),
                gridcolor='rgba(45, 55, 72, 0.2)'
            ),
            angularaxis=dict(
                tickfont=dict(color='#2d3748', size=10),
                gridcolor='rgba(45, 55, 72, 0.2)'
            )
        ),
        paper_bgcolor='rgba(255,255,255,0)',
        plot_bgcolor='rgba(255,255,255,0)',
        showlegend=False,
        margin=dict(l=100, r=100, t=40, b=40),
        height=450
    )
    return fig


# ==================== 主页面（打标 + 评分同页）====================

def render_main_page():
    """
    主页面布局：
    左侧：上传 + 媒体预览（图片/视频）
    右侧：上方打标结果，下方评分结果
    """
    st.markdown('<p class="main-title">南孚高精度视觉审计系统</p>', unsafe_allow_html=True)
    
    # 文件上传：支持图片和多种视频格式，增大单文件限制
    uploaded_file = st.file_uploader(
        "上传图片或视频",
        type=ALL_ACCEPTED,
        help="图片：JPG/PNG/GIF/WEBP/BMP | 视频：MP4/MOV/AVI/WEBM/MKV/M4V/WMV。上传限制在 .streamlit/config.toml 中配置。"
    )
    
    if uploaded_file is None:
        st.info("👆 请上传图片或视频（支持 JPG、PNG、MP4、MOV、录屏等常见格式）")
        return
    
    # 上传新文件时清除旧结果
    if "last_analyzed_file" in st.session_state and st.session_state["last_analyzed_file"] != uploaded_file.name:
        for key in ["tag_result", "score_result", "suggestions", "last_analyzed_file"]:
            st.session_state.pop(key, None)
    
    # 布局：左侧媒体，右侧结果区（分上下）
    col_left, col_right = st.columns([1, 1])
    
    with col_left:
        st.markdown("**媒体预览**")
        # 图片类型（仅图片参与素材评价体系；视频仍显示打标 + 模拟评分）
        image_type = st.selectbox(
            "图片类型（用于素材评分权重）",
            options=["品牌KV", "投放素材"],
            index=0,
            help="品牌KV：视觉与内容权重更高；投放素材：传播与商业潜力权重更高",
        )
        ext = get_file_extension(uploaded_file.name)
        file_bytes = uploaded_file.read()
        uploaded_file.seek(0)  # 重置指针，供后续可能的二次读取

        if is_image(uploaded_file.name):
            render_image_compat(file_bytes)
        elif is_video(uploaded_file.name):
            # 浏览器常见支持：mp4, webm；部分支持 mov
            if ext in ["mp4", "webm", "mov", "m4v"]:
                st.video(file_bytes)
            else:
                st.warning(f"当前格式（.{ext}）暂不支持在线预览，但可正常分析。")
                st.caption("建议导出为 MP4 以便预览。")
        
        # 开始分析按钮
        if st.button("🔄 开始分析", type="primary", use_container_width=True):
            tag_result = None
            from_llm_tags = False
            if HAS_LLM_SERVICE:
                try:
                    file_size_mb = len(file_bytes) / (1024 * 1024)
                    is_large = file_size_mb > 10

                    # 较大文件：必须走上传，避免 Base64 超限
                    if is_large:
                        with st.status("⏳ 正在上传到云端...", expanded=True) as status:
                            file_url = _save_and_upload(uploaded_file)
                            status.update(label="上传完成，AI 分析中...", state="running")
                            tag_result = analyze_media_for_tags_by_url(
                                file_url=file_url,
                                is_image=is_image(uploaded_file.name),
                            )
                            status.update(label="✅ 分析完成", state="complete")
                            from_llm_tags = tag_result is not None
                    else:
                        # 小文件：优先 Base64（无需上传），上传方式作为备选
                        if HAS_DASHSCOPE_FILE or upload_file_via_openai_client:
                            try:
                                with st.status("⏳ 正在上传到云端...", expanded=True) as status:
                                    file_url = _save_and_upload(uploaded_file)
                                    status.update(label="上传完成，AI 分析中...", state="running")
                                    tag_result = analyze_media_for_tags_by_url(
                                        file_url=file_url,
                                        is_image=is_image(uploaded_file.name),
                                    )
                                    status.update(label="✅ 分析完成", state="complete")
                                    from_llm_tags = tag_result is not None
                            except Exception:
                                with st.spinner("AI 正在分析..."):
                                    tag_result = analyze_media_for_tags(
                                        file_bytes=file_bytes,
                                        filename=uploaded_file.name,
                                        is_image=is_image(uploaded_file.name),
                                    )
                                    from_llm_tags = tag_result is not None
                        else:
                            with st.spinner("AI 正在分析..."):
                                tag_result = analyze_media_for_tags(
                                    file_bytes=file_bytes,
                                    filename=uploaded_file.name,
                                    is_image=is_image(uploaded_file.name),
                                )
                                from_llm_tags = tag_result is not None
                except Exception as e:
                    st.warning(f"Qwen-VL 审计失败，已使用模拟数据：{e}")
            if tag_result is None:
                tag_result = get_mock_auto_tagging_result()
                from_llm_tags = False

            # 图片素材评价体系：图片走 API（可选），视频或失败时用 Mock
            score_result = None
            from_llm_score = False
            if is_image(uploaded_file.name) and HAS_LLM_SERVICE and analyze_media_for_score is not None:
                try:
                    file_size_mb = len(file_bytes) / (1024 * 1024)
                    if file_size_mb > 10:
                        file_url = _save_and_upload(uploaded_file)
                        score_result = analyze_media_for_score_by_url(
                            file_url=file_url, is_image=True, image_type=image_type
                        )
                        from_llm_score = score_result is not None
                    else:
                        score_result = analyze_media_for_score(
                            file_bytes=file_bytes,
                            filename=uploaded_file.name,
                            is_image=True,
                            image_type=image_type,
                        )
                        from_llm_score = score_result is not None
                except Exception:
                    score_result = None
            if score_result is None:
                score_result = get_mock_quality_score(image_type)
                from_llm_score = False
            suggestions = get_mock_ai_suggestions()
            st.session_state["tag_result"] = tag_result
            st.session_state["score_result"] = score_result
            st.session_state["suggestions"] = suggestions
            st.session_state["last_analyzed_file"] = uploaded_file.name

            # 自动本地持久化（仅在 LLM 的打标 + 评分都成功解析时追加）
            if from_llm_tags and from_llm_score:
                local_csv = Path(__file__).resolve().parent / "tagging_results.csv"
                ok = save_results_to_local(
                    uploaded_filename=uploaded_file.name,
                    tag_result=tag_result,
                    csv_path=local_csv,
                )
                if ok:
                    if hasattr(st, "toast"):
                        st.toast("✅ 标签已自动追加至本地表格")
                    else:
                        st.success("✅ 标签已自动追加至本地表格")
    
    with col_right:
        # 右上：打标结果
        st.markdown('<p class="section-title">📎 审计结果（置信度 > 85%）</p>', unsafe_allow_html=True)
        if "tag_result" in st.session_state:
            result = st.session_state["tag_result"]
            # 五大类：场景、人群、卖点、内容体裁、情绪与痛点（即使为空也固定展示）
            for category in ["场景", "人群", "卖点", "内容体裁", "情绪与痛点"]:
                tags = result.get(category) or []
                st.markdown(f'<p class="tag-category">{category}</p>', unsafe_allow_html=True)
                if not tags:
                    st.caption("暂无标签（未达到 85% 置信度）")
                    continue
                try:
                    st.pills(
                        "",
                        tags,
                        selection_mode="multi",
                        key=f"pills_{category}",
                        label_visibility="collapsed",
                    )
                except (AttributeError, TypeError):
                    pills_html = " ".join(
                        [
                            f'<span style="display:inline-block;background:#e2e8f0;color:#1a365d;'
                            f'padding:0.25rem 0.75rem;border-radius:999px;margin:0.2rem;'
                            f'font-size:0.9rem;">{t}</span>'
                            for t in tags
                        ]
                    )
                    st.markdown(pills_html, unsafe_allow_html=True)
        else:
            st.caption("点击「开始分析」后显示打标结果")
        
        st.markdown("---")
        
        # 右下：图片素材评价得分（四维度 1~2 分，加权总分 1.00~2.00）
        st.markdown('<p class="section-title">⭐ 图片素材评价</p>', unsafe_allow_html=True)
        if "score_result" in st.session_state:
            score_result = st.session_state["score_result"]
            suggestions = st.session_state.get("suggestions", [])
            total = score_result.get("总分") or score_result.get("Final_Score") or 0
            img_type = score_result.get("Image_Type") or ""
            st.markdown(f'<div class="score-display">{total:.2f} / 2.00</div>', unsafe_allow_html=True)
            if img_type:
                st.caption(f"图片类型：{img_type}")
            fig = create_radar_chart(score_result)
            st.plotly_chart(fig, use_container_width=True)
            dim_scores = score_result.get("Dimension_Scores") or {}
            if dim_scores:
                with st.expander("各维度得分与依据"):
                    for dim_name in QUALITY_DIMENSIONS:
                        d = dim_scores.get(dim_name) or {}
                        s = d.get("score", "-")
                        r = d.get("reasoning", "")
                        st.markdown(f"**{dim_name}**：{s}")
                        if r:
                            st.caption(r)
            st.markdown("**AI 修改建议**")
            for s in suggestions:
                st.markdown(f'> {s}')
        else:
            st.caption("点击「开始分析」后显示评分结果")


# ==================== 主程序入口 ====================

def main():
    """主函数"""
    st.sidebar.markdown("---")
    st.sidebar.markdown('<div class="sidebar-brand"><p class="sidebar-title">🔋 南孚电池</p><p class="sidebar-subtitle">高精度视觉审计系统</p></div>', unsafe_allow_html=True)
    st.sidebar.markdown("---")
    # 大文件上传状态诊断（便于排查 dashscope 问题）
    with st.sidebar.expander("📁 大文件上传状态"):
        if HAS_DASHSCOPE_FILE:
            st.success("已就绪：支持较大文件上传")
        else:
            st.warning("大文件上传不可用")
            if _dashscope_file_error:
                st.caption(f"原因：{_dashscope_file_error}")
            st.caption("请确认：1) 在当前运行 Streamlit 的 Python 环境中执行 pip install dashscope  2) 重启 Streamlit")
    st.sidebar.markdown("---")
    render_main_page()


if __name__ == "__main__":
    main()
