"""The BookLeaf Knowledge Base, split by ticket category.

A drafted reply only needs the policy for its own category, plus the tone
guidelines and one worked example. Sending just that slice instead of the whole
document keeps every draft call smaller (see `sections_for`).
"""

from dataclasses import dataclass

from app.models.enums import TicketCategory

COMPANY_OVERVIEW = """\
- BookLeaf Publishing is a self-publishing company operating in India and the US.
- Packages: Standard Free (no upfront cost) and Bestseller Breakthrough (premium, paid package with marketing and distribution add-ons).
- BookLeaf handles cover design, typesetting, ISBN assignment, printing, distribution and royalty management for its authors.
- In-house printing facility and warehouse in Delhi; print partners include Repro India and Epitome Books."""

TONE_GUIDELINES = """\
- Always empathetic and professional. Authors are our partners, not customers to be managed.
- Acknowledge the author's concern before jumping to solutions.
- Be specific: include actual numbers, dates and statuses wherever possible rather than vague reassurances.
- If something is BookLeaf's fault (delayed royalties, ISBN error), own it directly. No corporate deflection.
- If the issue requires escalation or investigation, give a clear timeline ("Our team will look into this and get back to you within 48 hours") rather than open-ended promises.
- Always end with a clear next step for the author and/or the BookLeaf team."""

ROYALTY_POLICY = """\
- 80/20 royalty split: 80% of the net profit per book goes to the author, 20% to BookLeaf.
- Net profit = MRP minus printing cost, platform commission (Amazon/Flipkart) and shipping charges.
- Royalties are calculated quarterly and paid within 45 days of the quarter ending.
- Minimum payout threshold: ₹1,000. If accumulated royalties are below this, they roll over to the next quarter.
- Payouts are made via bank transfer to the account linked in the author's dashboard.
- Authors can view a detailed royalty breakdown in their dashboard, showing sales figures per platform."""

ISBN_POLICY = """\
- Every book published through BookLeaf receives a unique ISBN assigned by BookLeaf.
- ISBNs are registered under BookLeaf's publisher imprint. An author who wants an ISBN under their own imprint must obtain it independently.
- An ISBN error (duplicate, wrong book linked) is a high-priority issue and is escalated to the production team.
- Metadata updates (e.g. book description) can be submitted through the dashboard or by emailing the BookLeaf team; changes typically reflect on platforms within 3-5 business days."""

PRINTING_POLICY = """\
- In-house printing (Delhi) handles most orders. Overflow or specific format requirements go to Repro India or Epitome Books.
- Standard print turnaround: 5-7 business days from order confirmation.
- Quality issues (misprints, binding defects, colour inconsistency): BookLeaf arranges a free reprint after verification. The author may need to share photos of the defective copy."""

DISTRIBUTION_POLICY = """\
- Books are listed on Amazon India, Flipkart, Amazon US, Amazon UK and the BookLeaf Store.
- New listings typically go live within 7-10 business days after publication is complete.
- A book showing as unavailable on a platform usually indicates a stock sync issue; BookLeaf's team can trigger a re-sync, which takes 24-48 hours."""

PRODUCTION_POLICY = """\
- Production stages: Manuscript Received -> Editing (if opted) -> Cover Design -> Typesetting -> Proofreading -> ISBN Assignment -> Printing -> Distribution Setup -> Published & Live.
- Authors are updated at each stage via email.
- Delays typically happen at Cover Design (waiting for author approval) and Proofreading (revision rounds).
- Frame delays collaboratively; never blame the author, even if the delay is on their side."""

# For general questions we don't know which policy applies, so send a compact digest of all of them.
GENERAL_DIGEST = """\
- Royalties: 80/20 split of net profit; calculated quarterly, paid within 45 days of quarter end; ₹1,000 minimum payout (smaller amounts roll over); paid by bank transfer to the account linked in the dashboard.
- ISBNs are assigned by BookLeaf under its imprint; authors wanting their own imprint must obtain an ISBN independently.
- Metadata updates (e.g. book description) can be submitted through the dashboard or by emailing the BookLeaf team; changes reflect on platforms within 3-5 business days.
- Printing turnaround 5-7 business days; free reprint for verified quality defects.
- Listings go live 7-10 business days after publication; availability problems are fixed by a re-sync within 24-48 hours.
- Production: Manuscript Received -> Editing (if opted) -> Cover Design -> Typesetting -> Proofreading -> ISBN Assignment -> Printing -> Distribution Setup -> Published & Live."""


