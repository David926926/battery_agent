# Production Agent 2.0 Workflow

## 简介
Production Agent 2.0 是一个基于 LangGraph 的“主图商详”生成流程，用于把 `Background / Layout / Object / Text` 四类素材组织成电商主图商详。

系统的核心目标有两个：

1. 自动生成主图商详候选图
2. 额外导出便于后期人工微调的辅助图层资产

当前主模型：
- `qwen-image-2.0-pro`

---

## 输入素材
系统读取 `resources` / `sources` 下的四类素材：

- `Background`
  背景氛围参考
- `Layout`
  排版结构参考
- `Object`
  产品主体、包装、人物等素材
- `Text`
  标题、标签、文字风格素材

---

## Workflow

### 1. 素材读取
扫描四类素材，生成统一素材清单。

输出：
- `asset_manifest.json`

### 2. 参考板生成
将原始素材整理成三张参考板：

- `style_board`
  Layout + Background
- `object_board`
  Object 素材
- `text_board`
  Text 素材

输出：
- `style_board.png`
- `object_board.png`
- `text_board.png`

### 3. 创意规划
根据任务目标和素材生成：

- creative brief
- prompt plan

输出：
- `creative_brief.json`
- `prompt_plan.json`

### 4. Qwen 主图生成
将三张参考板和 prompt 一起输入 Qwen，生成主图商详候选图。

输出：
- `candidate_*.png`

### 5. 辅助图层导出
系统额外导出一组便于人工调整的辅助图层：

- `background_base.png`
- `layout_hint.png`
- `object_cluster.png`
- `text_cluster.png`
- `final_preview.png`
- `layout_plan.json`

### 6. 背景与特效反解
系统会进一步尝试从最终生成图中近似提取：

- `background_clean_*.png`
- `effects_overlay_black_*.png`

说明：
这一步是后期辅助用途的近似分层，不是严格真实图层恢复。

### 7. 最终状态保存
保存整次运行的最终状态：

- `final_state.json`

---

## Flowchart

```mermaid
flowchart TD
    A[读取四类素材<br/>Background / Layout / Object / Text]
    B[生成素材清单<br/>asset_manifest.json]
    C[生成参考板<br/>style_board / object_board / text_board]
    D[生成创意规划<br/>creative_brief + prompt_plan]
    E[调用 Qwen 生成主图商详候选图<br/>candidate_*.png]
    F[导出辅助图层<br/>background_base / layout_hint / object_cluster / text_cluster / final_preview]
    G[反解背景层<br/>background_clean_*.png]
    H[反解特效层<br/>effects_overlay_black_*.png]
    I[保存最终状态<br/>final_state.json]

    A --> B
    B --> C
    C --> D
    D --> E
    E --> F
    F --> G
    G --> H
    H --> I
