import requests

BASE = "http://127.0.0.1:8000"


def chat(session_id, message):
    r = requests.post(f"{BASE}/chat", json={"session_id": session_id, "message": message})
    r.raise_for_status()
    return r.json()


def new_chat(message):
    return chat(None, message)


def section(title):
    print(f"\n{'=' * 60}\n{title}\n{'=' * 60}")


# --- 1. Order Tracking: two phrasing variations ---
section("1a. Order Tracking - 'Where is my order?' -> 111")
r = new_chat("Where is my order?")
print("Bot:", r["reply"])
r = chat(r["session_id"], "111")
print("Bot:", r["reply"])
assert "Shipped, arriving tomorrow" in r["reply"], "FAIL: order 111 text mismatch"

section("1b. Order Tracking - 'Track my package' (variation) -> 222")
r = new_chat("Track my package")
print("Bot:", r["reply"])
r = chat(r["session_id"], "222")
print("Bot:", r["reply"])
assert "Processing, ships in 24 hours" in r["reply"], "FAIL: order 222 text mismatch"

section("1c. Order 333 -> Delivered + follow-up, then 'no'")
r = new_chat("what's the status of my order")
sid = r["session_id"]
r = chat(sid, "333")
print("Bot:", r["reply"])
assert "Delivered" in r["reply"] and "good shape" in r["reply"], "FAIL: 333 follow-up missing"
r = chat(sid, "no, all good")
print("Bot:", r["reply"])

section("1d. Invalid order number -> 999")
r = new_chat("order tracking")
r = chat(r["session_id"], "999")
print("Bot:", r["reply"])
assert "couldn't find that order" in r["reply"], "FAIL: invalid order handling"

# --- 2. Returns & Exchanges ---
section("2. Returns & Exchanges")
r = new_chat("how do I return an item")
print("Bot:", r["reply"])
assert "30-day returns" in r["reply"] and "unused" in r["reply"] and "original packaging" in r["reply"].lower()
assert "returns" in r["reply"].lower()  # link mention

# --- 3. Product Recommendation ---
section("3. Product Recommendation (2 clarifying questions)")
r = new_chat("can you recommend a product")
print("Bot:", r["reply"])
sid = r["session_id"]
r = chat(sid, "hiking")
print("Bot:", r["reply"])
r = chat(sid, "mostly cold weather")
print("Bot:", r["reply"])
assert "Cold Weather" in r["reply"], "FAIL: recommendation category mismatch"

# --- 4. Human Handoff (explicit) ---
section("4a. Human Handoff - explicit request")
r = new_chat("I want to talk to a human")
print("Bot:", r["reply"])
assert "Live Agent" in r["reply"]
sid = r["session_id"]
r = chat(sid, "menu")
print("Bot (after 'menu'):", r["reply"][:60], "...")
assert "How can I help" in r["reply"] or "help with" in r["reply"], "FAIL: return to menu after handoff"

# --- 4b. Human Handoff via fallback ---
section("4b. Fallback -> then escalate to human")
r = new_chat("asdkjfh randomgibberish 12345")
print("Bot:", r["reply"])
assert "didn't quite catch" in r["reply"], "FAIL: fallback message missing"
sid = r["session_id"]
r = chat(sid, "human")
print("Bot:", r["reply"])
assert "Live Agent" in r["reply"], "FAIL: fallback -> human handoff"

# --- 5. Shipping info bonus check ---
section("5. Shipping info")
r = new_chat("how long does shipping take")
print("Bot:", r["reply"])
assert "3-5 business days" in r["reply"] and "1-2 business days" in r["reply"]

# --- 6. Regression tests for reported bugs ---
section("6a. Regression: bare order number right after a resolved order (no re-prompt)")
r = new_chat("Track my order")
sid = r["session_id"]
r = chat(sid, "222")
print("Bot:", r["reply"])
r = chat(sid, "111")  # bare number, no "track order" phrase this time
print("Bot:", r["reply"])
assert "Shipped, arriving tomorrow" in r["reply"], "FAIL: bare number after a resolved order should still be treated as a new order lookup"

section("6b. Regression: switching intent while awaiting an order number")
r = new_chat("Track my order")
sid = r["session_id"]
r = chat(sid, "112")  # invalid order number
print("Bot:", r["reply"])
assert "couldn't find that order" in r["reply"]
r = chat(sid, "I want to track my order")  # user retries with a full sentence, no digits
print("Bot:", r["reply"])
assert "What's your order number" in r["reply"], "FAIL: should re-prompt for order number, not repeat 'not found'"
r = chat(sid, "111")
print("Bot:", r["reply"])
assert "Shipped, arriving tomorrow" in r["reply"]

section("6c. Regression: asking about returns while awaiting an order number")
r = new_chat("Track my order")
sid = r["session_id"]
r = chat(sid, "What is returns policy?")  # switch topic instead of giving a number
print("Bot:", r["reply"])
assert "30-day returns" in r["reply"], "FAIL: should switch to returns flow, not report order not found"

section("6d. Regression: unrelated text with common words should NOT match an intent")
r = new_chat("here is tajmahal")
print("Bot:", r["reply"])
assert "didn't quite catch" in r["reply"], "FAIL: unrelated text falsely matched a real intent"

