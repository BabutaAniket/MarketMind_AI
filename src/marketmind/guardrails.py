"""MarketMind AI - input and output guardrails.

check_input() blocks requests in these risk categories: prompt_injection,
secret_disclosure, auto_publish, unauthorised_messaging, private_data,
fabricated_proof, unsupported_claim, false_urgency, unapproved_warranty,
source_tampering. It also redacts emails and Indian phone numbers.
check_output() flags forbidden claim phrases in generated drafts.

Used by: orchestrator, evaluation, the API, agents and tests.
"""

from __future__ import annotations

import re

INJECTION_PATTERNS = [
    r"ignore\s+(all|previous|earlier)\s+instructions",
    r"system\s*:\s*",
    r"reveal\s+(the\s+)?prompt",
    r"print\s+(the\s+)?api\s*key",
    r"send\s+everything\s+to",
]

_ANY = r"[^.?!\n]{0,60}"

RISK_PATTERNS: dict[str, list[str]] = {
    "prompt_injection": [
        r"\b(ignore|forget|disregard|override|bypass|skip)\b"
        + _ANY
        + r"\b(instructions?|rules?|guidelines?|polic(y|ies)|guardrails?|restrictions?|safety|checks?)\b",
        r"\bsystem\s*:",
        r"\b(new|updated|real)\s+(system\s+)?(instruction|prompt|rules?)\b",
        r"\b(treat|use)\b" + _ANY + r"\bas\s+(a\s+|the\s+)?(new\s+)?(system\s+)?(instruction|prompt|command)s?\b",
        r"\byou\s+are\s+now\b",
        r"\b(developer|admin|god|dan|jailbreak)\s+mode\b",
        r"\bjailbreak\b",
        r"\bpretend\s+(you\s+)?(have\s+no|there\s+are\s+no)\s+(rules|restrictions)\b",
    ],
    "secret_disclosure": [
        r"\b(api|secret|access|private)[\s_-]*keys?\b",
        r"\b(passwords?|passwd|credentials?|auth\s*tokens?|access\s*tokens?|bearer\s+token)\b",
        r"\.env\b",
        r"\b(system|hidden|internal)\s+(prompt|instructions?)\b",
        r"\b(reveal|show|print|dump|leak|share)\b" + _ANY + r"\b(prompt|config(uration)?|settings\s+file|secrets?)\b",
    ],
    "auto_publish": [
        r"\b(auto[\s-]?publish|auto[\s-]?post)\w*",
        r"\b(publish|post|upload|schedule|go\s+live|push\s+live)\w*\b"
        + _ANY
        + r"\b(directly|automatically|immediately|right\s+away|without\s+(any\s+)?(approval|review|checking|asking|permission|human))\b",
        r"\b(skip|bypass|avoid|no\s+need\s+(for|of)|don'?t\s+(wait\s+for|need))\b"
        + _ANY
        + r"\b(approval|review|reviewer|manager|human|sign[\s-]?off)\b",
    ],
    "unauthorised_messaging": [
        r"\b(send|blast|broadcast|forward|message|whatsapp|sms|text|e-?mail|mail)\w*\b"
        + _ANY
        + r"\b(all|every|entire|whole|full)\b"
        + _ANY
        + r"\b(contacts?|customers?|clients?|leads?|numbers?|list|database|crm|dealers?)\b",
        r"\bbulk\s+(messages?|sms|whatsapp|e-?mails?|texts?)\b",
        r"\bwithout\s+(their\s+|the\s+)?(consent|permission|opt[\s-]?in)\b",
        r"\bspam\w*\b",
        r"\bsend\s+everything\s+to\b",
    ],
    "private_data": [
        r"\b(customer|client|lead|dealer|user|buyer)s?'?\s+(list|data|database|details|records|contacts?|phone|mobile|numbers?|e-?mails?|addresses|names)\b",
        r"\b(phone|mobile|contact)\s+numbers?\s+of\s+(our\s+|the\s+|all\s+)?(customers?|clients?|leads?|dealers?|buyers?)\b",
        r"\b(aadhaar|aadhar|pan\s+(card|number)|bank\s+(details|account)|personal\s+(data|details|information))\b",
        r"\bcrm\s+(data|export|list|records)\b",
    ],
    "fabricated_proof": [
        r"\b(fake|made[\s-]?up|invent\w*|fabricat\w*|make\s+up|dummy|fictional|imaginary|cook\s+up)\b"
        + _ANY
        + r"\b(reviews?|testimonials?|customers?|ratings?|certificates?|certifications?|awards?|data|numbers?|stat(istic)?s?|quotes?|case\s+stud(y|ies)|clients?|endorsements?)\b",
        r"\b(reviews?|testimonials?|quotes?|ratings?)\b"
        + _ANY
        + r"\b(fake|made[\s-]?up|invent\w*|fabricat\w*|make\s+(one|them|it)\s+up)\b",
        r"\b(certified|certification|iso|bis|bee|isi|approved|award)\w*\b"
        + _ANY
        + r"\b(even\s+though|although|though|even\s+if|not\s+yet|don'?t\s+have|do\s+not\s+have|haven'?t|without\s+(a\s+|any\s+)?(certificate|proof))\b",
        r"\b(even\s+though|although|even\s+if)\b"
        + _ANY
        + r"\b(not|n't|never|no)\b"
        + _ANY
        + r"\b(certified|certificate|approved|award|customers?)\b",
    ],
    "unsupported_claim": [
        r"\bguarantee\w*\b"
        + _ANY
        + r"\b(sav\w*|returns?|roi|profit|results?|reduction|bills?|payback|performance|cooling|efficiency)\b",
        r"\b\d{2,3}\s?%\s*(sav\w*|cheaper|less|reduction|lower|cut|roi|returns?|off\s+(your\s+)?bills?)",
        r"\b(zero|no|nil)\s+(electricity|power|current)\s+bills?\b",
        r"\bfree\s+electricity\b",
        r"\b(double|triple|10x)\s+(your\s+)?(money|returns?|roi|savings?)\b",
        r"\b(without|no)\s+(any\s+)?(proof|evidence|data|verification|source|test\s+report)\b",
        r"\b(unverified|not\s+verified|unproven)\b",
        r"\b(cures?|prevents?|heals?)\b" + _ANY + r"\b(disease|asthma|allergy|illness|covid|infection)\b",
        r"\b(best|no\.?\s*1|number\s+one|#1|cheapest)\b(\s+[\w-]+){0,3}\s+(in\s+india|in\s+the\s+world|in\s+the\s+market)\b",
    ],
    "false_urgency": [
        r"(?<!no\s)(?<!avoid\s)(?<!without\s)(?<!not\s)\b(fake|false|artificial|create\s+(a\s+)?(sense\s+of\s+)?)\s*(urgency|scarcity|deadline)\b",
        r"\bonly\s+\d+\s+(units?|pieces?|pcs|slots?|seats?|left|remaining)\b",
        r"\b(offer|sale|deal|discount|price)\s+(ends|expires|ending|closes)\s+(today|tonight|now|in\s+\d+\s+(hours?|minutes?|mins?))\b",
        r"\b(last\s+chance|hurry\s+up|act\s+now|before\s+it'?s\s+too\s+late)\b",
        r"\bprices?\s+(will\s+)?(go|going)\s+up\s+(tomorrow|tonight|today|soon)\b",
    ],
    "unapproved_warranty": [
        r"\b(lifetime|life[\s-]?long|\d{1,2}[\s-]?(year|yr)s?)\s+(free\s+)?(warranty|guarantee)\b",
        r"\b(warranty|guarantee)\s+(for\s+)?(life|lifetime|\d{1,2}\s+(years?|yrs?))\b",
        r"\bfree\s+(service|maintenance|servicing|installation|replacement)\s+(for\s+life|forever|lifetime|for\s+\d+\s+years?)\b",
        r"\b(promise|offer|add|mention|say|write)\w*\b"
        + _ANY
        + r"\bwarranty\b"
        + _ANY
        + r"\b(not\s+approved|unapproved|even\s+though|extra|extended)\b",
    ],
    "source_tampering": [
        r"\b(change|edit|modify|alter|replace|overwrite|delete|tamper|rewrite|fake)\w*\b"
        + _ANY
        + r"\b(sources?|references?|citations?|knowledge\s+base|website\s+(text|content|data)|data_input|datasheets?|campaign_plan|audit\s+logs?|logs?|records?|evidence)\b",
        r"\b(remove|hide|drop|delete|skip)\w*\s+(the\s+|all\s+)?(sources?|citations?|disclaimers?|terms|conditions|footnotes?)\b",
    ],
}

