from __future__ import annotations

from pathlib import Path

from production_agent_2.models.dashscope import (
    DashScopeClient,
    download_binary,
    encode_image_as_data_url,
    extract_image_urls,
)
from production_agent_2.models.model_routing import get_default_model, run_with_model_fallback


class QwenImageClient:
    model_name = get_default_model("image_generation")

    def is_enabled(self) -> bool:
        return DashScopeClient().enabled

    def generate(
        self,
        reference_images: list[str],
        prompt: str,
        negative_prompt: str,
        size: str,
        variants: int,
        base_seed: int,
        output_dir: str,
        filename_prefix: str = "candidate",
        preferred_model: str | None = None,
    ) -> list[dict[str, str]]:
        client = DashScopeClient()
        if not client.enabled:
            return []

        content = [{"image": encode_image_as_data_url(path)} for path in reference_images[:3]]
        content.append({"text": prompt})
        results: list[dict[str, str]] = []
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        total_variants = max(1, min(variants, 8))
        for idx in range(total_variants):
            seed = base_seed + idx
            def _call(model_name: str) -> dict[str, object]:
                payload = {
                    "model": model_name,
                    "input": {"messages": [{"role": "user", "content": content}]},
                    "parameters": {
                        "n": 1,
                        "seed": seed,
                        "watermark": False,
                        "prompt_extend": True,
                        "size": size,
                        "negative_prompt": negative_prompt,
                    },
                }
                return client.post_multimodal_generation(payload)

            response_json, resolved_model, attempts = run_with_model_fallback(
                family="image_generation",
                preferred_model=preferred_model or self.model_name,
                call=_call,
            )
            image_urls = extract_image_urls(response_json)
            if not image_urls:
                continue
            output_path = Path(output_dir) / f"{filename_prefix}_{idx + 1}_seed_{seed}.png"
            output_path.write_bytes(download_binary(image_urls[0]))
            results.append(
                {
                    "index": str(idx + 1),
                    "seed": str(seed),
                    "model": resolved_model,
                    "attempted_models": attempts,
                    "path": str(output_path),
                    "source_url": image_urls[0],
                }
            )
        return results
