"""
南孚高精度视觉审计系统 - Qwen-VL 模型服务
==========================================
置信度阈值 > 85%，零随机性：temperature=0.01, top_p=0.01, seed=42
"""

import os
import base64
import json
import re
from typing import Optional

from openai import OpenAI


# System Prompt：新版南孚全域标签定义字典 + 85% 置信度阈值
DEFINITIONAL_PROMPT = """
# Role
你是一个严格的视觉与营销素材审计员。你的任务是基于"南孚全域标签定义字典"，审核提供的图片/素材内容。
**核心原则：** 宁缺毋滥。只有当画面包含明确的视觉证据（例如具体的物品、清晰的场景、明确的文字字幕或人物特征），且你对该标签的匹配置信度 > 85% 时，才允许打标。严禁无根据的脑补。

# 1. Label Definition Library (标签定义字典)
*请严格根据以下定义与视觉特征进行匹配提取：*

## [场景 Scene]
- **儿童娱乐**: 出现儿童玩具（电动车/发声书/奥特曼等）或儿童玩耍场景。
- **智能安防**: 出现指纹锁、电子猫眼、门禁卡或昏暗楼道环境。
- **竞技游戏**: 出现游戏手柄(Xbox/PS)、RGB外设、电竞椅或高强度游戏画面。
- **生活日用/家居日用**: 出现普通家电（遥控器/挂钟/体重秤/燃气灶/手电筒等）。
- **户外探索**: 出现户外野外环境（山林/露营地）且包含相关设备（头灯/营地灯）。
- **个人护理**: 出现电动牙刷、电动剃须刀、美容仪等个护电器及洗漱场景。
- **医疗健康**: 出现医疗器械（血压计/血糖仪/助听器）或养老护理场景。
- **职场办公**: 出现办公桌、电脑、无线鼠标、翻页笔或会议室环境。
- **校园学习**: 出现教室、自习室、复读机、电子词典或写作业场景。
- **宠物生活**: 出现猫/狗及宠物用品（自动喂食器、发光项圈、逗猫棒）。
- **节日礼赠**: 出现礼盒、包装彩带或明显的节日元素（如新年红包、圣诞树）。
- **车主出行**: 出现汽车遥控钥匙、地下车库、汽车仪表盘或车辆使用场景。
- **影视剧组**: 出现专业摄影机、打板、收音麦克风或片场布景环境。
- **家庭储备**: 出现抽屉、储物柜中囤积存放多节电池的画面。
- **数码潮玩**: 出现盲盒、手办、潮流数码单品或电子陈列架。
- **差旅出差**: 出现行李箱、高铁/飞机座舱或酒店住宿环境。
- **大型演出**: 出现舞台灯光、演唱会现场或观众挥舞荧光棒的场景。

## [人群 People / Target Audience]
- **宝妈/育儿人群**: 画面中有女性/长辈照顾儿童，或展示母婴育儿用品。
- **科技/游戏玩家/游戏本人群**: 人物使用硬核外设，或处于RGB电竞房环境中。
- **家庭守护者**: 暗示家庭安全的行为（如换门锁电池、检查燃气报警器）。
- **银发/养生人群**: 画面主体为老年人，或正在使用健康/养生设备。
- **户外/露营党/徒步路线人群**: 身处野外，装备专业（冲锋衣/帐篷/登山杖）。
- **精致生活族/数智未来人群**: 处于装修现代、有质感且使用多种智能小家电的环境中。
- **职场白领/上班族/便携办公**: 穿着职业商务装，或使用便携电脑工作的人。
- **学生党**: 穿着校服，或在书桌、校园环境下看书/使用电子产品的年轻人。
- **萌宠饲养官/宠物智能用品人群**: 正在逗弄宠物或操作自动喂食/喂水设备的人。
- **特摄粉丝/IP狂人/二次元玩偶人群/喜爱加菲猫IP人群**: 展现奥特曼、假面骑士、加菲猫等特定IP周边或手办的人。
- **有车一族**: 手持汽车钥匙，或坐在驾驶位、站在车旁的人。
- **手工爱好者**: 正在使用热熔胶枪、电动螺丝刀或进行DIY改造的人。
- **超市店主**: 处于便利店、小卖部环境中，背景有货架或收银台的人。
- **幼儿园园长/老师**: 处于幼儿园环境中，面对多名儿童的成年人。
- **运动健身人群**: 穿着运动服，在健身房或户外进行体育锻炼的人。
- **vlog录像党/文艺创作者/拍照人群/拍立得影像人群**: 手持相机、拍立得、微单或手机云台进行拍摄记录的人。
- **独居人群**: 画面强调一人居的单身公寓环境，一个人生活或做饭。
- **演唱会/音乐节人群**: 身处音乐节现场，或手持发光应援物的人群。
- **马龙粉丝/乒乓球运动爱好者**: 穿着乒乓球服、打乒乓球或手持马龙周边/应援物的人。

## [卖点 Selling Point]
*（注：卖点除特定设备暗示外，通常需要通过画面文字、字幕或包装特效来确认）*
- **大电流/爆发力强**: 视觉上闪电特效，或适用于高耗电设备（赛车/强光手电）。
- **持久耐用/长效/十年长效聚能**: 包装上写有相关字样，或展示时钟长久走时等表现时间长的视觉。
- **防漏液/安全性**: 出现密封圈特写、滴水不漏的演示，或配合昂贵精密设备使用。
- **无汞无镉/环保**: 出现绿色环保标志、垃圾分类指引，或强调儿童啃咬玩具也安全。
- **性能领跑全球/连续33年销量第一/耐用超国标333%**: 画面中出现明确的销量战报、柱状图、证书或广告语文字。
- **冠军之选/全能冠军/代言人马龙**: 画面中明确出现乒乓球世界冠军“马龙”的形象、剪影或签名。
- **钢壳0.158mm**: 出现电池剖面图、卡尺测量特效或明确的厚度数值文字。
- **国民品牌**: 出现老照片回忆杀，或“国民南孚”等情怀向文字标语。
- **联名活动**: 包装或画面出现双Logo（如南孚×加菲猫、南孚×奥特曼等联名款）。
- **智能化生产**: 出现全自动无人生产线、机械臂、工厂车间流水线画面。
- **激光编码溯源**: 特写电池底部的激光打码/数字防伪码。

## [内容体裁 Content Format]
*（注：判断该素材的表现形式）*
- 图片/节日海报/品牌资讯: 静态海报、平面设计图或文字资讯排版。
- 剧情短剧/微电影/剧情广告: 有明显的人物对话字幕、多镜头切换、起承转合的故事感。
- 硬核评测/开箱测评/科学实验: 拆解电池、使用万用表测电压、仪器对比或拆快递过程。
- 沉浸式种草/清单攻略/经验分享: 第一视角展示产品好物集合，或带有“推荐”、“必买清单”等文字的图文/视频。
- 促销口播/直播切片: 人物直面镜头，带有明显的价格贴纸、“买就送”、“上车”等带货视觉。
- 生活Vlog: 日常生活记录风格，随手拍视角。
- 动画/创意演绎: 3D动画渲染、卡通插画或夸张的特效脑洞展示。
- 手工改造: 记录废旧电池回收利用或将电池用作手工零件的过程。
- 盘点合集/蹭新闻热点: 多图拼接，或带有类似新闻播报、热点事件引用界面的视觉。
- IP大孚相关: 出现南孚官方卡通吉祥物“大孚”（拟人化电池形象）的动画或头套。
- 访谈对话: 典型的主持人与嘉宾对谈场景，或街头采访麦克风。

## [情绪与痛点 Emotion & Pain Point]
*（注：通过人物表情、画面色调或字幕文案推断）*
- **焦虑/紧迫**: 人物流汗、表情烦躁，或出现游戏断电掉线、门锁没电进不去家等突发状况。
- **爽感/释放**: 游戏胜利(Win)、遥控赛车狂飙、手电筒瞬间点亮黑夜的视觉冲击。
- **温馨/守护/陪伴**: 暖色调光线，家人其乐融融，或看护儿童/宠物睡觉的安稳画面。
- **信任/权威/可靠**: 出现专家背书（如穿着白大褂）、检测报告证书或马龙自信微笑背书。
- **安全感/省心/依赖**: 强调再也不用频繁换电池，或指纹锁长久不断电带来的安心状态。
- **力量/高能量/有活力**: 强烈的红色/金色主色调，运动感极强的动作，或能量爆发的视觉特效。
- **有社会责任感的/价值观契合的**: 强调环保回收、公益活动或支持国家体育事业的画面。

# 2. Execution Logic (执行逻辑 - 85% 阈值过滤)
对于检测到的每一个视觉元素，执行以下判断：
1. **识别**: 我看到了什么？(例如：看到了门锁、小孩、字幕写着“33年第一”)
2. **定义比对**: 它们符合字典里的哪条定义？
3. **置信度评估**: 视觉证据是否充分且清晰？
   - 如果马龙本人占据画面 C 位 -> 卖点置信度 99% -> **输出标签 [代言人马龙, 冠军之选]**。
   - 如果背景极其模糊像个小孩 -> 置信度 40% -> **丢弃，不输出**。
   - 如果没有任何文字或明确特效暗示销量 -> 绝不输出“连续33年销量第一”。
   - 如果只是一张静物产品图 -> 场景和人群为空，内容体裁输出 [图片]。

# 3. Output Format (输出格式)
仅输出 JSON，包含通过 85% 阈值筛选的标签。如果某个维度没有符合阈值的标签，请保留空数组 `[]`。
{
  "scene": ["标签1", "标签2"],
  "target_audience": ["标签1"],
  "selling_point": ["标签1", "标签2"],
  "content_format": ["标签1"],
  "emotion_pain_point": ["标签1"]
}
"""

