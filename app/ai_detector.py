import re

SCAM_PATTERNS = [
    r"\\b(pin|password|otp|one[- ]time password)\\b",
    r"\\b(approve|confirm|authori[sz]e)\\b.*\\b(payment|transaction|beneficiar(y|ies)|transfer)\\b",
    r"\\b(send|transfer|move)\\b.*\\b(money|funds)\\b",
    r"\\b(remote access|anydesk|teamviewer)\\b",
    r"\\b(bank|fraud) department\\b",
]

COERCION_PATTERNS = [
    r"\\b(do it now|right now|immediately)\\b",
    r"\\b(if you don't|if you do not)\\b.*\\b(lock|close|freeze|arrest|lose)\\b",
    r"\\b(don't tell|do not tell)\\b.*\\b(anyone|the bank|your family)\\b",
    r"\\b(you must|you have to)\\b",
]

def analyze_transcript(text: str) -> dict:
    normalized = text.lower()
    scam_hits = [p for p in SCAM_PATTERNS if re.search(p, normalized)]
    coercion_hits = [p for p in COERCION_PATTERNS if re.search(p, normalized)]
    scam_score = min(1.0, len(scam_hits) * 0.24)
    coercion_score = min(1.0, len(coercion_hits) * 0.30)
    return {
        "scam_risk": round(scam_score, 2),
        "coercion_risk": round(coercion_score, 2),
        "matched_scam_signals": len(scam_hits),
        "matched_coercion_signals": len(coercion_hits),
        "analysis_mode": "demo_heuristic"
    }
