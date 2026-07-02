"""
test_chatbot.py

Pytest test suite for the North Star Support Bot.

This uses pytest so you get a clean report showing how many tests
passed/failed and the pass percentage (the familiar "dots" progress
output). It talks to the conversation engine directly (no running
server needed), so you can simply run:

    pytest -v            # verbose: shows each test name + PASS/FAIL
    pytest               # compact: shows dots for progress
    pytest --tb=short    # shorter tracebacks on failure

Each test maps to a requirement from the project brief, grouped by the
four required use cases plus intent recognition, fallback handling,
shipping info, and edge cases. The report doubles as a
requirements-coverage checklist.
"""

import pytest

from conversation import Session, process_message


def bot(session: Session, message: str) -> str:
    """Send one message through the bot and return its reply."""
    return process_message(session, message)


def fresh() -> Session:
    """Start a brand-new conversation session."""
    return Session()


# ===========================================================================
# USE CASE 1: Order Tracking
# ===========================================================================
class TestOrderTracking:
    def test_asks_for_order_number(self):
        s = fresh()
        assert "order number" in bot(s, "Track my order").lower()

    def test_order_111_shipped(self):
        s = fresh()
        bot(s, "Track my order")
        assert "Shipped, arriving tomorrow" in bot(s, "111")

    def test_order_222_processing(self):
        s = fresh()
        bot(s, "Track my order")
        assert "Processing, ships in 24 hours" in bot(s, "222")

    def test_order_333_delivered_with_followup(self):
        s = fresh()
        bot(s, "Track my order")
        reply = bot(s, "333")
        assert "Delivered" in reply
        assert "good shape" in reply

    def test_invalid_order_number(self):
        s = fresh()
        bot(s, "Track my order")
        assert "couldn't find that order" in bot(s, "999")

    def test_bare_order_number_after_resolved(self):
        s = fresh()
        bot(s, "Track my order")
        bot(s, "222")
        assert "Shipped, arriving tomorrow" in bot(s, "111")


# ===========================================================================
# USE CASE 2: Returns & Exchanges
# ===========================================================================
class TestReturns:
    def test_return_policy_content(self):
        s = fresh()
        reply = bot(s, "What is your return policy?")
        assert "30-day returns" in reply
        assert "unused" in reply.lower()
        assert "original packaging" in reply.lower()

    def test_return_provides_link(self):
        s = fresh()
        reply = bot(s, "How do I return an item?")
        assert "returns" in reply.lower()
        assert "http" in reply.lower()


# ===========================================================================
# USE CASE 3: Product Recommendation
# ===========================================================================
class TestRecommendation:
    def test_asks_first_clarifying_question(self):
        s = fresh()
        assert "activity" in bot(s, "Can you recommend a product?").lower()

    def test_asks_second_clarifying_question(self):
        s = fresh()
        bot(s, "Can you recommend a product?")
        assert "weather" in bot(s, "hiking").lower()

    def test_full_recommendation_flow(self):
        s = fresh()
        bot(s, "Can you recommend a product?")
        bot(s, "camping")
        assert "Camping collection" in bot(s, "warm")

    def test_cold_weather_upgrades_category(self):
        s = fresh()
        bot(s, "Can you recommend a product?")
        bot(s, "hiking")
        assert "Cold Weather" in bot(s, "cold")

    def test_no_preference_accepted(self):
        s = fresh()
        bot(s, "Can you recommend a product?")
        reply = bot(s, "no idea")
        assert "one more thing" in reply.lower()
        assert "general" not in reply.lower()

    def test_gibberish_activity_reasks(self):
        s = fresh()
        bot(s, "Can you recommend a product?")
        assert "didn't quite catch" in bot(s, "Tajmahal")

    def test_repeated_gibberish_escapes_to_main_fallback(self):
        """After repeated unrecognized answers, the bot should stop looping
        on the activity question and fall back to the main menu options."""
        s = fresh()
        bot(s, "Can you recommend a product?")
        bot(s, "here is tajmahal")        # first unrecognized -> re-ask
        reply = bot(s, "asdfghjkl")        # second unrecognized -> main fallback
        assert "Track an order" in reply   # main options list, not the activity re-ask
        assert "activity" not in reply.lower()

    def test_recovers_after_one_gibberish(self):
        """One bad answer followed by a valid one should still complete."""
        s = fresh()
        bot(s, "Can you recommend a product?")
        bot(s, "blahblah")                 # unrecognized -> re-ask
        bot(s, "hiking")                    # valid -> proceeds to weather
        reply = bot(s, "warm")
        assert "Hiking collection" in reply


