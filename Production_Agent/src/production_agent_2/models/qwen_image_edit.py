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

    def retouch(self, image_path: str, instruction: str, output_path: str) -> dict[str, str]:
        client = DashScopeClient()
        if not client.enabled:
            return {"mode": "offline_stub", "model": self.model_name, "path": image_path}

        payload = {
            "model": self.model_name,
            "input": {
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"image": encode_image_as_data_url(image_path)},
                            {"text": instruction},
                        ],
                    }
                ]
            },
            "parameters": {
                "watermark": False,
                "n": 1,
                "negative_prompt": (
                    "replace product, change packaging, rewrite text, unreadable text, blur, duplicate objects, "
                    "broken battery, wrong brand, wrong layout, extra props, collage look"
                ),
            },
        }
        response_json = client.post_multimodal_generation(payload)
        image_urls = extract_image_urls(response_json)
        if not image_urls:
            return {"mode": "dashscope", "model": self.model_name, "path": image_path}
        Path(output_path).write_bytes(download_binary(image_urls[0]))
        return {"mode": "dashscope", "model": self.model_name, "path": output_path, "source_url": image_urls[0]}
