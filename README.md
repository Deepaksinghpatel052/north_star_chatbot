# North Star Support Bot

A customer support chatbot for a fictional outdoor apparel & camping gear
e-commerce brand, built for the Upwork Talent Accelerator: AI Chatbot
Developer program.

## Live Demo

The chatbot is hosted and ready to test — no setup, no API keys, no
accounts required. Just open the link and start chatting:

**Live URL:** _https://north-star-chatbot.onrender.com_

> **Note:** The demo is hosted on a free tier that sleeps after inactivity,
> so the very first visit may take ~30 seconds to wake up. After that it
> responds instantly.

If you prefer to run it locally instead, see **Run Locally** below.

## Run Locally (optional — no API keys needed)

**1. Create and activate a virtual environment** (recommended, keeps
dependencies isolated from your system Python):

```bash
python -m venv venv

# macOS / Linux
source venv/bin/activate

# Windows
venv\Scripts\activate
```

**2. Install runtime dependencies:**

```bash
pip install -r requirements.txt
```

**3. Run the server:**

```bash
uvicorn main:app --reload
```

Then open **http://127.0.0.1:8000** in your browser. That's it — no API keys,
no `.env` file, no accounts. Everything runs locally and fully offline
(no external API calls are made anywhere in the app).

> **Note on `.env`:** This project doesn't use a `.env` file because there
> are no secrets or environment-specific config to store — no API keys,
> no database credentials. All business data (order statuses, policies,
> shipping info) is intentionally kept in `data.py`, matching the brief
> exactly.

## Tech Stack

- **Backend**: FastAPI (Python)
- **Intent Recognition**: TF-IDF vectorization + cosine similarity (scikit-learn),
  combining a word-level and a character n-gram model for typo tolerance
- **Frontend**: Single-file HTML/CSS/JS chat widget (no build step, no framework)
- **State**: In-memory session store (no database needed for this simulated project)

No LLM API (OpenAI/Claude/etc.) is used. This is intentional: the brief requires
responses to be **100% accurate to the exact provided data** (order statuses,
return policy, shipping times) and to be **fully testable without any API key**.
A local TF-IDF-based intent classifier delivers genuine NLP-based
phrasing-variation handling while keeping every response deterministic and
reviewable with zero setup.

## Project Structure

```
north_star_chatbot/
├── main.py                 # FastAPI app, /chat and /welcome endpoints, serves the UI
├── conversation.py          # Conversation state machine (all 4 use case flows)
├── intent_classifier.py     # TF-IDF intent recognition (variations + typo tolerance)
├── data.py                   # Business data ONLY (exact order statuses, policies, shipping)
├── static/index.html        # Chat UI
├── requirements.txt          # Runtime dependencies (used for hosting/running the app)
├── requirements-dev.txt      # Extra dependencies for running the test suites
├── test_chatbot.py           # Pytest test suite (44 tests, no server needed)
└── test_flows.py             # HTTP-based test script (runs against a live server)
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
   by a fallback scenario. Transitions to a simulated "Live Agent" state;
   the user can type `menu` anytime to return to the bot.

**Intent recognition** handles phrasing variations (e.g. "Where is my
order?" vs "Track my package") and common typos (e.g. "trak my packeg") via
a combined word-level + character n-gram TF-IDF similarity model — see
`intent_classifier.py`.

**Fallback handling**: unrecognized input triggers a clear "I didn't
understand" message with menu options and an escalation hint, rather than
guessing or breaking the flow.

## Running the Tests

The project ships with a **pytest suite of 50 tests** covering every
required use case plus a wide range of edge cases. The test suites need a
couple of extra libraries listed in `requirements-dev.txt`:

```bash
pip install -r requirements-dev.txt
```

**Option A — Pytest suite (recommended, no server needed):**

```bash
pytest            # compact "dots" report
pytest -v         # verbose: shows each test name + PASS/FAIL + percentage
```

Sample output:

```
collected 50 items

test_chatbot.py ..................................................  [100%]

============================== 50 passed in 1.3s ==============================
```

Each dot is one passing test. The suite runs directly against the
conversation engine (no server required).

**Option B — HTTP flow script (runs against a live server):**

```bash
# In one terminal, start the server:
uvicorn main:app

# In another terminal, run:
python test_flows.py
```

### What the tests cover (50 tests)

| Area | Tests | Examples |
|------|-------|----------|
| **Order Tracking** | 6 | asks for order number; #111/#222/#333 exact statuses; invalid order; looking up a second order without re-typing the request |
| **Returns & Exchanges** | 2 | exact policy text (30-day / unused / original packaging); returns link |
| **Product Recommendation** | 8 | both clarifying questions; full flow; cold-weather upgrade; "no preference" answers; re-ask on unclear input; escaping the flow after repeated unclear input; recovery after one bad answer |
| **Human Handoff** | 3 | explicit request; return to menu after handoff; escalate from a fallback |
| **Intent Recognition** | 11 | phrasing variations for order tracking & returns; typo tolerance ("packeg", "trak", "retrn", "recomend") |
| **Fallback Handling** | 9 | gibberish input; structurally-similar-but-unrelated input ("where is tajmahal", "what time is it"); fallback offers options |
| **Shipping Info** | 1 | standard 3-5 / expedited 1-2 business days |
| **Delivered-order Follow-up** | 7 | "all good" answers close cheerfully; reported problems hand off to an agent |
| **Edge Cases** | 3 | empty message; `menu` reset; uppercase input |

Because each test maps to a specific brief requirement, the passing report
doubles as a requirements-coverage checklist.

## Deployment (Render)

This app is deployed on Render as a free web service. To reproduce:

1. Push the project to a GitHub repository.
2. On Render, create a **New Web Service** and connect the repo.
3. Use these settings:
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn main:app --host 0.0.0.0 --port $PORT`
   - **Instance Type:** Free
4. Deploy. Render provides a public URL that anyone can open and test with
   zero setup.

## Submission Checklist Mapping

- [x] All four required use cases implemented
- [x] Order tracking follows the provided mock data exactly (111/222/333/invalid)
- [x] Return policy and shipping information included where required
- [x] Intent recognition supports multiple phrasings (and common typos)
- [x] Fallback handling implemented ("I didn't understand" + options)
- [x] Users can return to main menu after human handoff (type `menu`)
- [x] Reviewable without API keys, accounts, or extra steps (hosted link, or one-command local run)
- [x] Fully testable — 44-test pytest suite included