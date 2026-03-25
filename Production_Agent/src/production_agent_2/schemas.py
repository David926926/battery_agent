from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


Category = Literal["background", "layout", "object", "text"]


class RunRequest(BaseModel):
    workflow_type: str = "主图商详"
    brand: str = "南孚"
    audience: str = "电商消费者"
    platform: str = "电商平台"
    aspect_ratio: str = "1:1"
    output_size: str = "1328*1328"
    variants: int = 5
    seed: int = 42
    primary_copy: str = "南孚电池"
    secondary_copy: str = "持久电力 稳定输出"
    selling_points: list[str] = Field(
        default_factory=lambda: ["聚能环科技"]
    )
    dry_run: bool = False


class MaterialAsset(BaseModel):
    asset_id: str
    category: Category
    path: str
    filename: str
    width: int
    height: int
    mode: str


class ReferenceBoard(BaseModel):
    board_id: str
    category: str
    source_asset_ids: list[str] = Field(default_factory=list)
    path: str
    note: str


class CreativeBrief(BaseModel):
    product_focus: str
    visual_tone: list[str] = Field(default_factory=list)
    composition_rules: list[str] = Field(default_factory=list)
    text_rules: list[str] = Field(default_factory=list)
    must_include: list[str] = Field(default_factory=list)
    avoid: list[str] = Field(default_factory=list)


class PromptPlan(BaseModel):
    model: str
    prompt: str
    negative_prompt: str
    reference_board_paths: list[str] = Field(default_factory=list)
    size: str
    variants: int
    base_seed: int


class GeneratedImage(BaseModel):
    index: int
    path: str
    source_url: str | None = None


class RunState(BaseModel):
    run_id: str
    status: str = "pending"
    request: RunRequest
    assets: list[MaterialAsset] = Field(default_factory=list)
    reference_boards: list[ReferenceBoard] = Field(default_factory=list)
    brief: CreativeBrief | None = None
    prompt_plan: PromptPlan | None = None
    generated_images: list[GeneratedImage] = Field(default_factory=list)
    selected_image: str | None = None
    artifacts: dict[str, str] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
