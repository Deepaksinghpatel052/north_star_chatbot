# North Star Support Bot

A customer support chatbot for a fictional outdoor apparel & camping gear
e-commerce brand, built for the Upwork Talent Accelerator: AI Chatbot
Developer program.

## Live Demo

No setup needed to review — this app runs fully locally with zero external
dependencies (no API keys, no accounts). See **Quick Start** below; it takes
under a minute.

## Quick Start (local — no API keys needed)

**1. Create and activate a virtual environment** (recommended, keeps
dependencies isolated from your system Python):

```bash
python3 -m venv venv

# macOS / Linux
source venv/bin/activate

# Windows
venv\Scripts\activate
```

**2. Install dependencies:**

```bash
pip install -r requirements.txt
```

**3. Run the server:**

```bash
uvicorn main:app --reload
```

Then open **http://127.0.0.1:8000** in your browser. That's it — no API keys,
no `.env` file, no accounts, no additional setup. Everything runs locally and
fully offline (no external API calls are made at all).

> **Note on `.env`:** This project doesn't use a `.env` file because there
> are no secrets or environment-specific config to store — no API keys,
> no database credentials. All business data (order statuses, policies,
> shipping info) is intentionally kept in `data.py`, matching the brief
> exactly, with no external service calls anywhere in the app.

## Tech Stack

- **Backend**: FastAPI (Python)
- **Intent Recognition**: TF-IDF vectorization + cosine similarity (scikit-learn)
- **Frontend**: Single-file HTML/CSS/JS chat widget (no build step, no framework)
- **State**: In-memory session store (no database — this is a simulated project, not deployed)

No LLM API (OpenAI/Claude/etc.) is used. This is intentional: the brief requires
responses to be **100% accurate to the exact provided data** (order statuses,
return policy, shipping times) and to be **fully testable without any API key**.
A local TF-IDF-based intent classifier achieves genuine NLP-based phrasing-variation
handling while keeping every response deterministic and evaluator-testable with zero setup.

## Project Structure

```
north_star_chatbot/
├── main.py               # FastAPI app, /chat and /welcome endpoints, serves the UI
├── conversation.py        # Conversation state machine (all 4 use case flows)
├── intent_classifier.py   # TF-IDF intent recognition (handles phrasing variations)
├── data.py                 # Business data ONLY (exact order statuses, policies, shipping)
├── static/index.html      # Chat UI
├── requirements.txt
└── test_flows.py           # Automated test script covering all use cases
```

`data.py` intentionally contains **only** the business facts given in the
project brief, verbatim. `intent_classifier.py` contains phrase *patterns*
used purely as matching logic (like an advanced set of if/else rules) — not
business content, and not a source of any customer-facing claim.

## Use Cases Implemented

1. **Order Tracking** — asks for order number, returns exact mock status
   (111 → Shipped, 222 → Processing, 333 → Delivered + follow-up, anything
   else → invalid order).
2. **Returns & Exchanges** — states the 30-day / unused / original-packaging
   policy and a returns link.
3. **Product Recommendation** — asks 2 clarifying questions (activity type,
   then weather conditions) and recommends a product category.
4. **Human Handoff** — triggered by explicit request ("talk to a human") or
   by fallback (unrecognized input after being offered escalation).
   Transitions to a simulated "Live Agent" state; user can type `menu`
   anytime to return to the bot.

**Intent recognition** handles phrasing variations (e.g. "Where is my
order?" vs "Track my package") via TF-IDF + cosine similarity across a
bank of example phrases per intent — see `intent_classifier.py`.

**Fallback handling**: unrecognized input triggers a clear "I didn't
understand" message with menu options and an escalation hint, rather than
guessing or breaking the flow.

## Running the Tests

```bash
pip install requests --break-system-packages   # if not already installed
python3 test_flows.py
```

This exercises all 4 use cases, 2+ phrasing variations for order tracking,
all 4 mock order codes (111/222/333/invalid), the delivered-order follow-up,
fallback handling, and human handoff + return-to-menu.

## Submission Checklist Mapping

- [x] All four required use cases implemented
- [x] Order tracking follows the provided mock data exactly (111/222/333/invalid)
- [x] Return policy and shipping information included where required
- [x] Intent recognition supports multiple phrasings (TF-IDF similarity matching)
- [x] Fallback handling implemented ("I didn't understand" + options)
- [x] Users can return to main menu after human handoff (type `menu`)
- [x] Reviewable without API keys, accounts, or extra setup — `pip install` + `uvicorn` only
- [x] No external services/deployment required (runs fully locally, no network calls)
