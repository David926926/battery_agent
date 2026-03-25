import os
import json
import base64
from pathlib import Path
from datetime import datetime
import mimetypes

import numpy as np
import soundfile as sf
from openai import OpenAI

from urllib.parse import urlparse

SYSTEM_PROMPT = (
    "You are a strict e-commerce creative quality auditor. "
    "Always output strictly valid JSON."
)

def url_to_media_block(url: str) -> dict:
    # 去掉 querystring，只看 path 后缀
    path = urlparse(url).path.lower()

    if path.endswith((".png", ".jpg", ".jpeg", ".webp")):
        return {"type": "image_url", "image_url": {"url": url}}

    if path.endswith((".mp4", ".mov", ".m4v", ".webm")):
        return {"type": "video_url", "video_url": {"url": url}}

    raise ValueError(f"无法识别媒体类型（请用图片或视频直链）：{url}")

def file_to_media_block(path: str) -> dict:
    """
    将本地图片/视频转为 OpenAI-compatible 的 base64 media block。
    优先用 mimetypes 判断；再用后缀兜底。
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"找不到本地文件: {path}")

    suffix = p.suffix.lower()
    mime, _ = mimetypes.guess_type(str(p))
    mime = (mime or "").lower()

    data_b64 = base64.b64encode(p.read_bytes()).decode("utf-8")

    # 图片
    if suffix in {".png", ".jpg", ".jpeg", ".webp"} or mime.startswith("image/"):
        # 兼容写法：image_url + data URI
        # 部分兼容接口也支持 {"type":"input_image","image_base64":...}，但这里用 data URI 更通用
        if not mime:
            mime = "image/png" if suffix == ".png" else "image/jpeg"
        return {
            "type": "image_url",
            "image_url": {"url": f"data:{mime};base64,{data_b64}"}
        }

    # 视频
    if suffix in {".mp4", ".mov", ".m4v", ".webm"} or mime.startswith("video/"):
        if not mime:
            mime = "video/mp4" if suffix in {".mp4", ".m4v"} else "video/quicktime"
        return {
            "type": "video_url",
            "video_url": {"url": f"data:{mime};base64,{data_b64}"}
        }

    raise ValueError(f"不支持的文件类型: {suffix} ({mime})")


# =========================
# 配置区
# =========================

DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY")
BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
MODEL_NAME = "qwen3-omni-flash"

# 你的素材文本（可为空，但建议至少给一句背景）
CONTENT_TEXT = ""
CHECKLIST_TYPE = "media_ad"  # 可选: "main_detail" (主图商详) / "media_ad" (媒介投放)

# ✅ 视频必须用 URL（不要本地路径 / 不要 base64）
MEDIA_URL = ""
MEDIA_PATH = "/Users/liyuanheng/Desktop/Battery Agent/Samples/3.16/bad_samples_主图商详/text/拼写错误或错别字_bad1.png"

# 输出文件名（带时间戳，避免覆盖）
ts = datetime.now().strftime("%Y%m%d_%H%M%S")
OUT_JSON = f"evaluation_{ts}.json"
# OUT_MD = f"evaluation_{ts}.md"
# OUT_WAV = f"evaluation_{ts}.wav"


# =========================
# 工具函数
# =========================
def ensure_key():
    if not DASHSCOPE_API_KEY:
        raise RuntimeError("❌ 未检测到环境变量 DASHSCOPE_API_KEY。请先 export DASHSCOPE_API_KEY='你的key'")

def ensure_media():
    if MEDIA_PATH:
        p = Path(MEDIA_PATH)
        if not p.exists():
            raise RuntimeError(f"❌ MEDIA_PATH 不存在：{MEDIA_PATH}")
        return

    if MEDIA_URL:
        if not (MEDIA_URL.startswith("http://") or MEDIA_URL.startswith("https://")):
            raise RuntimeError("❌ MEDIA_URL 必须是 http/https 开头的公网 URL。")
        return

    raise RuntimeError("❌ 请提供 MEDIA_PATH(本地文件) 或 MEDIA_URL(公网直链) 之一。")

CHECKLISTS = {
    "main_detail": {
        "title": "电商渠道 主图&商详 Checklist",
        "dimensions": {
            "Background": {
                "issue_tags": [
                    "场景无关",
                    "背景杂乱或噪点过多",
                    "明显的“AI生成”痕迹",
                    "人物或物体部位缺失/断裂",
                    "明显拼贴或合成痕迹",
                ],
                "severe": [
                    "场景无关",
                    "明显的“AI生成”痕迹",
                    "人物或物体部位缺失/断裂",
                    "明显拼贴或合成痕迹",
                ],
                "minor": [
                    "背景杂乱或噪点过多",
                ],
                "rules": {
                    "risky": "severe>=1 OR minor>=3",
                    "acceptable": "severe==0 AND minor in [1,2]",
                    "excellent": "severe==0 AND minor==0",
                }
            },
            "Object": {
                "issue_tags": [
                    "产品包装文字模糊或不可读",
                    "物体轮廓不完整（缺失或被裁切）",
                    "多余或重复部件（轮廓异常延展）",
                    "物体摆放或姿态不符合物理逻辑",
                    "光影或透视与场景不一致",
                    "比例或尺度不合理",
                    "未展示产品实物细节（增强确定性）",
                ],
                "severe": [
                    "产品包装文字模糊或不可读",
                    "物体轮廓不完整（缺失或被裁切）",
                    "多余或重复部件（轮廓异常延展）",
                    "物体摆放或姿态不符合物理逻辑",
                    "比例或尺度不合理",
                ],
                "minor": [
                    "光影或透视与场景不一致",
                    "未展示产品实物细节（增强确定性）",
                ],
                "rules": {
                    "risky": "severe>=1 OR minor>=2",
                    "acceptable": "severe==0 AND minor==1",
                    "excellent": "severe==0 AND minor==0",
                }
            },
            "Text": {
                "issue_tags": [
                    "行距或断行不合理",
                    "风格与品牌或海报调性不符",
                    "笔画渲染错误",
                    "拼写错误或错别字",
                    "缺少应出现的覆盖文字",
                    "字体过小",
                    "文字相互重叠（或与主体重叠）",
                ],
                "severe": [
                    "笔画渲染错误",
                    "拼写错误或错别字",
                    "缺少应出现的覆盖文字",
                    "字体过小",
                    "文字相互重叠（或与主体重叠）",
                ],
                "minor": [
                    "行距或断行不合理",
                    "风格与品牌或海报调性不符",
                ],
                "rules": {
                    "risky": "severe>=1 OR minor>=3",
                    "acceptable": "severe==0 AND minor in [1,2]",
                    "excellent": "severe==0 AND minor==0",
                }
            },
            "Layout": {
                "issue_tags": [
                    "画面过于拥挤或杂乱",
                    "留白过多",
                    "构图视觉不平衡",
                    "重要元素被遮挡或互相遮挡",
                    "信息层级不清晰",
                ],
                "severe": ["重要元素被遮挡或互相遮挡"],
                "minor": [
                    "画面过于拥挤或杂乱",
                    "留白过多",
                    "构图视觉不平衡",
                    "信息层级不清晰",
                ],
                "rules": {
                    "risky": "severe>=1 OR minor>=2",
                    "acceptable": "severe==0 AND minor==1",
                    "excellent": "severe==0 AND minor==0",
                }
            }
        },
        "overall_rule": {
            "score_formula": "(B+O+T+L)/4",
            "grade": {
                "excellent": "overall_score>=1.5 AND no_dim_risky",
                "acceptable": "0.75<=overall_score<1.5 AND risky_dims<=1",
                "risky": "overall_score<0.75 OR risky_dims>=2",
            }
        }
    },

    "media_ad": {
        "title": "电商渠道 媒介投放素材 Checklist",
        "dimensions": {
            "Background": {
                "issue_tags": [
                    "场景或语境较弱",
                    "场景无关",
                    "背景杂乱或噪点过多",
                    "明显的“AI生成”痕迹",
                    "人物或物体部位缺失/断裂",
                    "明显拼贴或合成痕迹",
                    "场景创新度不够",
                ],
                "severe": [
                    "场景无关",
                    "明显的“AI生成”痕迹",
                    "人物或物体部位缺失/断裂",
                    "明显拼贴或合成痕迹",
                ],
                "minor": [
                    "场景或语境较弱",
                    "背景杂乱或噪点过多",
                    "场景创新度不够",
                ],
                "rules": {
                    "risky": "severe>=1 OR minor>=3",
                    "acceptable": "severe==0 AND minor in [1,2]",
                    "excellent": "severe==0 AND minor==0",
                }
            },
            "Object": {
                "issue_tags": [
                    "产品包装文字模糊或不可读",
                    "物体轮廓不完整（缺失或被裁切）",
                    "多余或重复部件（轮廓异常延展）",
                    "物体摆放或姿态不符合物理逻辑",
                    "光影或透视与场景不一致",
                    "比例或尺度不合理",
                    "明显合成痕迹",
                    "产品未形成视觉焦点",
                    "用户难以理解该设备为何会使用本产品（如燃气表）",
                ],
                "severe": [
                    "产品包装文字模糊或不可读",
                    "物体轮廓不完整（缺失或被裁切）",
                    "多余或重复部件（轮廓异常延展）",
                    "物体摆放或姿态不符合物理逻辑",
                    "比例或尺度不合理",
                    "用户难以理解该设备为何会使用本产品（如燃气表）",
                ],
                "minor": [
                    "光影或透视与场景不一致",
                    "明显合成痕迹",
                    "产品未形成视觉焦点",
                ],
                "rules": {
                    "risky": "severe>=1 OR minor>=2",
                    "acceptable": "severe==0 AND minor==1",
                    "excellent": "severe==0 AND minor==0",
                }
            },
            "Text": {
                "issue_tags": [
                    "拼写错误或错别字",
                    "缺少应出现的覆盖文字",
                    "字体过小",
                    "文字相互重叠（或与主体重叠）",
                ],
                "severe": [
                    "拼写错误或错别字",
                    "缺少应出现的覆盖文字",
                    "字体过小",
                    "文字相互重叠（或与主体重叠）",
                ],
                "minor": [
                ],
                "rules": {
                    "risky": "severe>=1 OR minor>=3",
                    "acceptable": "severe==0 AND minor in [1,2]",
                    "excellent": "severe==0 AND minor==0",
                }
            },
            "Layout": {
                "issue_tags": [
                    "画面过于拥挤或杂乱",
                    "留白过多",
                    "构图视觉不平衡",
                    "重要元素被遮挡或互相遮挡",
                ],
                "severe": ["重要元素被遮挡或互相遮挡"],
                "minor": [
                    "画面过于拥挤或杂乱",
                    "留白过多",
                    "构图视觉不平衡",
                ],
                "rules": {
                    "risky": "severe>=1 OR minor>=2",
                    "acceptable": "severe==0 AND minor==1",
                    "excellent": "severe==0 AND minor==0",
                }
            }
        },
        "overall_rule": {  # 你这套和主图商详一致
            "score_formula": "(B+O+T+L)/4",
            "grade": {
                "excellent": "overall_score>=1.5 AND no_dim_risky",
                "acceptable": "0.75<=overall_score<1.5 AND risky_dims<=1",
                "risky": "overall_score<0.75 OR risky_dims>=2",
            }
        }
    }
}

def build_dimension_output_schema(dim_names: list[str]) -> str:
    blocks = []
    for idx, dim_name in enumerate(dim_names):
        body = f'''"{dim_name}": {{
      "issue_tags": [],
      "other_tags": [],
      "severe_count": 0,
      "minor_count": 0,
      "grade": "Excellent/Acceptable/Risky",
      "score": 0,
      "evidence": ["列出1-3条可观察证据（例如：某处文字模糊/遮挡/场景不符等）"]
    }}'''
        if idx < len(dim_names) - 1:
            body += ","
        blocks.append(body)
    return "\n".join(blocks)


def normalize_result(result: dict, checklist_type: str) -> dict:
    cfg = CHECKLISTS[checklist_type]
    dim_names = list(cfg["dimensions"].keys())
    dim_results = result.get("dimensions")
    if not isinstance(dim_results, dict):
        dim_results = {}

    normalized_dimensions = {}
    risky_dims = 0
    score_sum = 0.0

    for dim_name in dim_names:
        raw_dim = dim_results.get(dim_name)
        if not isinstance(raw_dim, dict):
            raw_dim = {}

        score = raw_dim.get("score", 0)
        try:
            score = float(score)
        except Exception:
            score = 0.0

        grade = raw_dim.get("grade", "Risky")
        if grade not in {"Excellent", "Acceptable", "Risky"}:
            grade = "Risky"

        if grade == "Risky":
            risky_dims += 1
        score_sum += score

        normalized_dimensions[dim_name] = {
            "issue_tags": raw_dim.get("issue_tags") if isinstance(raw_dim.get("issue_tags"), list) else [],
            "other_tags": raw_dim.get("other_tags") if isinstance(raw_dim.get("other_tags"), list) else [],
            "severe_count": int(raw_dim.get("severe_count", 0) or 0),
            "minor_count": int(raw_dim.get("minor_count", 0) or 0),
            "grade": grade,
            "score": score,
            "evidence": raw_dim.get("evidence") if isinstance(raw_dim.get("evidence"), list) else [],
        }

    overall_score = result.get("overall_score")
    try:
        overall_score = float(overall_score)
    except Exception:
        overall_score = score_sum / max(len(dim_names), 1)

    overall_grade = result.get("overall_grade")
    if overall_grade not in {"Excellent", "Acceptable", "Risky"}:
        if overall_score >= 1.5 and risky_dims == 0:
            overall_grade = "Excellent"
        elif overall_score >= 0.75 and risky_dims <= 1:
            overall_grade = "Acceptable"
        else:
            overall_grade = "Risky"

    return {
        "checklist_type": checklist_type,
        "material_summary": str(result.get("material_summary", "") or ""),
        "assumptions": str(result.get("assumptions", "") or ""),
        "dimensions": normalized_dimensions,
        "overall_score": overall_score,
        "overall_grade": overall_grade,
        "rationale": str(result.get("rationale", "") or ""),
    }


def build_prompt(user_content: str, checklist_type: str) -> str:
    cfg = CHECKLISTS[checklist_type]
    dim_names = list(cfg["dimensions"].keys())

    # 拼维度说明（让模型“先勾 tag，再数 severe/minor，再按规则判定”）
    dim_blocks = []
    for dim_name, dim_cfg in cfg["dimensions"].items():
        tags = "\n- ".join(dim_cfg["issue_tags"])
        severe = "\n- ".join(dim_cfg["severe"])
        minor = "\n- ".join(dim_cfg["minor"])

        rules = dim_cfg["rules"]
        dim_blocks.append(f"""