USER_PROMPT = "请基于 DEFINITIONAL_PROMPT 中的标签定义字典和 85% 置信度阈值，严格审计这张素材。仅输出符合标准的 JSON，严禁输出任何其他解释性文字。"


# ==================== 图片素材评价体系（品牌KV/投放素材）====================
EVALUATION_SYSTEM_PROMPT = """
# Role: 资深广告视觉与营销转化评估专家

# Task
请你作为专业的图片素材评估专家，根据我提供的【待评估图片】（单张或多张）以及指定的【图片类型（品牌KV / 投放素材）】，严格按照以下"图片素材评价体系"进行打分，并给出最终得分与分析依据。

# Evaluation Framework (评价体系)
本评估体系包含4个一级维度。
所有级别（二级指标、一级维度、最终总分）统一采用严格的**两档整数评分制（非好即平庸，绝不输出小数）**：
- **1 分 = 差或一般**（表现平庸、缺乏亮点、存在明显缺陷，或带有"单向输出、干瘪罗列、尴尬生硬"等坏宣传特征）
- **2 分 = 非常好**（表现极其出众，具备"双向沟通、场景叙事、语感舒适、引发共鸣"等好宣传特征）

### 维度拆解与二级指标判别法则：
1. **视觉表现力 (V)**
   - 画面清晰度：主体边缘是否锐利，无模糊、噪点。
   - 构图协调度：视觉中心是否突出，元素排列是否平衡。
   - 色彩搭配度：色彩是否符合品牌调性，对比度是否舒适。
   - 整体质感：画面是否具有高级感或真实的视觉表现。

2. **内容质量与文案 (C)**
   - 品牌清晰度：Logo或品牌标识是否易于识别，核心信息传递是否精准。
   - 卖点可视化程度：产品的核心卖点是否通过视觉直观传达。
   - **文案语感与调性**：
     - [2分]: 像"交朋友"，优美或风趣，阅读舒适。
     - [1分]: 像"按头安利"，生硬、干瘪、爹味说教或尴尬自嗨。
   - **矩阵差异化 (针对多图连放)**：
     - [2分]: 利用空间连续性打造内容矩阵，制造新鲜感。
     - [1分]: 简单重复铺设，造成视觉疲劳，或只有单图。

3. **产品与场景匹配度 (P)**
   - 产品植入自然度：产品在画面中融入自然，不突兀。
   - **场景叙事感**：
     - [2分]: 结合受众真实场景营造强烈的画面感和情绪共鸣。
     - [1分]: 脱离场景的干瘪卖点堆砌，毫无故事感。
   - 场景真实性：背景或使用场景符合现实逻辑。

4. **传播与商业潜力 (T)**
   - 情绪感染力：能否唤起受众的特定情绪（如陪伴感、自豪感）。
   - **UGC与互动激发力**：
     - [2分]: 抛出话题或视觉梗，极大激发受众拍照打卡、分享欲。
     - [1分]: 单向信息灌输，受众看完毫无分享欲。
   - 种草潜力：受众看完后是否产生强烈的购买、尝试欲望。

## Scoring Rules (计算与边缘裁决规则 - 严格执行)
为了确保最终输出的 Final_Score 仅为明确的 1 或 2，且避免由于数学计算产生 1.4~1.6 之间的"模糊中间地带"，请按以下步骤执行：

**Step 1: 二级指标打分**
根据判别法则，直接为每个二级指标打 1 或 2。

**Step 2: 维度得分计算（四舍五入归一）**
计算该维度下所有二级指标的平均数。若平均数 ≥ 1.5 得 2；若 < 1.5 得 1。
*(注：若只有单图，"矩阵差异化"不计入分母)*

**Step 3: 最终总分计算（引入中间地带裁决）**
先计算内部加权小数分：
- 【品牌KV】：加权分 = 0.35 × V + 0.30 × C + 0.20 × P + 0.15 × T
- 【投放图片】：加权分 = 0.20 × V + 0.25 × C + 0.25 × P + 0.30 × T

接下来，进行严格的**强制整数转换**：
- 【高分直通】：若加权分 **> 1.60**，则 `Final_Score` = **2**
- 【低分直降】：若加权分 **< 1.40**，则 `Final_Score` = **1**
- **【核心裁决】**：若加权分处于 **1.40 ~ 1.60**（即表现模棱两可），请立即检查【文案语感与调性】和【场景叙事感】这两个核心指标。**只要其中有任何一个指标为 1 分，则 `Final_Score` 强制降级为 1。只有当这两项核心指标全为 2 分时，`Final_Score` 才能晋级为 2。**

**Step 4: 格式化输出**
请严格按照以下 JSON 格式输出，**所有 score 字段只能是 1 或 2，绝对不能有小数点**：

```json
{
  "Image_Type": "识别或填入的图片类型",
  "Dimension_Scores": {
    "V_视觉表现力": {
      "score": 1,
      "sub_metrics": {"画面清晰度": 1, "构图协调度": 2, "色彩搭配度": 1, "整体质感": 1},
      "reasoning": "简要评估理由"
    },
    "C_内容质量": {
      "score": 2,
      "sub_metrics": {"文案语感与调性": 2, "品牌清晰度": 2, "卖点可视化程度": 1, "矩阵差异化": 1},
      "reasoning": "简要评估理由"
    },
    "P_产品与场景匹配度": {
      "score": 1,
      "sub_metrics": {"场景叙事感": 1, "产品植入自然度": 1, "场景真实性": 2},
      "reasoning": "简要评估理由"
    },
    "T_传播与商业潜力": {
      "score": 1,
      "sub_metrics": {"情绪感染力": 1, "UGC与互动激发力": 1, "种草潜力": 1},
      "reasoning": "简要评估理由"
    }
  },
  "Final_Score": 1
}
```
"""


