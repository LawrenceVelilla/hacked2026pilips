"""Quick test: call IDM-VTON on Replicate with local images."""

import asyncio
from backend.tryon import run_tryon

# Local file paths
SAMPLE_HUMAN_IMG = "photos/IMG_2759-2.png"
SAMPLE_GARMENT_IMG = "test_images/chaining/04060233800-e1.jpg"


async def main():
    print("Running IDM-VTON test...")
    print(f"Human image:  {SAMPLE_HUMAN_IMG}")
    print(f"Garment image: {SAMPLE_GARMENT_IMG}")
    print()

    try:
        result_url = await run_tryon(
            human_img_url=SAMPLE_HUMAN_IMG,
            garm_img_url=SAMPLE_GARMENT_IMG,
            category="lower_body",
        )
        print(f"Success --> Result: {result_url}")
    except RuntimeError as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    asyncio.run(main())
