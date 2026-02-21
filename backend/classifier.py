"""Gemini Vision: describe outfits and update descriptions from chat."""

import asyncio
import json

from google import genai
from google.genai import types
import httpx

from backend.config import GEMINI_API_KEY
from backend.models import ClassificationResult

_client = genai.Client(api_key=GEMINI_API_KEY)

CLASSIFY_PROMPT = """Analyze this clothing image. Return a JSON object with:
{
    "description": "detailed description of the full outfit including all visible garments, colors, and materials",
    "fit_notes": "fit and silhouette notes (e.g. oversized, slim, relaxed)",
    "colors": ["color1", "color2"],
    "style": "style category (e.g. streetwear, smart casual, formal)"
}
Only return valid JSON, no other text."""

UPDATE_PROMPT_TEMPLATE = """You are editing a clothing outfit description. Here is the CURRENT description (treat this as the source of truth):

{current_description}

The user wants ONE specific change: "{user_message}"

{new_image_context}

IMPORTANT RULES:
- ONLY change what the user explicitly asked to change
- Keep ALL other details EXACTLY as they are in the current description
- Do NOT add new details, embellishments, seams, stitching, or features that aren't in the current description
- Do NOT re-interpret or re-analyze the outfit — just apply the requested change
- If the user says "make the pants black", change ONLY the pants color to black. Everything else stays identical.

Return the updated JSON:
{{
    "description": "the current description with ONLY the requested change applied",
    "fit_notes": "keep existing fit notes, only update if the user's change affects fit",
    "colors": ["updated", "color", "list"],
    "style": "style category"
}}
Only return valid JSON, no other text."""


def _extract_json(text: str) -> dict:
    """Strip markdown code fences if present, then parse JSON."""
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1].rsplit("```", 1)[0]
    return json.loads(text)


async def classify_image(image_url: str) -> ClassificationResult:
    """Classify a Pinterest image and extract outfit description."""
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(image_url)
            resp.raise_for_status()
            image_bytes = resp.content

        image_part = types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg")

        response = await asyncio.to_thread(
            _client.models.generate_content,
            model="gemini-2.5-flash",
            contents=[CLASSIFY_PROMPT, image_part],
        )
        parsed = _extract_json(response.text)
        return ClassificationResult(**parsed)
    except Exception as e:
        raise RuntimeError(f"Classification failed: {e}") from e


async def update_description(
    current_description: str,
    user_message: str,
    new_image_url: str | None = None,
) -> ClassificationResult:
    """Update outfit description based on user's chat message."""
    try:
        new_image_context = ""
        parts: list = []

        if new_image_url:
            async with httpx.AsyncClient() as client:
                resp = await client.get(new_image_url)
                resp.raise_for_status()
                image_bytes = resp.content
            new_image_context = (
                "The user also provided a new garment image (attached). "
                "Incorporate this item into the outfit description."
            )
            parts.append(types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg"))

        prompt = UPDATE_PROMPT_TEMPLATE.format(
            current_description=current_description,
            user_message=user_message,
            new_image_context=new_image_context,
        )
        parts.insert(0, prompt)

        response = await asyncio.to_thread(
            _client.models.generate_content,
            model="gemini-2.5-flash",
            contents=parts,
        )
        parsed = _extract_json(response.text)
        return ClassificationResult(**parsed)
    except Exception as e:
        raise RuntimeError(f"Description update failed: {e}") from e
