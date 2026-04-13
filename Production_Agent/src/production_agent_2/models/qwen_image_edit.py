from __future__ import annotations

from pathlib import Path

from production_agent_2.models.dashscope import (
    DashScopeClient,
    download_binary,
    encode_image_as_data_url,
    extract_image_urls,
)


class QwenImageEditClient:
    model_name = "qwen-image-edit-max"

    def is_enabled(self) -> bool:
        return DashScopeClient().enabled

    def retouch(
        self,
        image_path: str,
        instruction: str,
        output_path: str,
        negative_prompt: str | None = None,
        reference_images: list[str] | None = None,
    ) -> dict[str, str]:
        client = DashScopeClient()
        if not client.enabled:
            return {"mode": "offline_stub", "model": self.model_name, "path": image_path}

        content = [{"image": encode_image_as_data_url(image_path)}]
        for ref_path in reference_images or []:
            content.append({"image": encode_image_as_data_url(ref_path)})
        content.append({"text": instruction})

        payload = {
            "model": self.model_name,
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
        response_json = client.post_multimodal_generation(payload)
        image_urls = extract_image_urls(response_json)
        if not image_urls:
            return {"mode": "dashscope", "model": self.model_name, "path": image_path}
        Path(output_path).write_bytes(download_binary(image_urls[0]))
        return {"mode": "dashscope", "model": self.model_name, "path": output_path, "source_url": image_urls[0]}
