"""Identify foods in a photo with Claude vision."""
from __future__ import annotations

import base64
import io

from pydantic import BaseModel, Field

MAX_EDGE = 1568  # longest side Claude uses at full detail; larger only costs more
MEDIA_TYPES = {
    b"\xff\xd8\xff": "image/jpeg",
    b"\x89PNG\r\n\x1a\n": "image/png",
    b"GIF87a": "image/gif",
    b"GIF89a": "image/gif",
}

PROMPT = """You are the food recognition step of a calorie tracker.
List every distinct food or drink visible in the photo.

For each one give:
- name: a short, common, lowercase name, preferring one of these known names when it fits: {known}
- quantity: how many standard servings are visible (e.g. 2 for two rotis, 0.5 for half a plate of rice)
- calories_per_serving: your best estimate for one standard serving
- tip: one short, friendly nutrition tip

If the photo contains no food, return an empty list."""


class DetectedFood(BaseModel):
    name: str
    quantity: float = Field(gt=0)
    calories_per_serving: int = Field(ge=0)
    tip: str


class Detection(BaseModel):
    foods: list[DetectedFood]


class VisionError(Exception):
    """A user-facing problem with photo recognition."""


def sniff_media_type(data: bytes) -> str | None:
    for magic, media in MEDIA_TYPES.items():
        if data.startswith(magic):
            return media
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    return None


def _shrink(data: bytes, media_type: str) -> tuple[bytes, str]:
    """Downscale big photos with Pillow when it is installed."""
    try:
        from PIL import Image
    except ImportError:
        return data, media_type
    try:
        img = Image.open(io.BytesIO(data))
    except Exception as e:
        raise VisionError("That file doesn't look like a valid image.") from e
    if max(img.size) <= MAX_EDGE:
        return data, media_type
    img.thumbnail((MAX_EDGE, MAX_EDGE))
    out = io.BytesIO()
    img.convert("RGB").save(out, format="JPEG", quality=88)
    return out.getvalue(), "image/jpeg"


def identify_foods(data: bytes, *, api_key: str, model: str, known_foods: list[str]) -> list[DetectedFood]:
    if not api_key:
        raise VisionError("Photo recognition is off: set ANTHROPIC_API_KEY to enable it.")
    media_type = sniff_media_type(data)
    if not media_type:
        raise VisionError("Upload a JPEG, PNG, GIF or WebP image.")
    data, media_type = _shrink(data, media_type)

    import anthropic

    client = anthropic.Anthropic(api_key=api_key, timeout=60.0)
    try:
        response = client.beta.messages.parse(
            model=model,
            max_tokens=4096,
            output_config={"effort": "low"},
            # On a safety decline, let the API retry on a suitable fallback model.
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
            output_format=Detection,
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": base64.standard_b64encode(data).decode("ascii"),
                        },
                    },
                    {"type": "text", "text": PROMPT.format(known=", ".join(known_foods))},
                ],
            }],
        )
    except anthropic.AuthenticationError as e:
        raise VisionError("The Anthropic API key was rejected.") from e
    except anthropic.RateLimitError as e:
        raise VisionError("Too many photo requests right now; try again in a minute.") from e
    except anthropic.BadRequestError as e:
        raise VisionError(f"The image could not be processed: {e.message}") from e
    except anthropic.APIStatusError as e:
        raise VisionError(f"Photo recognition failed ({e.status_code}); try again later.") from e
    except anthropic.APIConnectionError as e:
        raise VisionError("Could not reach the recognition service; check your connection.") from e

    if response.stop_reason == "refusal":
        raise VisionError("This photo could not be analyzed.")
    if response.parsed_output is None:
        raise VisionError("Could not read the recognition result; try another photo.")
    return response.parsed_output.foods
