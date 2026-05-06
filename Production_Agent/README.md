# Production_Agent_2.0

这是南孚图片生产 Agent 的“工作一 / 模式一：稳妥生产模式”实现。当前主链路由 Streamlit interface 编排，将 Production Agent 的背景生成能力、Evaluation Agent 的 checklist 审核能力、Edit Loop、组件成图和最终输出连成一个可操作闭环。

当前支持：

- 背景生成/提取：支持“图片提取背景”和“文字生成背景”。
- 自动评估：背景图生成后、Edit 后、组件成图后都会自动调用 Evaluation Agent。
- 背景 Edit：用户选择候选图作为 Base，填写需要修改/保持不变的内容，生成新候选。
- 组件成图：用户上传电池、包装、Logo、卖点文案、人物等组件，生成最终商业图。
- 二次评估：组件成图后重点检查品牌元素、文字、遮挡、商业可用性等问题。
- 最终输出：支持 PNG 原图、JPG 压缩版、生产记录 JSON，并可继续使用 HD Redraw 高清化。

暂未完整支持：

- PSD 分层输出。
- 完整南孚组件素材库选择页。
- 模式二“创意实验模式”。
- 模式三“本土化 + 翻译”。

命令行仍可直接运行底层背景生成流程；完整模式一闭环请使用 `interface/app.py`。

## 安装

```bash
cd Production_Agent_2.0
pip install -e .
```

## 运行

先做离线检查：

```bash
python -m production_agent_2.cli --dry-run
```

正式出图前配置：

```bash
export DASHSCOPE_API_KEY=your_key
```

默认调用 Qwen 生成背景候选图（需要配置 `DASHSCOPE_API_KEY`）：

```bash
python -m production_agent_2.cli \
  --primary-copy "南孚电池" \
  --secondary-copy "持久电力 稳定输出" \
  --selling-points "聚能环科技,高效续航,电商爆款视觉"
```

说明：当前版本不再提供 `--enable-ai-polish` 相关逻辑，直接生成背景底图并输出摆放建议。

运行结果会写到：

```text
Production_Agent_2.0/runs/<run_id>/
```

其中重点产物包括：

- `artifacts/asset_manifest.json`
- `artifacts/reference_boards.json`
- `artifacts/prompt_plan.json`
- `artifacts/generation_result.json`
- `artifacts/placement_plan.json`
- `artifacts/placement_preview.png`
- `state/final_state.json`

## 当前模型

当前默认使用：

- 背景生成：`qwen-image-2.0-pro`
- 图片编辑/背景提取/组件成图：`qwen-image-edit-max`
- 自动评估：`qwen3-omni-flash`

若首选模型限流或繁忙，interface 会按模型族配置自动降级。
