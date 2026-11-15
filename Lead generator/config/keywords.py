"""
High-intent keyword dictionaries and negative filters for lead ingestion.
Ensures zero wasted Gemini API calls by pre-filtering noise.
"""

# Phrases indicating a buyer / client looking for technical help
HIGH_INTENT_KEYWORDS = [
    # Explicit hiring intent
    "need a website",
    "need a web developer",
    "need a developer",
    "looking for a web developer",
    "looking for a developer",
    "looking for web development",
    "looking for a coder",
    "looking for a programmer",
    "hiring a web developer",
    "hiring a developer",
    "hiring a programmer",
    "recommend an agency",
    "recommend a web developer",
    "recommend a developer",
    "agency recommendation",
    
    # Redesign & modernization
    "website redesign",
    "redesign my website",
    "redesign our website",
    "rebuild our website",
    "rebuild my website",
    "revamp my website",
    "upgrade my website",
    "fix my website",
    "improve my website",
    
    # Web application & MVP
    "build a web app",
    "build an mvp",
    "need an mvp",
    "looking for an agency to build",
    "need someone to build",
    "hire someone to build",
    "looking to hire a developer",
    "looking to build a platform",
    "custom web application",
    "saas development",
    
    # E-commerce & Landing pages
    "new ecommerce store",
    "build an online store",
    "shopify developer needed",
    "shopify redesign",
    "landing page needed",
    "need a landing page",
    
    # AI agents / tools
    "build an ai agent",
    "need an ai tool",
    "custom ai integration",
    "automate my workflow",
    "build a bot",
]

# Phrases indicating freelancers/agencies pitching their OWN services (Spam / Competitors)
NEGATIVE_KEYWORDS = [
    "[for hire]",
    "for hire",
    "i will build",
    "hire me",
    "i am a web developer",
    "i am a freelance",
    "my portfolio",
    "check out my portfolio",
    "my rates start at",
    "offering web development",
    "available for hire",
    "looking for work",
    "dm me for portfolio",
    "i can do this for you",
]

# Flairs to prioritize (e.g. r/forhire, r/freelance)
RELEVANT_FLAIRS = {
    "positive": ["hiring", "job", "request", "help", "advice", "question"],
    "negative": ["for hire", "offer", "meta", "promo"],
}
