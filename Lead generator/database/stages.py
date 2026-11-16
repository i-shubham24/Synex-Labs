"""Pipeline stages shared by prospects (Maps) and leads (social / website)."""

OPEN = ("new", "alerted")
ACTIVE = ("contacted", "replied", "call_booked", "proposal_sent")
POSITIVE = ("replied", "call_booked", "proposal_sent", "won")
CLOSED = ("won", "lost", "no_response", "not_interested", "skipped", "ignored")

PROSPECT_STAGES = OPEN + ACTIVE + CLOSED
LEAD_STAGES = OPEN + ACTIVE + ("won", "lost", "no_response", "not_interested", "ignored", "disqualified")

LABELS = {
    "new": "New",
    "alerted": "Sent to Telegram",
    "contacted": "Contacted",
    "replied": "Replied",
    "call_booked": "Call booked",
    "proposal_sent": "Proposal sent",
    "won": "Won",
    "lost": "Lost",
    "no_response": "No response",
    "not_interested": "Not interested",
    "skipped": "Skipped",
    "ignored": "Ignored",
    "disqualified": "Disqualified",
}