# ===========================================================================
# USE CASE 4: Human Handoff
# ===========================================================================
class TestHumanHandoff:
    def test_explicit_request(self):
        s = fresh()
        assert "Live Agent" in bot(s, "I want to talk to a human")

    def test_return_to_menu_after_handoff(self):
        s = fresh()
        bot(s, "I want to talk to a human")
        assert "help you with" in bot(s, "menu").lower()

    def test_fallback_then_escalate(self):
        s = fresh()
        bot(s, "asdfghjkl")
        assert "Live Agent" in bot(s, "human")


# ===========================================================================
# Intent Recognition (handles phrasing variations + typos)
# ===========================================================================
class TestIntentRecognition:
    @pytest.mark.parametrize("phrase", [
        "Where is my order?",
        "Track my package",
        "What's the status of my order",
        "Has my order shipped",
    ])
    def test_order_tracking_variations(self, phrase):
        s = fresh()
        assert "order number" in bot(s, phrase).lower()

    @pytest.mark.parametrize("phrase", [
        "I want to return this",
        "How do exchanges work",
        "What is your return policy",
    ])
    def test_returns_variations(self, phrase):
        s = fresh()
        assert "30-day returns" in bot(s, phrase)

    @pytest.mark.parametrize("phrase,expected", [
        ("where is my packeg", "order number"),
        ("trak my package", "order number"),
        ("retrn policy", "30-day returns"),
        ("recomend a product", "activity"),
    ])
    def test_typo_tolerance(self, phrase, expected):
        s = fresh()
        assert expected in bot(s, phrase).lower()


# ===========================================================================
# Fallback Handling
# ===========================================================================
class TestFallback:
    @pytest.mark.parametrize("phrase", [
        "asdfghjkl",
        "here is tajmahal",
        "purple elephant",
        "what is the weather today",
    ])
    def test_gibberish_triggers_fallback(self, phrase):
        s = fresh()
        assert "didn't quite catch" in bot(s, phrase)

    def test_fallback_offers_options(self):
        s = fresh()
        reply = bot(s, "asdfghjkl")
        assert "Track an order" in reply
        assert "human" in reply.lower()


# ===========================================================================
# Shipping Information
# ===========================================================================
class TestShipping:
    def test_shipping_info_content(self):
        s = fresh()
        reply = bot(s, "how long does shipping take")
        assert "3-5 business days" in reply
        assert "1-2 business days" in reply


# ===========================================================================
# Delivered-order follow-up handling
# ===========================================================================
class TestDeliveredFollowup:
    @pytest.mark.parametrize("answer", [
        "no, all good",
        "all good",
        "everything is fine",
        "nope",
    ])
    def test_all_good_closes_cheerfully(self, answer):
        s = fresh()
        bot(s, "track my order")
        bot(s, "333")
        assert "Glad to hear" in bot(s, answer)

    @pytest.mark.parametrize("answer", [
        "yes there is an issue",
        "it's damaged",
        "the item is broken",
    ])
    def test_problem_hands_off(self, answer):
        s = fresh()
        bot(s, "track my order")
        bot(s, "333")
        assert "live agent" in bot(s, answer).lower()


# ===========================================================================
# Edge cases
# ===========================================================================
class TestEdgeCases:
    def test_empty_message(self):
        s = fresh()
        assert "didn't quite catch" in bot(s, "")

    def test_menu_command_resets(self):
        s = fresh()
        bot(s, "track my order")
        assert "help you with" in bot(s, "menu").lower()

    def test_uppercase_input(self):
        s = fresh()
        assert "order number" in bot(s, "TRACK MY ORDER").lower()
