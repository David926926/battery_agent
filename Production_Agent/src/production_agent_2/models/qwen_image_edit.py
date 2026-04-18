from __future__ import annotations

from pathlib import Path

from production_agent_2.models.dashscope import (
    DashScopeClient,
    download_binary,
    encode_image_as_data_url,
    extract_image_urls,
)
from production_agent_2.models.model_routing import get_default_model, run_with_model_fallback


class QwenImageEditClient:
    model_name = get_default_model("image_edit")

    def is_enabled(self) -> bool:
        return DashScopeClient().enabled

    def retouch(
        self,
        image_path: str,
        instruction: str,
        output_path: str,
        negative_prompt: str | None = None,
        reference_images: list[str] | None = None,
        preferred_model: str | None = None,
    ) -> dict[str, str]:
        client = DashScopeClient()
        if not client.enabled:
            return {"mode": "offline_stub", "model": self.model_name, "path": image_path}

        content = [{"image": encode_image_as_data_url(image_path)}]
        for ref_path in reference_images or []:
            content.append({"image": encode_image_as_data_url(ref_path)})
        content.append({"text": instruction})

        def _call(model_name: str) -> dict[str, object]:
            payload = {
                "model": model_name,
                "input": {
                    "messages": [
                        {
                            "role": "user",
                            "content": content,
                        }
                    ]
                },
                "parameters": {
                    "watermark": False,
                    "n": 1,
                    "negative_prompt": negative_prompt
                    or (
                        "text, logo, product, battery, human, face, hand, body, packaging, chinese characters, letters, "
                        "numbers, symbols, watermark, button, label, signage, unreadable text, garbled text, promo banner, "
                        "badge, extra props, object outline, subject silhouette, foreground residue, duplicate object, "
                        "collage board, low quality"
                    ),
                },
            }
            return client.post_multimodal_generation(payload)

        response_json, resolved_model, attempts = run_with_model_fallback(
            family="image_edit",
            preferred_model=preferred_model or self.model_name,
            call=_call,
        )
        image_urls = extract_image_urls(response_json)
        if not image_urls:
            return {"mode": "dashscope", "model": resolved_model, "path": image_path, "attempted_models": attempts}
        Path(output_path).write_bytes(download_binary(image_urls[0]))
        return {
            "mode": "dashscope",
            "model": resolved_model,
            "attempted_models": attempts,
            "path": output_path,
            "source_url": image_urls[0],
        }
