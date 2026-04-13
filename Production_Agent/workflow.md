# Production Agent 2.0 Workflow

## 简介
Production Agent 2.0 是一个基于 LangGraph 的“背景优先”生成流程：用一张**成品主图/海报**作风格参考，生成不含文字与主体的电商背景底图，并输出后续摆放建议；`Production_Agent/sources` 下的组件素材会汇总进 `placement_plan.json`。

系统的核心目标有两个：

1. 自动生成背景候选图
2. 输出后续摆放建议（占位框）用于后期合成

当前主模型：
- `qwen-image-2.0-pro`

---

## 输入素材

- **前端/运行目录**：将用户上传的成品参考图放入 `materials/Background/`（内部仍用 `background` 类别扫描），拼成参考板后送入模型。
- **仓库组件库**：读取 `Production_Agent/sources` 下除 `Background` / `Layout` / `Object` / `Text` 外的子目录（如电池体、电商彩盒等），写入 `placement_plan.json` 的 `component_library`。

---

## Workflow

### 1. 素材读取
扫描 `Background` 素材，生成统一素材清单。

输出：
- `asset_manifest.json`

### 2. 参考板生成
将上传的成品参考图整理为 1 张拼板：

- `style_board.png`
  （由成品参考图拼成；无文件名字幕）

输出：
- `style_board.png`

### 3. 创意规划
根据任务目标和素材生成：

- creative brief
- prompt plan

输出：
- `creative_brief.json`
- `prompt_plan.json`

### 4. Qwen 背景生成
将背景参考板和 prompt 一起输入 Qwen，生成背景候选图。

输出：
- `candidate_*.png`

### 5. 摆放建议输出
系统基于选中的背景候选图，输出后期合成建议：

- `artifacts/placement_plan.json`
- `artifacts/placement_preview.png`

### 6. 最终状态保存
保存整次运行的最终状态：

- `final_state.json`

---

## Flowchart

```mermaid
flowchart TD
    A[读取 Background 素材]
    B[生成素材清单<br/>asset_manifest.json]
    C[生成参考板<br/>style_board.png（仅背景）]
    D[生成创意规划<br/>creative_brief + prompt_plan]
    E[调用 Qwen 生成背景候选图<br/>candidate_*.png]
    F[输出摆放建议<br/>placement_plan / placement_preview]
    G[保存最终状态<br/>final_state.json]

    A --> B
    B --> C
    C --> D
    D --> E
    E --> F
    F --> G
