import json
import requests
from typing import Dict, Any


OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "qwen3:8b"


SYSTEM_PROMPT = """
You are the Mission Intelligence Officer inside an Antarctic
navigation decision-support system.

Your job is ONLY to explain supplied mission-analysis results.

The navigation system has already calculated:
- route selection
- iceberg exposure
- sea-ice exposure
- minimum separation
- operational hazard levels

You must NOT perform those calculations yourself.

STRICT RULES:

1. Use ONLY the supplied mission data.

2. Never invent measurements, observations, weather conditions,
   iceberg positions, probabilities, or scientific facts.

3. Never call an operational risk level a calibrated collision probability.

4. Treat separation, exposure, and risk levels as decision-support
   indicators, not absolute safety guarantees.

5. Be concise and professional.

6. Do not use marketing language.

7. Do not mention that you are an AI or language model.

8. If information is missing, say so rather than inferring it.

9. Return ONLY valid JSON.

10. Never confuse an iceberg hazard with a route or route option.

11. Never give unconditional navigation instructions such as
    "proceed", "continue", or "safe to navigate".

12. Use decision-support language such as "reassess", "review",
    "monitor", or "consider an alternative".

13. Refer to hazards specifically as "icebergs", "iceberg hazards",
    "route hazards", or "iceberg exposure". Do not use generic terms
    such as "obstacles".

14. Keep every assessment and recommendation directly tied to the
    supplied route metrics, iceberg hazards, sea-ice exposure,
    separation, and risk indicators.

15. Do not claim that a route is safe solely because no hazard was
    detected in the supplied data.

16. When an iceberg hazard is supplied, identify the iceberg by its
    provided ID when relevant. Do not invent an ID.

17. Do not introduce information about environmental conditions,
    vessel capabilities, or navigation constraints that are not
    present in the supplied mission data.

Return exactly:

{
  "summary": "...",
  "assessment": "...",
  "recommendation": "..."
}
"""


def generate_mission_intelligence(
    mission_data: Dict[str, Any],
) -> dict:

    prompt = f"""
{SYSTEM_PROMPT}

MISSION ANALYSIS DATA:

{json.dumps(mission_data, indent=2)}

Generate the concise operational mission brief now.
"""

    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "think": False,
        "format": "json",
        "options": {
            "temperature": 0,
            "num_predict": 180,
        },
    }

    try:
        response = requests.post(
            OLLAMA_URL,
            json=payload,
            timeout=30,
        )

        response.raise_for_status()

        data = response.json()

        content = data.get("response", "").strip()

        if not content:
            raise ValueError("Empty Ollama response")

        result = json.loads(content)

        return {
            "status": "success",
            "summary": result.get("summary", ""),
            "assessment": result.get("assessment", ""),
            "recommendation": result.get("recommendation", ""),
        }

    except Exception as exc:
        return {
            "status": "unavailable",
            "summary": "Mission intelligence unavailable.",
            "assessment": "Structured route analysis remains available.",
            "recommendation": "Use the route assessment and hazard watch.",
            "error": str(exc),
        }