@dataclass(frozen=True)
class Example:
    query: str
    approach: str


@dataclass(frozen=True)
class CategoryKnowledge:
    label: str
    policy: str
    examples: tuple[Example, ...]


KNOWLEDGE: dict[TicketCategory, CategoryKnowledge] = {
    TicketCategory.ROYALTY_PAYMENTS: CategoryKnowledge(
        "Royalty & Payments",
        ROYALTY_POLICY,
        (
            Example(
                "I published my book 4 months ago and still haven't received any royalty. What's going on?",
                "Acknowledge the frustration. Explain the quarterly royalty cycle and 45-day payout window. Check if "
                "their bank details are linked. Provide the specific next payout date. If the payment is genuinely "
                "overdue, escalate with a 48-hour resolution timeline.",
            ),
            Example(
                "My royalty amount seems too low. I sold 200 copies but only received ₹3,000.",
                "Explain the net profit calculation: MRP minus printing, platform commission and shipping. Offer to "
                "share a detailed line-by-line royalty breakdown. Don't be defensive; offer transparency.",
            ),
        ),
    ),
    TicketCategory.ISBN_METADATA: CategoryKnowledge(
        "ISBN & Metadata Issues",
        ISBN_POLICY,
        (
            Example(
                "My book is showing a different ISBN on Amazon than what's on the physical copy.",
                "Treat as high priority. Acknowledge this is a serious data issue. Confirm you are escalating to the "
                "production team immediately. Provide a 48-hour resolution timeline.",
            ),
        ),
    ),
    TicketCategory.PRINTING_QUALITY: CategoryKnowledge(
        "Printing & Quality",
        PRINTING_POLICY,
        (
            Example(
                "I received my author copies and the print quality is terrible. The images are blurry and pages are "
                "misaligned.",
                "Apologise sincerely. Ask the author to share photos of the defective copies. Confirm that BookLeaf "
                "will arrange a free reprint once verified. Provide a timeline of 5-7 business days for the reprint.",
            ),
        ),
    ),
    TicketCategory.DISTRIBUTION_AVAILABILITY: CategoryKnowledge(
        "Distribution & Availability",
        DISTRIBUTION_POLICY,
        (
            Example(
                "My book is published but it's showing as \"Currently Unavailable\" on Amazon.",
                "Explain that this is typically a stock sync issue. Confirm you're triggering a re-sync with the "
                "distribution team. Set expectation: 24-48 hours for it to go live again.",
            ),
        ),
    ),
    TicketCategory.BOOK_STATUS_PRODUCTION: CategoryKnowledge(
        "Book Status & Production Updates",
        PRODUCTION_POLICY,
        (
            Example(
                "It's been 3 weeks and my book is still in typesetting. When will it be done?",
                "Check the actual production status. If it's delayed, be honest about why (e.g. waiting on author "
                "approval for proofs). Provide a specific updated timeline. Don't blame the author even if the delay "
                "is on their side; frame it collaboratively.",
            ),
        ),
    ),
    TicketCategory.GENERAL_INQUIRY: CategoryKnowledge(
        "General Inquiry",
        GENERAL_DIGEST,
        (
            Example(
                "Can I update the description of my book on Amazon after it's already live?",
                "Yes, metadata updates can be submitted through the dashboard or by emailing the BookLeaf team. "
                "Changes typically reflect on platforms within 3-5 business days.",
            ),
        ),
    ),
}


def sections_for(category: TicketCategory | None) -> CategoryKnowledge:
    return KNOWLEDGE[category or TicketCategory.GENERAL_INQUIRY]


def category_label(category: TicketCategory | None) -> str:
    return sections_for(category).label if category else "Unclassified"