【{dim_name}】
Issue tags（从下列中勾选，可多选）：
- {tags}

严重问题（命中任一即计入 severe_count）：
- {severe}

一般问题（命中即计入 minor_count）：
- {minor}

判定规则（必须严格执行，禁止主观调分）：
- Risky(0): {rules["risky"]}
- Acceptable(1): {rules["acceptable"]}
- Excellent(2): {rules["excellent"]}
""".strip())

    dim_text = "\n\n".join(dim_blocks)
    dimension_list = " + ".join(dim_names)
    score_formula = cfg["overall_rule"]["score_formula"]
    dimension_schema = build_dimension_output_schema(dim_names)

    overall = cfg["overall_rule"]["grade"]

    return f"""
你是“电商素材质量审核员”。你必须严格遵守《{cfg["title"]}》。

工作流程（必须按顺序）：
1) 只基于画面真实可见信息，先勾选每个维度命中的 issue_tags（从提供列表中选，不要自造新tag；若确实需要补充，用 other_tags 字段）。
2) 统计 severe_count 与 minor_count（只统计该维度定义的 severe/minor）。
3) 严格按该维度判定规则产出 grade 与 score（Excellent=2 / Acceptable=1 / Risky=0）。
4) 计算 overall_score = ({dimension_list}) / {len(dim_names)}。可参考符号公式：{score_formula}。
5) 依据 overall_grade 规则输出 overall_grade。

