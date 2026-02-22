# Fitted

**See it on them. See it on you. Buy it.**

Fitted is a Chrome extension that lets you virtually try on clothes while browsing Pinterest. See an outfit you like, click "Try on", and see yourself wearing it in seconds.

## Why Fitted?

Online shopping is broken. You see clothes on models who don't look like you, in lighting that doesn't reflect reality, and in sizes that don't match your body. The result? Endless returns, wasted money, and frustration.

Fitted closes the gap between browsing and buying by putting **you** in the outfit.

### Accessibility First

Fitting rooms aren't for everyone:

- **Physical disabilities & chronic illness** — For wheelchair users, people with limited mobility, or those with chronic pain, physically trying on clothes is exhausting or impossible. Fitted brings the fitting room to you.
- **Neurodivergent & sensory needs** — Fitting rooms are overwhelming — bright lights, cramped spaces, time pressure. Fitted lets you try on from a calm, familiar space.
- **Social anxiety & agoraphobia** — For those who struggle with in-store experiences, Fitted removes the social barrier entirely.
- **Body representation** — Most product photos show a narrow range of body types. Fitted shows you clothes on *your* body, not a model's. Every body deserves to see how an outfit actually looks on them.
- **Geographic & economic barriers** — Not everyone lives near clothing stores. Not everyone can afford to buy, try, and return. Fitted reduces that friction.

## How It Works

```
1. Upload a full-body reference photo (one-time setup)
2. Browse Pinterest normally
3. Hover over any clothing image → click "Try on"
4. See yourself wearing it in the side panel (~12 seconds)
5. Chat to modify: "make it blue", "add a jacket over this", "try different pants"
```

## Architecture

```
Chrome Extension (Side Panel + Content Script on Pinterest)
    ↕ HTTP (localhost:8000)
FastAPI Backend
    ├── Gemini 2.5 Flash — describes the outfit from the image
    ├── FLUX.2 Pro — generates you wearing the outfit
    └── rembg — removes background for clean output
```

### The Pipeline

1. **Classify** — Gemini Vision analyzes the Pinterest image and generates a detailed outfit description (colors, fit, style)
2. **Generate** — FLUX.2 Pro takes your reference photo + the outfit image + the description and generates a photorealistic image of you in that outfit
3. **Post-process** — Background removal produces a clean, transparent result
4. **Chat** — Modify the outfit through natural language. Each message updates the description and regenerates, preserving your session context

### Layering

Fitted supports iterative outfit building:
- Start with a base outfit
- Add a jacket on top
- Swap the pants
- Change colors

Each modification builds on the previous result, like a dress-up game powered by generative AI.

## Tech Stack

| Component          | Technology               |
|--------------------|--------------------------|
| Backend            | FastAPI + uvicorn        |
| Outfit Description | Gemini 2.5 Flash         |
| Try-On Generation  | FLUX.2 Pro via Replicate |
| Background Removal | rembg (u2net)            |
| Image Processing   | Pillow                   |
| HTTP Client        | httpx (async)            |
| Frontend           | Chrome Extension MV3 (Side Panel), vanilla JS |

## Setup

### Prerequisites
- Python 3.11+
- Chrome browser
- API keys: [Replicate](https://replicate.com), [Google AI](https://ai.google.dev)

### Backend
```bash
# Clone and install
git clone <repo-url>
cd fitted
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Add your REPLICATE_API_TOKEN and GOOGLE_API_KEY

# Run
uvicorn backend.main:app --reload
```

### Chrome Extension
1. Open `chrome://extensions/`
2. Enable "Developer mode"
3. Click "Load unpacked" → select the `extension/` folder
4. Browse Pinterest and click the Fitted icon to open the side panel

## Cost

| Step | Cost | Speed |
|------|------|-------|
| Gemini classification | ~$0.00 | ~2 sec |
| FLUX.2 Pro generation | ~$0.08 | ~9 sec |
| Background removal | $0.00 (local) | ~1-2 sec |
| **Total per try-on** | **~$0.08** | **~12 sec** |

## Future Roadmap

- **User accounts & database** — Persistent profiles, saved try-on history, photo management and caching.
- **Cloud deployment** — Hosted backend with cloud ML model serving.
- **Model fine-tuning** — Custom models trained on diverse body types for better representation
- **Expanded body forms** — Dedicated support for paraplegic users, prosthetics, seated poses, and other body forms that are underrepresented in fashion tech
- **More platforms** — Extend beyond Pinterest to ASOS, Zara, H&M, and other clothing sites
- **Shoe try-on** — Lower body and footwear virtual try-on
- **Buy links** — Scrape Pinterest product tags and surface purchase links alongside try-on results
- **Lighter deployment** — Switch from u2net (172MB) to u2netp (~4MB) for faster installs

## Notes
- The more layers to try to change, the more likely the facial integrity degrades. This is due to the fact that the model, with a security constraint of 5, will change a little bit of face each time. Lowering this constraint will likely improve the facial integrity, but will compromise some of the details of the outfit.
- Note that everytime you press the try on button, it will store 12 outfits in the queue which you can scroll through but after you pick a new one, and want to see the old outfit, you'd have to regenerate it. This is because there is no caching yet.

## Team

- Jordan Antonio - Frontend and Popup Design and Wiring
- Lawrence Velilla - Backend wiring and AI Agents

Built at HackED 2026.
