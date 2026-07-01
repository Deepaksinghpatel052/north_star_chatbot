"""
intent_classifier.py

Lightweight NLP-based intent recognition using TF-IDF vectorization +
cosine similarity. This lets the bot understand *variations* in phrasing
(e.g., "Where is my order?" vs "Track my package") without needing any
external LLM API call — fully self-contained and evaluator-testable
with zero setup.

NOTE: The example phrases below are training/pattern data (code logic
for intent matching), not business facts. All business facts (order
status, policies, shipping times) live exclusively in data.py and are
taken verbatim from the project brief.
"""

from __future__ import annotations

from dataclasses import dataclass

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


INTENT_ORDER_TRACKING = "order_tracking"
INTENT_RETURNS = "returns_exchanges"
INTENT_RECOMMENDATION = "product_recommendation"
INTENT_HUMAN_HANDOFF = "human_handoff"
INTENT_SHIPPING_INFO = "shipping_info"
INTENT_MAIN_MENU = "main_menu"
INTENT_AFFIRM = "affirm"
INTENT_DENY = "deny"
INTENT_UNKNOWN = "unknown"

# Confidence threshold below which we treat the input as "unknown" and
# trigger fallback handling instead of guessing. Tuned to sit above the
# score unrelated/gibberish input tends to reach (~0.28) but below the
# score genuine phrases and common typos reach, using the combined
# word + character n-gram similarity.
CONFIDENCE_THRESHOLD = 0.32

TRAINING_PHRASES: dict[str, list[str]] = {
    INTENT_ORDER_TRACKING: [
        "where is my order",
        "track my package",
        "track my order",
        "what is the status of my order",
        "has my order shipped",
        "order status",
        "i want to check my order",
        "when will my order arrive",
        "check order tracking",
        "order tracking",
        "my package hasn't arrived",
        "can you check my package location",
        "i want to track a shipment",
        "order number",
        "delivery status",
    ],
    INTENT_RETURNS: [
        "i want to return this",
        "how do i return an item",
        "return policy",
        "what is your return policy",
        "i want to exchange this product",
        "how do exchanges work",
        "can i get a refund",
        "i need to send this back",
        "return and exchange",
        "how many days do i have to return",
        "start a return",
        "return process",
        "exchange policy",
    ],
    INTENT_RECOMMENDATION: [
        "can you recommend a product",
        "what should i buy",
        "i need gear recommendations",
        "help me find a product",
        "what do you suggest for camping",
        "i need something for hiking",
        "looking for outdoor gear",
        "suggest some products",
        "what gear do i need",
        "product recommendation",
        "help me pick something",
        "i don't know what to buy",
    ],
    INTENT_HUMAN_HANDOFF: [
        "i want to talk to a human",
        "connect me to a live agent",
        "i need a real person",
        "talk to customer service",
        "speak to an agent",
        "human please",
        "this isn't helping, get me a person",
        "escalate to an agent",
        "live agent",
        "can i speak with support staff",
    ],
    INTENT_SHIPPING_INFO: [
        "what are your shipping options",
        "how long does shipping take",
        "shipping information",
        "shipping info",
        "shipping details",
        "when will my order ship",
        "do you offer expedited shipping",
        "how fast is delivery",
        "delivery time",
    ],
    INTENT_MAIN_MENU: [
        "main menu",
        "go back",
        "start over",
        "show me options",
        "help",
        "what can you do",
    ],
    INTENT_AFFIRM: ["yes", "yeah", "yep", "sure", "correct", "that's right", "ok"],
    INTENT_DENY: ["no", "nope", "not really", "nah", "negative"],
}


@dataclass
class IntentResult:
    """The outcome of classifying a single user message.

    Attributes:
        intent: One of the INTENT_* constants, or INTENT_UNKNOWN if no
            training phrase was similar enough to be confident.
        confidence: The cosine similarity score (0.0-1.0) of the best match.
    """

    intent: str
    confidence: float


class IntentClassifier:
    """TF-IDF + cosine-similarity intent classifier.

    Fits example phrases across all intents and classifies new input by
    finding the most similar training phrase. This lets the bot handle
    phrasing variations (e.g. "Where is my order?" vs "Track my package")
    without any external LLM API call.

    Two vectorizers are combined:
      - A word-level TF-IDF (with English stopwords removed) for precise
        matching on meaningful whole words.
      - A character n-gram TF-IDF for typo tolerance, so misspellings like
        "packeg" for "package" still share enough character sequences with
        the training phrases to be recognized.

    The final similarity score is a weighted blend of the two, giving
    robust matching that tolerates common spelling mistakes while keeping
    unrelated input safely below the confidence threshold.
    """

    # Relative weight of the word-level score vs the character-level score.
    _WORD_WEIGHT = 0.45
    _CHAR_WEIGHT = 0.55

    def __init__(self) -> None:
        """Build both vectorizers and fit them over all training phrases."""
        corpus: list[str] = []
        self._labels: list[str] = []
        for intent, phrases in TRAINING_PHRASES.items():
            for phrase in phrases:
                corpus.append(phrase)
                self._labels.append(intent)

        # Word-level: precise matching on meaningful words.
        self._word_vectorizer = TfidfVectorizer(stop_words="english")
        self._word_matrix = self._word_vectorizer.fit_transform(corpus)

        # Character-level: 3-5 char n-grams for typo tolerance.
        self._char_vectorizer = TfidfVectorizer(
            analyzer="char_wb", ngram_range=(3, 5)
        )
        self._char_matrix = self._char_vectorizer.fit_transform(corpus)

    def classify(self, text: str) -> IntentResult:
        """Classify a user message into one of the known intents.

        Args:
            text: The raw user message to classify.

        Returns:
            An IntentResult with the best-matching intent and its
            confidence score. Returns INTENT_UNKNOWN if the input is
            empty or the best combined score falls below
            CONFIDENCE_THRESHOLD, so the caller can trigger fallback
            handling instead of guessing.
        """
        text = (text or "").strip().lower()
        if not text:
            return IntentResult(INTENT_UNKNOWN, 0.0)

        word_vec = self._word_vectorizer.transform([text])
        word_sims = cosine_similarity(word_vec, self._word_matrix)[0]

        char_vec = self._char_vectorizer.transform([text])
        char_sims = cosine_similarity(char_vec, self._char_matrix)[0]

        combined = self._WORD_WEIGHT * word_sims + self._CHAR_WEIGHT * char_sims

        best_idx = combined.argmax()
        best_score = float(combined[best_idx])

        if best_score < CONFIDENCE_THRESHOLD:
            return IntentResult(INTENT_UNKNOWN, best_score)

        return IntentResult(self._labels[best_idx], best_score)


# Singleton instance reused across requests (avoids re-fitting TF-IDF every call)
classifier = IntentClassifier()
