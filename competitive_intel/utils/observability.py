# utils/observability.py
# =============================================
# LangSmith Observability
# =============================================
# LangSmith tracks every LLM call with:
#   - Input prompt
#   - Output response
#   - Latency (how long it took)
#   - Token count (cost estimation)
#   - Quality scores


import os
import time
from dotenv import load_dotenv

load_dotenv()

# Enable LangSmith tracing automatically

LANGSMITH_ENABLED = bool(
    os.getenv("LANGCHAIN_API_KEY") and
    os.getenv("LANGCHAIN_API_KEY") != "your_langsmith_key_here"
)

if LANGSMITH_ENABLED:
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGCHAIN_PROJECT"]    = os.getenv("LANGCHAIN_PROJECT", "CompeteIQ")


class PipelineTrace:
    """
    Tracks a full pipeline run with timing.
    LangSmith tracing happens automatically via LangChain —
    this class just handles per-step latency for the UI.
    """

    def __init__(self, name: str, **metadata):
        self.name       = name
        self.metadata   = metadata
        self.start_time = time.time()
        self.spans      = []


    def score(self, name: str, value: float, comment: str = ""):
        """Log a quality score — stored locally for UI display."""
        self.spans.append({"score": name, "value": value, "comment": comment})
        print(f"  📊 Score [{name}]: {value} — {comment}")

    def finish(self) -> dict:
        """Returns timing summary for display in UI."""
        total = round(time.time() - self.start_time, 2)
        if LANGSMITH_ENABLED:
            print(f"  📡 LangSmith trace saved → https://smith.langchain.com")
        return {
            "total_seconds":      total,
            "steps":              self.spans,
            "langsmith_enabled":  LANGSMITH_ENABLED,
        }




    