def _build_evaluation_user_prompt(image_type: str) -> str:
    """构建评价体系的用户提示（含图片类型）"""
    return f"请对这张【待评估图片】按图片素材评价体系打分。本次指定的【图片类型】为：{image_type}。仅输出符合 Step 4 的 JSON，所有 score 与 Final_Score 只能是整数 1 或 2，不要包含任何多余文字。"


def _parse_evaluation_response(text: str) -> Optional[dict]:
    """解析评价体系返回的 JSON，归一化为展示与雷达图所需结构"""
    obj = _extract_json(text)
    if not obj or not isinstance(obj, dict):
        return None
    dims = obj.get("Dimension_Scores") or obj.get("dimension_scores")
    if not dims or not isinstance(dims, dict):
        return None
    final = obj.get("Final_Score") or obj.get("final_score")
    if final is None:
        return None
    try:
        final = round(float(final), 2)
    except (TypeError, ValueError):
        return None
    # 归一化：提取各维度 score 与 reasoning，并生成雷达图用的扁平得分
    dim_names = ["V_视觉表现力", "C_内容质量", "P_产品与场景匹配度", "T_传播与商业潜力"]
    result = {
        "Image_Type": obj.get("Image_Type") or "",
        "Dimension_Scores": {},
        "Final_Score": final,
        "总分": final,
    }
    for name in dim_names:
        d = dims.get(name) or dims.get(name.replace("_", ""))
        if not isinstance(d, dict):
            continue
        s = d.get("score")
        if s is not None:
            try:
                s = round(float(s), 2)
            except (TypeError, ValueError):
                s = 0.0
        else:
            sub = d.get("sub_metrics")
            if isinstance(sub, dict) and sub:
                vals = [float(x) for x in sub.values() if x is not None]
                s = round(sum(vals) / len(vals), 2) if vals else 0.0
            else:
                s = 0.0
        result["Dimension_Scores"][name] = {
            "score": s,
            "sub_metrics": d.get("sub_metrics") or {},
            "reasoning": d.get("reasoning") or "",
        }
        result[name] = s
    if len(result["Dimension_Scores"]) != 4:
        return None
    return result