禁止：
- 不允许臆测看不清的内容；看不清=按问题处理，并写入 assumptions。
- 不允许“和稀泥”给高分；任何严重问题直接 Risky。

==============================
维度规则
{dim_text}

==============================
Overall Grade 判定规则（必须严格执行）：
- Excellent: {overall["excellent"]}
- Acceptable: {overall["acceptable"]}
- Risky: {overall["risky"]}

==============================
输出要求：只输出一个 JSON（不要 markdown / 不要多余解释）

{{
  "checklist_type": "{checklist_type}",
  "material_summary": "客观描述素材内容（<=100字）",
  "assumptions": "任何不确定/看不清/无法判断点；若无则空字符串",
  "dimensions": {{
    {dimension_schema}
  }},
  "overall_score": 0.0,
  "overall_grade": "Excellent/Acceptable/Risky",
  "rationale": "最大风险点 + 是否适合直接投放（1-2句）"
}}

【素材文本】{user_content}
""".strip()

def json_to_md(result: dict) -> str:
    result = normalize_result(result, result.get("checklist_type", CHECKLIST_TYPE))
    lines = []
    lines.append("# 品牌素材评估结果\n")
    lines.append("## 总体素材描述\n")
    lines.append(result.get("material_summary", "").strip() + "\n")

    lines.append("## 总体评分\n")
    lines.append(f"- **Checklist Type**: {result.get('checklist_type', '')}\n")
    lines.append(f"- **Overall Grade**: {result.get('overall_grade', '')}\n")
    lines.append(f"- **Overall Score**: {result.get('overall_score', '')}\n")
    lines.append(f"- **Rationale**: {result.get('rationale', '')}\n")
    lines.append(f"- **Assumptions**: {result.get('assumptions', '')}\n")

    lines.append("## 分维度评分\n")
    for dim, obj in result.get("dimensions", {}).items():
        lines.append(f"### {dim}\n")
        lines.append(f"- **Grade**: {obj.get('grade', '')}")
        lines.append(f"- **Score**: {obj.get('score', '')}")
        lines.append(f"- **Issue Tags**: {', '.join(obj.get('issue_tags', [])) or '无'}")
        lines.append(f"- **Other Tags**: {', '.join(obj.get('other_tags', [])) or '无'}")
        lines.append(f"- **Evidence**: {'; '.join(obj.get('evidence', [])) or '无'}")
        lines.append("")
    return "\n".join(lines).strip() + "\n"

def extract_first_json(text: str) -> dict:
    raw = (text or "").strip()
    if not raw:
        raise RuntimeError("❌ 模型没有返回文本（text_buf 为空）。")

    # 容错：截取第一个 JSON 对象
    if not (raw.startswith("{") and raw.endswith("}")):
        l = raw.find("{")
        r = raw.rfind("}")
        if l != -1 and r != -1 and r > l:
            raw = raw[l:r+1]

    return json.loads(raw)


# =========================
# 主流程
# =========================
def main():
    ensure_key()
    ensure_media()

    # 选择媒体 block（本地优先）
    if MEDIA_PATH:
        media_block = file_to_media_block(MEDIA_PATH)
    else:
        media_block = url_to_media_block(MEDIA_URL)

    client = OpenAI(api_key=DASHSCOPE_API_KEY, base_url=BASE_URL)

    prompt = build_prompt(CONTENT_TEXT, checklist_type=CHECKLIST_TYPE)      # ad, brand_kv
    print("===== PROMPT START =====")
    print(prompt)
    print("===== PROMPT END =====")

    messages = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                media_block, 
            ],
        }
    ]

    # 流式接收：文本 + 音频（base64）
    text_buf = ""
    audio_b64 = ""

    completion = client.chat.completions.create(
        model=MODEL_NAME,
        messages=messages,
        # modalities=["text", "audio"],
        # audio={"voice": "Cherry", "format": "wav"},
        stream=True,  # 官方要求必须 True :contentReference[oaicite:1]{index=1}
        stream_options={"include_usage": True},
    )

    for chunk in completion:
        if chunk.choices:
            delta = chunk.choices[0].delta

            # 文本
            if getattr(delta, "content", None):
                text_buf += delta.content

            # 音频 base64（兼容 dict）
            if hasattr(delta, "audio") and delta.audio:
                try:
                    audio_b64 += delta.audio.get("data", "")
                except Exception:
                    pass

    # 解析 JSON
    result = normalize_result(
        extract_first_json(text_buf),
        checklist_type=CHECKLIST_TYPE,
    )

    # 落盘 JSON + MD
    Path(OUT_JSON).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    # Path(OUT_MD).write_text(json_to_md(result), encoding="utf-8")

    # 保存 wav（按官方示例方式写）
    # if audio_b64:
    #     wav_bytes = base64.b64decode(audio_b64)
    #     audio_np = np.frombuffer(wav_bytes, dtype=np.int16)
    #     sf.write(OUT_WAV, audio_np, samplerate=24000)

    # print(f"✅ Saved: {OUT_JSON}, {OUT_MD}" + (f", {OUT_WAV}" if audio_b64 else ""))


if __name__ == "__main__":
    main()
