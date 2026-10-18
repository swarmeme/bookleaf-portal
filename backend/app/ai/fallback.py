"""Keyword-based triage, used when the AI is unavailable or not configured.

Deliberately simple and predictable. Tickets classified this way are marked
with source "fallback" so admins know to double-check them.
"""

import re
from dataclasses import dataclass

from app.models.enums import TicketCategory, TicketPriority

_CATEGORY_KEYWORDS: dict[TicketCategory, tuple[str, ...]] = {
    TicketCategory.ROYALTY_PAYMENTS: (
        "royalt", "payment", "payout", "paid", "bank", "money", "earning", "statement", "₹", "rupee", "invoice",
    ),
    TicketCategory.ISBN_METADATA: (
        "isbn", "metadata", "description", "author name", "title is wrong", "blurb", "imprint", "category on",
    ),
    TicketCategory.PRINTING_QUALITY: (
        "print", "blurry", "misalign", "binding", "defect", "damaged", "torn", "colour", "color", "quality",
        "pages are", "author copies", "misprint",
    ),
    TicketCategory.DISTRIBUTION_AVAILABILITY: (
        "unavailable", "not available", "out of stock", "amazon", "flipkart", "listing", "listed", "store",
        "buy my book", "search results",
    ),
    TicketCategory.BOOK_STATUS_PRODUCTION: (
        "typesetting", "cover design", "proofread", "production", "manuscript", "stage", "when will", "delay",
        "still in", "status", "editing", "proof",
    ),
    TicketCategory.GENERAL_INQUIRY: (
        "bio", "profile", "package", "account", "password", "contract", "bestseller breakthrough",
    ),
}

_LONG_TIME = r"(\b(\d+|several|many|four|five|six|seven|eight|nine|ten|twelve)\s+months?\b|\b(a|one|over a|\d+)\s+years?\b)"
_CRITICAL_PATTERNS = (
    rf"{_LONG_TIME}[\s\S]*\b(royalt|pay|paid|money)",
    rf"\b(royalt|pay|paid|money)[\s\S]*{_LONG_TIME}",
    r"\b(legal|lawyer|court|fraud|scam|piracy|pirated|cheat)",
    r"\bwrong book\b",
)
_HIGH_PATTERNS = (
    r"\bnever (received|got|been paid)\b",
    r"\b(not|haven't|have not|didn't|did not) (received|been paid|got)\b",
    r"\b(overdue|urgent|asap|immediately)\b",
    r"\b(defect|damaged|misprint|blurry|misalign)",
    r"\b(unavailable|not available|out of stock)\b",
    r"\bduplicate\b",
)
_LOW_PATTERNS = (
    r"\b(bio|biography|profile|photo)\b",
    r"^(can|could|how do|how can|is it possible)\b",
    r"\b(just wondering|quick question|curious)\b",
)


@dataclass(frozen=True)
class FallbackTriage:
    category: TicketCategory
    priority: TicketPriority
    reasoning: str


def _any(patterns: tuple[str, ...], text: str) -> bool:
    return any(re.search(p, text, re.MULTILINE) for p in patterns)


def classify(subject: str, description: str) -> FallbackTriage:
    text = f"{subject}\n{description}".lower()

    scores = {cat: sum(text.count(kw) for kw in kws) for cat, kws in _CATEGORY_KEYWORDS.items()}
    best, best_score = max(scores.items(), key=lambda item: item[1])
    category = best if best_score > 0 else TicketCategory.GENERAL_INQUIRY

    if _any(_CRITICAL_PATTERNS, text):
        priority = TicketPriority.CRITICAL
    elif category == TicketCategory.ISBN_METADATA and re.search(r"\b(isbn|wrong|different|duplicate)", text):
        priority = TicketPriority.HIGH  # policy: ISBN errors are always high priority
    elif _any(_HIGH_PATTERNS, text):
        priority = TicketPriority.HIGH
    elif _any(_LOW_PATTERNS, text) or category == TicketCategory.GENERAL_INQUIRY:
        priority = TicketPriority.LOW
    else:
        priority = TicketPriority.MEDIUM

    return FallbackTriage(category, priority, "Set by keyword rules because AI triage was unavailable.")