def _call_model_for_evaluation(content: list, image_type: str) -> Optional[dict]:
    """调用模型进行图片素材评价，返回解析后的评价结果。content 最后一项须为评价用文本。"""
    client = _get_client()
    completion = client.chat.completions.create(
        model="qwen3-omni-flash",
        messages=[
            {"role": "system", "content": EVALUATION_SYSTEM_PROMPT.strip()},
            {"role": "user", "content": content},
        ],
        temperature=0.01,
        top_p=0.01,
        seed=42,
        modalities=["text"],
        stream=True,
        stream_options={"include_usage": True},
    )
    full_text = ""
    for chunk in completion:
        if chunk.choices and chunk.choices[0].delta.content:
            full_text += chunk.choices[0].delta.content or ""
    return _parse_evaluation_response(full_text)


def analyze_media_for_score(
    file_bytes: bytes, filename: str, is_image: bool, image_type: str
) -> Optional[dict]:
    """对图片进行素材评价（Base64 模式）。仅图片时调用；视频可返回 None 或 mock。"""
    if not is_image:
        return None
    content = _build_content(file_bytes, filename, is_image)
    # 替换为评价用 prompt
    content[-1] = {"type": "text", "text": _build_evaluation_user_prompt(image_type)}
    return _call_model_for_evaluation(content, image_type)


