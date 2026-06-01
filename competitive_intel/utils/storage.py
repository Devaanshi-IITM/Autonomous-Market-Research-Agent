# utils/storage.py
# Persists past briefs to disk so they survive page refreshes

import json
import os
from datetime import datetime

BRIEFS_FILE = "./briefs_history.json"


def save_brief(title: str, result: dict):
    """Save a brief to disk."""
    briefs = load_briefs()
    briefs.insert(0, {
        "title": title,
        "timestamp": datetime.now().isoformat(),
        "result": {
            "final_brief":   result.get("final_brief", ""),
            "scores_data":   result.get("scores_data", ""),
            "analysis_data": result.get("analysis_data", ""),
            "scraped_data":  result.get("scraped_data", ""),
            "history":       result.get("history", []),
            "timings":       result.get("timings", {}),
            "eval_scores":   result.get("eval_scores", {}),
            "total_time":    result.get("total_time", 0),
        }
    })
    # Keep only last 20 briefs
    briefs = briefs[:20]
    with open(BRIEFS_FILE, "w") as f:
        json.dump(briefs, f, indent=2)


def load_briefs() -> list:
    """Load briefs from disk."""
    if not os.path.exists(BRIEFS_FILE):
        return []
    try:
        with open(BRIEFS_FILE) as f:
            return json.load(f)
    except Exception:
        return []


def clear_briefs():
    """Delete all saved briefs."""
    if os.path.exists(BRIEFS_FILE):
        os.remove(BRIEFS_FILE)