from __future__ import annotations

from pathlib import Path

from production_agent_2.models.dashscope import (
    DashScopeClient,
    download_binary,
    encode_image_as_data_url,
    extract_image_urls,
)


class QwenImageClient:
    model_name = "qwen-image-2.0-pro"

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
            payload = {
                "model": self.model_name,
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
            response_json = client.post_multimodal_generation(payload)
            image_urls = extract_image_urls(response_json)
            if not image_urls:
                continue
            output_path = Path(output_dir) / f"candidate_{idx + 1}_seed_{seed}.png"
            output_path.write_bytes(download_binary(image_urls[0]))
            results.append(
                {
                    "index": str(idx + 1),
                    "seed": str(seed),
                    "path": str(output_path),
                    "source_url": image_urls[0],
                }
            )
        return results