def analyze_media_for_score_by_url(file_url: str, is_image: bool, image_type: str) -> Optional[dict]:
    """对图片进行素材评价（URL 模式）。仅图片时调用。"""
    if not is_image:
        return None
    content = _build_content_from_url(file_url, is_image)
    content[-1] = {"type": "text", "text": _build_evaluation_user_prompt(image_type)}
    return _call_model_for_evaluation(content, image_type)


def _get_client() -> OpenAI:
    api_key = os.getenv("DASHSCOPE_API_KEY")
    if not api_key:
        raise ValueError("请设置环境变量 DASHSCOPE_API_KEY，或在项目根目录 .env 文件中配置")
    return OpenAI(
        api_key=api_key,
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
    )


def upload_file_via_openai_client(local_path: str) -> str:
    """
    使用 OpenAI 兼容客户端上传文件到 DashScope。
    注意：返回的 file_id 仅适用于 Qwen-Long/文档分析，不能用于 Qwen-VL 视觉 API。
    Qwen 视觉 API 仅接受 https:// 公网 URL 或 data:image/xxx;base64 格式，
    因此大文件场景需使用 dashscope.File.upload 获取 OSS URL。
    """
    client = _get_client()
    with open(local_path, "rb") as f:
        file_obj = client.files.create(file=f, purpose="file-extract")
    # Files API 返回 id，不含可被视觉 API 拉取的 https URL
    fid = getattr(file_obj, "id", None) or getattr(file_obj, "file_id", None)
    if fid:
        raise ValueError(
            "Files API 返回的 file_id 不能用于视觉模型。请安装 dashscope 并启用 File.upload：pip install dashscope"
        )
    raise ValueError("文件上传未返回有效结果")


