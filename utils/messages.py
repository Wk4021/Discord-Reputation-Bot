"""Loads the categorized flavour messages shown on the review panel."""
from utils.config import PROJECT_ROOT


def load_rep_messages():
    cats = {"good": [], "neutral": [], "bad": []}
    try:
        with open(PROJECT_ROOT / "assets" / "rep_messages.txt", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "|" in line:
                    cat, msg = line.split("|", 1)
                    cat = cat.strip().lower()
                    msg = msg.strip()
                    if cat in cats:
                        cats[cat].append(msg)
    except FileNotFoundError:
        # fallback to a minimal set
        cats["neutral"].append("No rep data…")
    return cats
