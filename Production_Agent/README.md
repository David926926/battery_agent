# Production_Agent_2.0

这是一个重新实现的总控生产 Agent，用 LangGraph 编排主图商详生成流程，并直接消费 `Production_Agent_2.0` 下的素材目录。

当前支持两种目录布局：

- `resources/Background`、`resources/Layout`、`resources/Object`、`resources/Text`
- `sources/Background`、`sources/Layout`、`sources/Object`、`sources/Text`

流程分为 5 步：

1. 扫描四类素材并生成 `asset_manifest.json`
2. 将全部素材整合为最多 3 张参考板，适配 `qwen-image-2.0-pro` 的多图输入限制
3. 先把背景、布局、主体、文字素材强制合成为一张底稿
4. 产出创意 brief 与精修 prompt
5. 调用 Qwen 对底稿做精修，而不是自由发挥重画
6. 写出运行产物与最终状态

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

默认只输出确定性的素材合成结果，不调用 AI 精修：

```bash
python -m production_agent_2.cli \
  --primary-copy "南孚电池" \
  --secondary-copy "持久电力 稳定输出" \
  --selling-points "聚能环科技,高效续航,电商爆款视觉"
```

如果你要试验性地让 Qwen 对底稿做二次精修，再显式开启：

```bash
python -m production_agent_2.cli \
  --primary-copy "南孚电池" \
  --secondary-copy "持久电力 稳定输出" \
  --selling-points "聚能环科技,高效续航,电商爆款视觉" \
  --enable-ai-polish
```

运行结果会写到：

```text
Production_Agent_2.0/runs/<run_id>/
```

其中重点产物包括：

- `artifacts/asset_manifest.json`
- `artifacts/reference_boards.json`
- `artifacts/prompt_plan.json`
- `artifacts/generation_result.json`
- `state/final_state.json`

## 当前模型

当前默认使用 `qwen-image-2.0-pro`。这是阿里云 Model Studio 文档里当前推荐的 Qwen 高质量图像生成/编辑模型；本项目通过先合成参考板的方式，把四类素材全部纳入模型上下文。