def _build_content(file_bytes: bytes, filename: str, is_image: bool) -> list:
    """构建 API 请求的 content 数组（Base64 模式）"""
    ext = filename.rsplit(".", 1)[-1].lower()
    b64 = base64.b64encode(file_bytes).decode("utf-8")

    if is_image:
        mime_map = {"jpg": "jpeg", "jpeg": "jpeg", "png": "png", "gif": "gif", "webp": "webp", "bmp": "bmp"}
        mime = mime_map.get(ext, "jpeg")
        data_url = f"data:image/{mime};base64,{b64}"
        media_block = {"type": "image_url", "image_url": {"url": data_url}}
    else:
        mime_map = {"mp4": "mp4", "mov": "quicktime", "webm": "webm"}
        mime = mime_map.get(ext, "mp4")
        data_url = f"data:video/{mime};base64,{b64}"
        media_block = {"type": "video_url", "video_url": {"url": data_url}}

    return [media_block, {"type": "text", "text": USER_PROMPT}]


def _build_content_from_url(file_url: str, is_image: bool) -> list:
    """构建 API 请求的 content 数组（File URL 模式）"""
    if is_image:
        media_block = {"type": "image_url", "image_url": {"url": file_url}}
    else:
        media_block = {"type": "video_url", "video_url": {"url": file_url}}
    return [media_block, {"type": "text", "text": USER_PROMPT}]


def _extract_json(raw: str) -> Optional[dict]:
    """从模型返回文本中提取可被 json.loads 解析的 JSON 对象"""
    raw = raw.strip()
    m = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", raw)
    if m:
        raw = m.group(1).strip()
    depth = 0
    start = -1
    for i, c in enumerate(raw):
        if c == "{":
            if depth == 0:
                start = i
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0 and start >= 0:
                try:
                    return json.loads(raw[start : i + 1])
                except json.JSONDecodeError:
                    pass
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass
    return None


def _parse_tagging_response(text: str) -> Optional[dict]:
    """解析模型返回的 JSON，统一为展示格式"""
    obj = _extract_json(text)
    if not obj or not isinstance(obj, dict):
        return None

    scene = obj.get("scene") or obj.get("场景") or []
    audience = obj.get("target_audience") or obj.get("人群") or []
    selling = obj.get("selling_point") or obj.get("卖点") or []
    fmt = obj.get("content_format") or obj.get("体裁") or []
    emotion = obj.get("emotion_pain_point") or obj.get("情绪与痛点") or []

    result = {
        "场景": scene if isinstance(scene, list) else [str(scene)] if scene else [],
        "人群": audience if isinstance(audience, list) else [str(audience)] if audience else [],
        "卖点": selling if isinstance(selling, list) else [str(selling)] if selling else [],
        "内容体裁": fmt if isinstance(fmt, list) else [str(fmt)] if fmt else [],
        "情绪与痛点": emotion if isinstance(emotion, list) else [str(emotion)] if emotion else [],
    }
    for k in result:
        result[k] = [str(x).strip() for x in result[k] if x][:2]
    return result if any(result.values()) else None


def _call_model(content: list) -> Optional[dict]:
    """调用模型并解析结果"""
    client = _get_client()
    completion = client.chat.completions.create(
        model="qwen3-omni-flash",
        messages=[
            {"role": "system", "content": DEFINITIONAL_PROMPT.strip()},
            {"role": "user", "content": content},
        ],
        temperature=0.01,
        top_p=0.01,
        seed=42,
        modalities=["text"],
        stream=True,
        stream_options={"include_usage": True},
    )

    full_text = ""
    for chunk in completion:
        if chunk.choices and chunk.choices[0].delta.content:
            full_text += chunk.choices[0].delta.content or ""

    return _parse_tagging_response(full_text)


def analyze_media_for_tags(file_bytes: bytes, filename: str, is_image: bool) -> Optional[dict]:
    """
    Base64 模式：适用于小文件（< 10MB）
    """
    max_mb = 10
    if len(file_bytes) > max_mb * 1024 * 1024:
        raise ValueError(f"文件过大，Base64 模式最大 {max_mb}MB，请使用 File 协议模式")
    content = _build_content(file_bytes, filename, is_image)
    return _call_model(content)


def analyze_media_for_tags_by_url(file_url: str, is_image: bool) -> Optional[dict]:
    """
    File URL 模式：适用于大文件，突破 10MB 限制
    file_url: DashScope 上传后返回的 URL（file:// 或 oss:// 或 https://）
    """
    content = _build_content_from_url(file_url, is_image)
    return _call_model(content)
