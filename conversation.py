"""
conversation.py

Conversation state machine for the North Star Support Bot.

Each session has:
  - `state`: which step of a guided flow the user is in
  - `context`: temporary data collected during a flow (e.g. recommendation answers)

Design goals (mapped to brief requirements):
  - Logical, guided interactions (state machine below)
  - Returns to main menu after resolution (every terminal response reoffers the menu)
  - Fallback handling with clear "I didn't understand" + escalation option
  - Human handoff with return-to-menu support
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from data import (
    BRAND_NAME,
    DELIVERED_FOLLOW_UP,
    ORDER_NOT_FOUND_MESSAGE,
    ORDER_STATUS,
    PRODUCT_CATEGORIES,
    RETURN_POLICY_TEXT,
    SHIPPING_INFO_TEXT,
)
from intent_classifier import (
    INTENT_AFFIRM,
    INTENT_DENY,
    INTENT_HUMAN_HANDOFF,
    INTENT_MAIN_MENU,
    INTENT_ORDER_TRACKING,
    INTENT_RECOMMENDATION,
    INTENT_RETURNS,
    INTENT_SHIPPING_INFO,
    classifier,
)

# ---------------------------------------------------------------------------
# States
# ---------------------------------------------------------------------------
STATE_MAIN_MENU = "MAIN_MENU"
STATE_AWAITING_ORDER_NUMBER = "AWAITING_ORDER_NUMBER"
STATE_AWAITING_DELIVERED_FOLLOWUP = "AWAITING_DELIVERED_FOLLOWUP"
STATE_AWAITING_REC_ACTIVITY = "AWAITING_REC_ACTIVITY"
STATE_AWAITING_REC_WEATHER = "AWAITING_REC_WEATHER"
STATE_LIVE_AGENT = "LIVE_AGENT"

MAIN_MENU_OPTIONS = [
    "📦 Track my order",
    "↩️ Returns & Exchanges",
    "🎒 Product recommendation",
    "🙋 Talk to a human",
]

WELCOME_MESSAGE = (
    f"Hey there! 👋 I'm {BRAND_NAME}, here to help with anything outdoor-gear related. "
    "I can help you:\n"
    "• Track an order\n"
    "• Handle a return or exchange\n"
    "• Recommend gear for your next trip\n"
    "• Connect you to a live agent\n\n"
    "What can I help you with?"
)

FALLBACK_MESSAGE = (
    "Hmm, I didn't quite catch that. 🤔 Here's what I can help with:\n"
    "• Track an order\n"
    "• Returns & Exchanges\n"
    "• Product recommendations\n"
    "• Talk to a live agent\n\n"
    "Or just type 'human' anytime to reach a live agent."
)

REC_ACTIVITY_CLARIFY_MESSAGE = (
    "Hmm, I didn't quite catch that. 🤔 Could you tell me what kind of "
    "activity you're gearing up for — hiking, camping, climbing, or "
    "something in cold weather? (Or just say 'not sure' if you don't have "
    "a preference!)"
)

REC_WEATHER_CLARIFY_MESSAGE = (
    "Sorry, I didn't quite catch that. 🤔 Will you mostly be out in warm "
    "weather, cold weather, or mixed conditions?"
)

# ---------------------------------------------------------------------------
# Recommendation flow: keyword/signal recognition
# ---------------------------------------------------------------------------
# These map recognizable words in the user's free-text answer to a known
# category. Anything that matches none of these (activity keywords, weather
# keywords, or a general "no preference" signal) is treated as unrecognized
# input rather than silently defaulted to "general" — e.g. "Tajmahal" should
# prompt a clarifying re-ask, not be accepted as a valid answer.
ACTIVITY_KEYWORDS: dict[str, list[str]] = {
    "hiking": ["hike", "hikes", "hiking", "trek", "treks", "trekking", "trail", "trails"],
    "camping": ["camp", "camps", "camping", "campsite", "campsites", "tent", "tents"],
    "climbing": ["climb", "climbs", "climbing", "mountaineer", "mountaineering"],
    "cold_weather": [
        "cold", "winter", "snow", "ski", "skis", "skiing", "snowboard", "snowboarding",
    ],
}

WEATHER_COLD_SIGNALS = ["cold", "winter", "snow", "freezing", "chilly"]
WEATHER_WARM_SIGNALS = ["warm", "hot", "summer"]
WEATHER_MIXED_SIGNALS = ["mixed", "both", "vary", "varies", "everything", "all conditions"]

# Phrases indicating the user has no specific preference; treated as an
# explicit "general" choice rather than an unrecognized answer.
GENERAL_PREFERENCE_SIGNALS = [
    "general", "anything", "any", "not sure", "unsure", "not picky",
    "no preference", "no idea", "no clue", "dont know", "don't know",
    "dunno", "idk", "whatever", "surprise me", "you decide", "you choose",
    "doesn't matter", "does not matter", "not really", "either", "everything",
]


def _contains_phrase(text: str, phrase: str) -> bool:
    """Word-boundary-safe check for whether `phrase` appears in `text`.

    Using a plain substring check (`phrase in text`) would let short
    signal words produce false positives — e.g. "any" matching inside
    "company" or "many". This anchors the match to word boundaries so
    only whole-word/phrase matches count.
    """
    return re.search(rf"\b{re.escape(phrase)}\b", text) is not None


def _match_activity_signal(text: str) -> str | None:
    """Identify which activity/category (or general preference) the user's
    free-text answer maps to.

    Args:
        text: The user's raw answer to "what activity are you gearing up for?"

    Returns:
        A category key ("hiking", "camping", "climbing", "cold_weather",
        or "general") if a recognizable signal was found; otherwise None,
        meaning the input didn't match anything we can confidently act on.
    """
    lower = text.lower()
    for category, keywords in ACTIVITY_KEYWORDS.items():
        if any(_contains_phrase(lower, kw) for kw in keywords):
            return category
    if any(_contains_phrase(lower, sig) for sig in GENERAL_PREFERENCE_SIGNALS):
        return "general"
    return None


def _match_weather_signal(text: str) -> str | None:
    """Identify which weather condition the user's free-text answer maps to.

    Args:
        text: The user's raw answer to the weather clarifying question.

    Returns:
        "cold", "warm", or "mixed" if a recognizable signal was found
        (a general "no preference" answer counts as "mixed"); otherwise
        None if the input didn't match anything recognizable.
    """
    lower = text.lower()
    if any(_contains_phrase(lower, sig) for sig in WEATHER_COLD_SIGNALS):
        return "cold"
    if any(_contains_phrase(lower, sig) for sig in WEATHER_WARM_SIGNALS):
        return "warm"
    if any(_contains_phrase(lower, sig) for sig in WEATHER_MIXED_SIGNALS):
        return "mixed"
    if any(_contains_phrase(lower, sig) for sig in GENERAL_PREFERENCE_SIGNALS):
        return "mixed"
    return None


@dataclass
class Session:
    """Holds per-user conversation state between chat turns.

    Attributes:
        state: The current step of the guided flow (see STATE_* constants).
        context: Temporary data collected during a multi-step flow, such as
            the activity type chosen mid-way through the product
            recommendation flow. Cleared once that flow completes.
        clarify_attempts: How many times in a row the user has given an
            unrecognized answer to the current clarifying question. Used to
            escape a flow gracefully (fall back to the main menu/options)
            instead of asking the same question forever.
    """

    state: str = STATE_MAIN_MENU
    context: dict = field(default_factory=dict)
    clarify_attempts: int = 0


# After this many consecutive unrecognized answers in a guided flow, the
# bot stops re-asking and falls back to the main menu / options so the
# user is never stuck in a loop.
MAX_CLARIFY_ATTEMPTS = 2


def _menu_footer() -> str:
    """Return the standard closing line appended after a resolved request,
    reminding the user they can keep chatting or return to the main menu."""
    return "\n\nWhat else can I help you with? (or type 'menu' anytime)"


def _order_tracking_start() -> tuple[str, str]:
    """Begin the Order Tracking flow by asking the user for their order number.

    Returns:
        A (next_state, reply) tuple. Moves the session into
        STATE_AWAITING_ORDER_NUMBER so the next user message is treated
        as an order number rather than a new intent.
    """
    return (
        STATE_AWAITING_ORDER_NUMBER,
        "Sure, happy to check that for you! What's your order number? (e.g. 111)",
    )


def _handle_order_number(text: str) -> tuple[str, str]:
    """Look up the order number the user just provided and build a reply.

    Extracts digits from the raw input (so "#111" or "order 111" both work),
    matches against the exact mock order data in data.py, and returns the
    exact status text for a valid order or the standard "not found" message
    for anything else, per the brief's requirement to use the provided
    mock data exactly.

    Args:
        text: The raw user message expected to contain an order number.

    Returns:
        A (next_state, reply) tuple. Order #333 (Delivered) routes to a
        follow-up question state; other valid orders return to the main
        menu; an invalid number keeps the session waiting for a retry.
    """
    digits = "".join(ch for ch in text if ch.isdigit())

    if digits in ORDER_STATUS:
        status = ORDER_STATUS[digits]
        if digits == "333":
            return (
                STATE_AWAITING_DELIVERED_FOLLOWUP,
                f"Order #{digits} status: {status}\n\n{DELIVERED_FOLLOW_UP}",
            )
        return (
            STATE_MAIN_MENU,
            f"Order #{digits} status: {status}{_menu_footer()}",
        )

    return (STATE_AWAITING_ORDER_NUMBER, ORDER_NOT_FOUND_MESSAGE)


def _returns_response() -> tuple[str, str]:
    """Return the exact Return & Exchange policy text plus the returns link.

    Returns:
        A (next_state, reply) tuple. Resolves immediately and returns the
        session to the main menu.
    """
    return (STATE_MAIN_MENU, RETURN_POLICY_TEXT + _menu_footer())


def _shipping_response() -> tuple[str, str]:
    """Return the exact shipping information (standard and expedited timelines).

    Returns:
        A (next_state, reply) tuple. Resolves immediately and returns the
        session to the main menu.
    """
    return (STATE_MAIN_MENU, SHIPPING_INFO_TEXT + _menu_footer())


def _recommendation_start() -> tuple[str, str]:
    """Begin the Product Recommendation flow with the first clarifying question.

    Returns:
        A (next_state, reply) tuple. Moves the session into
        STATE_AWAITING_REC_ACTIVITY to await the user's activity type.
    """
    return (
        STATE_AWAITING_REC_ACTIVITY,
        "Love it! 🌲 What kind of activity are you gearing up for — "
        "hiking, camping, climbing, or something in cold weather?",
    )


def _recommendation_activity(text: str) -> tuple[str, str, str] | None:
    """Parse the user's answer to the first recommendation clarifying question.

    Args:
        text: The user's raw answer describing their planned activity.

    Returns:
        A (next_state, reply, matched_activity_key) tuple if the answer
        matched a known activity keyword or an explicit "no preference"
        signal. Returns None if nothing recognizable was found (e.g. an
        unrelated word like "Tajmahal"), so the caller can ask again
        instead of silently guessing "general" for irrelevant input.
    """
    matched = _match_activity_signal(text)
    if matched is None:
        return None

    # Use a natural, human-readable acknowledgement rather than echoing the
    # internal category key (e.g. avoid the awkward "Got it, general!" when
    # the user said "no idea", or "Got it, cold weather!").
    acknowledgements = {
        "hiking": "Nice, hiking it is!",
        "camping": "Awesome, camping it is!",
        "climbing": "Great, climbing it is!",
        "cold_weather": "Got it — cold-weather adventures!",
        "general": "No worries, I can point you to something versatile!",
    }
    ack = acknowledgements.get(matched, "Got it!")

    reply = (
        f"{ack} One more thing — "
        "will you mostly be out in warm weather, cold weather, or mixed conditions?"
    )
    return STATE_AWAITING_REC_WEATHER, reply, matched


def _recommendation_final(activity: str, weather_text: str) -> tuple[str, str] | None:
    """Resolve the Product Recommendation flow into a final category suggestion.

    Args:
        activity: The activity key captured from the first clarifying
            question (e.g. "hiking", "camping", "climbing", "general").
        weather_text: The user's raw answer to the second clarifying
            question about weather conditions.

    Returns:
        A (next_state, reply) tuple if the weather answer matched a
        recognizable signal (cold/warm/mixed/no-preference). A "cold"
        signal upgrades the recommendation to the Cold Weather category
        regardless of the original activity. Returns None if the answer
        didn't match anything recognizable, so the caller can ask again.
    """
    weather_signal = _match_weather_signal(weather_text)
    if weather_signal is None:
        return None

    category_key = "cold_weather" if weather_signal == "cold" else activity
    category_desc = PRODUCT_CATEGORIES.get(category_key, PRODUCT_CATEGORIES["general"])
    return (
        STATE_MAIN_MENU,
        f"Based on that, I'd recommend checking out {category_desc}{_menu_footer()}",
    )


def _human_handoff() -> tuple[str, str]:
    """Transition the session into the simulated Live Agent state.

    Called either when the user explicitly asks for a human, or when a
    fallback scenario escalates (e.g. after a delivered order follow-up
    where the user reports a problem).

    Returns:
        A (next_state, reply) tuple. Moves the session into
        STATE_LIVE_AGENT and clearly communicates the handoff to the user,
        including how to return to the bot (typing 'menu').
    """
    return (
        STATE_LIVE_AGENT,
        "No problem — connecting you to a live agent now. 🙋\n\n"
        "**[Live Agent]**: Hi, this is a live support agent, how can I help?\n\n"
        "(This is a simulated handoff. Type 'menu' anytime to return to the bot.)",
    )


def _main_menu_response() -> tuple[str, str]:
    """Reset the session to the main menu and return the welcome/menu message.

    Returns:
        A (next_state, reply) tuple. Used both for the initial greeting
        and whenever the user explicitly asks to return to the main menu.
    """
    return (STATE_MAIN_MENU, WELCOME_MESSAGE)


def _looks_like_order_number(text: str) -> bool:
    """Check whether the message is essentially just an order number.

    Matches inputs like "111" or "#111" (optionally with surrounding
    whitespace), but not full sentences that merely contain a digit
    (e.g. "I want to track my order" or "order 111 please"), which are
    left to intent classification / the state-specific digit extraction
    instead.

    Args:
        text: The raw user message.

    Returns:
        True if the message is nothing but digits (after stripping a
        leading "#" and surrounding whitespace).
    """
    stripped = text.strip().lstrip("#").strip()
    return stripped.isdigit() and len(stripped) > 0


def _handle_core_intent(session: Session, intent: str) -> str | None:
    """Route a confidently-detected core intent to its starting flow.

    This is shared by two callers:
      1. The main-menu routing step (a fresh request from a neutral state).
      2. Mid-flow states like STATE_AWAITING_ORDER_NUMBER, so that if a
         user changes topic instead of answering the expected question
         (e.g. types "return policy" while the bot is waiting for an
         order number), the bot recognizes the new intent and switches
         flows instead of misreporting the old flow as failed/invalid.

    Args:
        session: The session to update (mutated in place on a match).
        intent: One of the INTENT_* constants from a prior classify() call.

    Returns:
        The reply text if `intent` matched one of the core, routable
        intents (order tracking, returns, shipping, recommendation, main
        menu); otherwise None, signaling "no route found" so the caller
        can fall back to its own state-specific handling.
    """
    if intent == INTENT_ORDER_TRACKING:
        session.state, reply = _order_tracking_start()
        return reply

    if intent == INTENT_RETURNS:
        session.state, reply = _returns_response()
        return reply

    if intent == INTENT_SHIPPING_INFO:
        session.state, reply = _shipping_response()
        return reply

    if intent == INTENT_RECOMMENDATION:
        session.state, reply = _recommendation_start()
        return reply

    if intent == INTENT_MAIN_MENU:
        session.state, reply = _main_menu_response()
        return reply

    return None


def process_message(session: Session, user_text: str) -> str:
    """Advance the conversation state machine by one turn and return the bot's reply.

    This is the single entry point the FastAPI layer calls for every
    incoming user message. It applies, in order:

    1. Global overrides available from any state ("menu" to reset, an
       explicit human-handoff request).
    2. State-specific handling for multi-turn flows currently in progress
       (e.g. awaiting an order number, awaiting recommendation answers).
    3. Intent-based routing from the main menu into one of the four core
       use cases.
    4. A fallback response if no intent could be confidently matched.

    Args:
        session: The caller's Session object; mutated in place to reflect
            the new state after this turn.
        user_text: The raw message text the user just sent.

    Returns:
        The chatbot's reply text for this turn.
    """
    raw_text = (user_text or "").strip()
    lowered = raw_text.lower()

    # Global override: user can request main menu or human handoff from ANY state.
    if lowered in {"menu", "main menu"}:
        session.state, reply = _main_menu_response()
        return reply

    result = classifier.classify(raw_text)

    # Global human-handoff override (explicit request), except while already
    # awaiting an order number/answer where digits might coincidentally match.
    if result.intent == INTENT_HUMAN_HANDOFF and session.state != STATE_LIVE_AGENT:
        session.state, reply = _human_handoff()
        return reply

    # A bare/near-bare order number (e.g. "111" or "#111") is treated as an
    # order lookup regardless of the current state — except states that
    # expect free-text answers (the recommendation clarifying questions)
    # or the live-agent handoff. This lets a user look up a second order
    # (e.g. right after seeing order #222's status) without having to
    # repeat "track my order" first.
    if (
        session.state not in (STATE_AWAITING_REC_ACTIVITY, STATE_AWAITING_REC_WEATHER, STATE_LIVE_AGENT)
        and _looks_like_order_number(raw_text)
    ):
        session.state, reply = _handle_order_number(raw_text)
        return reply

    # --- State-specific handling (guided multi-turn flows) -----------------
    if session.state == STATE_AWAITING_ORDER_NUMBER:
        digits = "".join(ch for ch in raw_text if ch.isdigit())
        if digits:
            # Looks like an order number attempt — validate it.
            session.state, reply = _handle_order_number(raw_text)
            if session.state != STATE_AWAITING_ORDER_NUMBER:
                # A valid order resolved the flow — reset the counter.
                session.clarify_attempts = 0
                return reply
            # Invalid number: still awaiting. Count it as a failed attempt,
            # and after too many, exit to the main fallback instead of
            # asking for a number indefinitely.
            session.clarify_attempts += 1
            if session.clarify_attempts >= MAX_CLARIFY_ATTEMPTS:
                session.state = STATE_MAIN_MENU
                session.clarify_attempts = 0
                return FALLBACK_MESSAGE
            return reply

        # No digits typed: the user likely switched topics instead of
        # answering with an order number (e.g. "return policy" or
        # "I want to track my order" again). Try to route the new intent
        # rather than incorrectly reporting "order not found".
        switched_reply = _handle_core_intent(session, result.intent)
        if switched_reply is not None:
            session.clarify_attempts = 0
            return switched_reply

        # Genuinely unclear input (e.g. gibberish). Re-ask a couple of
        # times, but if the user keeps giving unrecognized input, exit to
        # the main fallback so they're never stuck asking for a number.
        session.clarify_attempts += 1
        if session.clarify_attempts >= MAX_CLARIFY_ATTEMPTS:
            session.state = STATE_MAIN_MENU
            session.clarify_attempts = 0
            return FALLBACK_MESSAGE
        return ORDER_NOT_FOUND_MESSAGE

    if session.state == STATE_AWAITING_DELIVERED_FOLLOWUP:
        # "Everything in good shape, or is there an issue?"
        # Treat a denial ("no"), or any reassuring phrase, as "all good".
        all_good_signals = [
            "no", "nope", "nah", "all good", "good", "fine", "great",
            "perfect", "everything ok", "everything is ok", "everything's fine",
            "no issue", "no issues", "no problem", "all fine", "its fine",
            "it's fine", "thanks", "thank you",
        ]
        problem_signals = [
            "yes", "yeah", "yep", "issue", "issues", "problem", "problems",
            "damaged", "broken", "wrong", "missing", "defective", "not working",
        ]

        has_problem = any(_contains_phrase(lowered, s) for s in problem_signals)
        has_all_good = any(_contains_phrase(lowered, s) for s in all_good_signals)

        # If the user clearly reports a problem, hand off to a live agent.
        if has_problem and not has_all_good:
            session.state, reply = _human_handoff()
            return reply

        # If the user reassures us everything's fine (or denies an issue),
        # close the loop cheerfully and return to the menu.
        if has_all_good or result.intent == INTENT_DENY:
            session.state, reply = (
                STATE_MAIN_MENU,
                f"Glad to hear it! 🎉{_menu_footer()}",
            )
            return reply

        # If instead the user switched topics entirely (e.g. asked to track
        # a different order), follow that new intent.
        switched_reply = _handle_core_intent(session, result.intent)
        if switched_reply is not None:
            return switched_reply

        # Anything else is ambiguous — offer help via a live agent rather
        # than guessing, since this follows a delivered-order check-in.
        session.state, reply = _human_handoff()
        return reply

    if session.state == STATE_AWAITING_REC_ACTIVITY:
        outcome = _recommendation_activity(raw_text)
        if outcome is not None:
            session.state, reply, matched = outcome
            session.context["activity"] = matched
            session.clarify_attempts = 0
            return reply

        # Unrecognized answer — the user may have switched topics entirely
        # (e.g. asked about returns instead of naming an activity).
        switched_reply = _handle_core_intent(session, result.intent)
        if switched_reply is not None:
            session.context.clear()
            session.clarify_attempts = 0
            return switched_reply

        # Genuinely unclear. Re-ask a couple of times, but if the user keeps
        # giving unrecognized answers, exit the flow to the main fallback so
        # they're never stuck in a loop.
        session.clarify_attempts += 1
        if session.clarify_attempts >= MAX_CLARIFY_ATTEMPTS:
            session.state = STATE_MAIN_MENU
            session.context.clear()
            session.clarify_attempts = 0
            return FALLBACK_MESSAGE
        return REC_ACTIVITY_CLARIFY_MESSAGE

    if session.state == STATE_AWAITING_REC_WEATHER:
        activity = session.context.get("activity", "general")
        outcome = _recommendation_final(activity, raw_text)
        if outcome is not None:
            session.state, reply = outcome
            session.context.clear()
            session.clarify_attempts = 0
            return reply

        switched_reply = _handle_core_intent(session, result.intent)
        if switched_reply is not None:
            session.context.clear()
            session.clarify_attempts = 0
            return switched_reply

        session.clarify_attempts += 1
        if session.clarify_attempts >= MAX_CLARIFY_ATTEMPTS:
            session.state = STATE_MAIN_MENU
            session.context.clear()
            session.clarify_attempts = 0
            return FALLBACK_MESSAGE
        return REC_WEATHER_CLARIFY_MESSAGE

    if session.state == STATE_LIVE_AGENT:
        # Stay in live agent mode until user explicitly returns to menu.
        return (
            "**[Live Agent]**: Thanks for the details, our team will take it from here. "
            "(Type 'menu' to return to the bot anytime.)"
        )

    # --- MAIN_MENU state: route by detected intent --------------------------
    core_reply = _handle_core_intent(session, result.intent)
    if core_reply is not None:
        return core_reply

    if result.intent in (INTENT_AFFIRM, INTENT_DENY):
        session.state, reply = _main_menu_response()
        return reply

    # --- Fallback -------------------------------------------------------
    session.state = STATE_MAIN_MENU
    return FALLBACK_MESSAGE
