# Production_Agent_2.0

这是一个重新实现的总控生产 Agent，用 LangGraph 编排“背景优先”生成流程，并直接消费 `Production_Agent_2.0` 下的素材目录。

素材分两类：

- **成品风格参考**：放在 `resources/Background` 或 `sources/Background`（至少一张成品主图/海报，用于生成纯背景）。
- **后期组件素材库**：`sources` 下除 `Background` / `Layout` / `Object` / `Text` 外的子目录（如电池体、电商彩盒等），会在 `placement_plan.json` 的 `component_library` 中列出路径。

流程分为 4 步：

1. 扫描 `Background` 中的成品参考图并生成 `asset_manifest.json`
2. 将参考图整合为拼板并生成 `creative_brief` 与 `prompt_plan`
3. 调用 Qwen 仅生成背景候选图（`candidate_*.png`）
4. 输出 `placement_plan.json`（含组件库索引）+ `placement_preview.png`，并写出最终状态

命令行直接跑时，请确保 `sources/Background`（或 `resources/Background`）里至少有一张成品参考图；否则请用 Streamlit 界面上传。

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

当前默认使用 `qwen-image-2.0-pro`。本项目通过先合成 Background 参考板的方式把背景语义纳入模型上下文，只生成背景底图并输出摆放建议。
