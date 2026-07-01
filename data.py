"""
data.py

This module contains ONLY the business data explicitly provided in the
project brief (mock orders, return policy, shipping info). Nothing here
is invented — every value matches the brief exactly.

This is intentionally kept separate from intent_classifier.py, which
contains phrase *patterns* (code logic), not business data.
"""

# ---------------------------------------------------------------------------
# Mock Order Data (exact, as provided in the brief)
# ---------------------------------------------------------------------------
ORDER_STATUS = {
    "111": "Shipped, arriving tomorrow.",
    "222": "Processing, ships in 24 hours.",
    "333": "Delivered.",
}

ORDER_NOT_FOUND_MESSAGE = (
    "Hmm, I couldn't find that order number in our system. "
    "Could you double-check and send it again? (e.g., 111, 222, 333)"
)

# Follow-up offered specifically for delivered orders, per the brief:
# "Order #333 -> Delivered (ask follow-up if needed)"
DELIVERED_FOLLOW_UP = (
    "Looks like it's already delivered! 🏕️ Is everything in good shape, "
    "or is there an issue with the order?"
)

# ---------------------------------------------------------------------------
# Return & Exchange Policy (exact, as provided in the brief)
# ---------------------------------------------------------------------------
RETURN_POLICY_TEXT = (
    "Here's our Return & Exchange policy:\n"
    "• 30-day returns\n"
    "• Items must be unused\n"
    "• Original packaging required\n\n"
    "You can start a return here: https://northstar-gear.example.com/returns"
)

RETURNS_LINK = "https://northstar-gear.example.com/returns"

# ---------------------------------------------------------------------------
# Shipping Information (exact, as provided in the brief)
# ---------------------------------------------------------------------------
SHIPPING_INFO_TEXT = (
    "Here's our shipping info:\n"
    "• Standard shipping: 3-5 business days\n"
    "• Expedited shipping: 1-2 business days"
)

# ---------------------------------------------------------------------------
# Product Recommendation Categories
# (Reasonable general categories for an outdoor/camping gear store, used
#  only to route the recommendation flow — not claimed as brief-provided data)
# ---------------------------------------------------------------------------
PRODUCT_CATEGORIES = {
    "hiking": "our Hiking collection — lightweight boots, trekking poles, and daypacks 🥾",
    "camping": "our Camping collection — tents, sleeping bags, and portable stoves ⛺",
    "climbing": "our Climbing gear — harnesses, ropes, and grip-friendly apparel 🧗",
    "cold_weather": "our Cold Weather line — insulated jackets, thermal layers, and gloves 🧤",
    "general": "our Bestsellers collection, great for most outdoor adventures 🌲",
}

BRAND_NAME = "North Star Support Bot"