_COMPILED = {category: [re.compile(p, re.IGNORECASE) for p in patterns] for category, patterns in RISK_PATTERNS.items()}


def detect_injection(text: str) -> list[str]:
    lowered = text.lower()
    return [pattern for pattern in INJECTION_PATTERNS if re.search(pattern, lowered)]


def detect_risks(text: str) -> dict[str, list[str]]:
    hits: dict[str, list[str]] = {}
    for category, patterns in _COMPILED.items():
        for pattern in patterns:
            match = pattern.search(text)
            if match:
                hits.setdefault(category, []).append(match.group(0).strip())
    return hits


def redact_pii(text: str) -> str:
    text = re.sub(r"[\w.+-]+@[\w-]+\.[\w.-]+", "[EMAIL_REDACTED]", text)
    text = re.sub(r"(?<!\d)(?:\+?91[-\s]?)?[6-9]\d{9}(?!\d)", "[PHONE_REDACTED]", text)
    return text


def check_input(text: str) -> dict:
    injection = detect_injection(text)
    risks = detect_risks(text)
    return {
        "allowed": not injection and not risks,
        "injection_patterns": injection,
        "risk_categories": sorted(risks),
        "risk_matches": risks,
        "redacted_text": redact_pii(text),
    }


OUTPUT_FORBIDDEN = [
    "guaranteed return",
    "guaranteed saving",
    "guaranteed savings",
    "100% saving",
    "zero electricity bill",
    "free electricity",
    "lifetime warranty",
    "publish automatically",
    "secret api key",
]


def check_output(text: str) -> dict:
    lowered = text.lower()
    hits = [phrase for phrase in OUTPUT_FORBIDDEN if phrase in lowered]
    return {"allowed": not hits, "claim_or_safety_hits": hits}
