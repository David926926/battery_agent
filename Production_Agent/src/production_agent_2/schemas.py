from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator


Category = Literal["background", "layout", "object", "text"]
GenerationMode = Literal["image_to_background", "text_to_background"]
UseCase = Literal["main_detail", "media_ad"]
RealismLevel = Literal["realistic", "semi_realistic", "conceptual"]
VisualDensity = Literal["low", "medium", "high"]
BrandTone = Literal["reliable", "warm", "professional", "tech", "young"]


class RunRequest(BaseModel):
    workflow_type: str = "主图商详"
    generation_mode: GenerationMode = "image_to_background"
    brand: str = "南孚"
    platform: str = "电商平台"
    use_case: UseCase = "main_detail"
    audience: str = "电商消费者"
    scene: str = ""
    style: str = ""
    must_have: list[str] = Field(default_factory=list)
    must_avoid: list[str] = Field(default_factory=list)
    selling_points: list[str] = Field(default_factory=list)
    reserve_component_space: bool = True
    realism_level: RealismLevel = "realistic"
    brand_tone_priority: list[BrandTone] = Field(
        default_factory=lambda: ["reliable", "warm", "professional"]
    )
    visual_density: VisualDensity = "medium"
    preferred_text_model: str = "qwen-plus"
    preferred_image_generation_model: str = "qwen-image-2.0-pro"
    preferred_image_edit_model: str = "qwen-image-edit-max"
    aspect_ratio: str = "1:1"
    output_size: str = "1328*1328"
    direction_count: int = 3
    variants_per_direction: int = 2
    variants: int = 2
    background_prompt: str = ""
    dry_run: bool = False

    @model_validator(mode="after")
    def _sync_variant_fields(self) -> "RunRequest":
        directions = max(1, int(self.direction_count or 1))
        per_direction = int(self.variants_per_direction or 0)
        legacy_variants = int(self.variants or 0)
        if per_direction <= 0:
            per_direction = legacy_variants if legacy_variants > 0 else 1
        self.direction_count = directions
        self.variants_per_direction = per_direction
        self.variants = per_direction
        if not self.workflow_type:
            self.workflow_type = "主图商详" if self.use_case == "main_detail" else "媒介投放素材"
        return self


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


class TaskBrief(BaseModel):
    task_type: str = "background_generation"
    generation_mode: GenerationMode
    use_case: UseCase
    workflow_type: str
    audience: str
    scene: str
    style: str = ""
    must_have: list[str] = Field(default_factory=list)
    must_avoid: list[str] = Field(default_factory=list)
    selling_points: list[str] = Field(default_factory=list)
    reserve_component_space: bool = True
    realism_level: RealismLevel = "realistic"
    brand_tone_priority: list[BrandTone] = Field(default_factory=list)
    brand_tone: str = ""
    visual_density: VisualDensity = "medium"
    aspect_ratio: str
    output_size: str
    direction_count: int = 3
    variants_per_direction: int = 2
    source_summary: str = ""
    prompt_context: str = ""
    hard_constraints: list[str] = Field(default_factory=list)
    quality_constraints: list[str] = Field(default_factory=list)
    negative_constraints: list[str] = Field(default_factory=list)


class CreativeDirection(BaseModel):
    direction_id: str
    title: str
    summary: str
    visual_theme: str
    primary_palette: list[str] = Field(default_factory=list)
    scene_elements: list[str] = Field(default_factory=list)
    composition: str
    space_reservation: str
    fit_for_use_case: str
    risk_points: list[str] = Field(default_factory=list)
    recommendation_reason: str


class PromptPlan(BaseModel):
    direction_id: str
    direction_title: str
    model: str
    prompt: str
    negative_prompt: str
    reference_board_paths: list[str] = Field(default_factory=list)
    size: str
    variants: int
    preferred_model: str | None = None
    sections: dict[str, str] = Field(default_factory=dict)
    prompt_plan_path: str | None = None


class GeneratedImage(BaseModel):
    index: int
    direction_id: str
    direction_title: str
    variant_index: int
    seed: int
    resolved_model: str | None = None
    attempted_models: list[dict[str, object]] = Field(default_factory=list)
    prompt_plan_path: str | None = None
    path: str
    source_url: str | None = None


class RunState(BaseModel):
    run_id: str
    status: str = "pending"
    request: RunRequest
    assets: list[MaterialAsset] = Field(default_factory=list)
    reference_boards: list[ReferenceBoard] = Field(default_factory=list)
    task_brief: TaskBrief | None = None
    creative_directions: list[CreativeDirection] = Field(default_factory=list)
    prompt_plans: list[PromptPlan] = Field(default_factory=list)
    generated_images: list[GeneratedImage] = Field(default_factory=list)
    selected_image: str | None = None
    artifacts: dict[str, str] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    progress_callback: object | None = Field(default=None, exclude=True)