r = new_chat("tell me a joke")
print("Bot:", r["reply"])
assert "didn't quite catch" in r["reply"], "FAIL: unrelated text falsely matched a real intent"

section("6e. Regression: gibberish at recommendation activity question (should re-ask)")
r = new_chat("can you recommend a product")
sid = r["session_id"]
r = chat(sid, "Tajmahal")
print("Bot:", r["reply"])
assert "didn't quite catch" in r["reply"], "FAIL: gibberish activity answer was silently accepted"
r = chat(sid, "hiking")  # recover with a real answer
print("Bot:", r["reply"])
assert "One more thing" in r["reply"]

section("6f. Regression: gibberish at recommendation weather question (should re-ask)")
r = new_chat("can you recommend a product")
sid = r["session_id"]
chat(sid, "camping")
r = chat(sid, "purple elephant")
print("Bot:", r["reply"])
assert "didn't quite catch" in r["reply"], "FAIL: gibberish weather answer was silently accepted"
r = chat(sid, "mixed conditions")
print("Bot:", r["reply"])
assert "Camping collection" in r["reply"]

section("6g. Regression: switching intent mid-recommendation (activity step)")
r = new_chat("can you recommend a product")
sid = r["session_id"]
r = chat(sid, "what is your return policy")
print("Bot:", r["reply"])
assert "30-day returns" in r["reply"], "FAIL: should switch to returns flow, not treat as activity answer"

section("6h. Regression: switching intent mid-recommendation (weather step)")
r = new_chat("can you recommend a product")
sid = r["session_id"]
chat(sid, "hiking")
r = chat(sid, "track my order")
print("Bot:", r["reply"])
assert "What's your order number" in r["reply"], "FAIL: should switch to order tracking, not treat as weather answer"

section("6i. Regression: 'not sure' / 'anything' are valid no-preference answers")
r = new_chat("can you recommend a product")
sid = r["session_id"]
r = chat(sid, "not sure")
print("Bot:", r["reply"])
assert "One more thing" in r["reply"], "FAIL: 'not sure' should be accepted as a valid general answer"
r = chat(sid, "anything is fine")
print("Bot:", r["reply"])
assert "Bestsellers" in r["reply"]

section("6j. Regression: natural 'no preference' variants + no awkward 'general' echo")
for phrase in ["No idea", "dunno", "idk", "no clue"]:
    r = new_chat("can you recommend a product")
    sid = r["session_id"]
    r = chat(sid, phrase)
    print(f"[{phrase}] Bot:", r["reply"])
    assert "One more thing" in r["reply"], f"FAIL: '{phrase}' not accepted as no-preference"
    # The reply should NOT echo the internal category key back to the user.
    assert "general" not in r["reply"].lower(), f"FAIL: awkward 'general' echoed for '{phrase}'"

section("6k. Regression: common typos still route to the right intent")
typo_cases = {
    "where is my packeg": "What's your order number",   # order tracking
    "trak my package": "What's your order number",
    "retrn policy": "30-day returns",                    # returns
    "recomend a product": "What kind of activity",       # recommendation
    "talk to a humen": "live agent",                     # human handoff
}
for phrase, expected_snippet in typo_cases.items():
    r = new_chat(phrase)
    print(f"[{phrase}] Bot:", r["reply"][:70])
    assert expected_snippet in r["reply"], f"FAIL: typo '{phrase}' did not route correctly"

section("6l. Regression: gibberish still rejected (typo tolerance didn't over-trigger)")
for phrase in ["here is tajmahal", "what is the weather today", "purple elephant"]:
    r = new_chat(phrase)
    print(f"[{phrase}] Bot:", r["reply"][:50])
    assert "didn't quite catch" in r["reply"], f"FAIL: '{phrase}' falsely matched an intent"

section("6m. Regression: delivered-order followup 'all good' answers close cheerfully")
for answer in ["no, all good", "all good", "everything is fine", "it's fine", "nope"]:
    r = new_chat("track my order")
    sid = r["session_id"]
    chat(sid, "333")
    r = chat(sid, answer)
    print(f"[{answer}] Bot:", r["reply"][:40])
    assert "Glad to hear" in r["reply"], f"FAIL: '{answer}' should close cheerfully, not hand off"

section("6n. Regression: delivered-order followup reporting a problem hands off")
for answer in ["yes there is an issue", "it's damaged", "the item is broken"]:
    r = new_chat("track my order")
    sid = r["session_id"]
    chat(sid, "333")
    r = chat(sid, answer)
    print(f"[{answer}] Bot:", r["reply"][:40])
    assert "live agent" in r["reply"].lower(), f"FAIL: '{answer}' should hand off to a live agent"

section("6o. Regression: switching to returns from delivered-order followup")
r = new_chat("track my order")
sid = r["session_id"]
chat(sid, "333")
r = chat(sid, "what is your return policy")
print("Bot:", r["reply"][:40])
assert "30-day returns" in r["reply"], "FAIL: should route to returns, not hand off"

print("\n\n✅ ALL TESTS PASSED")
