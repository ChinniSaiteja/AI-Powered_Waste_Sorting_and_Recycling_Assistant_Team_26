"""
Demo for the AI part - Subsystem 4 (Ha Le Thu)
Run:  python demo_ai_guidance.py
Without an API key it shows the fallback; with AI_API_KEY in .env it calls the AI.
"""

from database.db import DatabaseManager
from database.guidance import GuidanceService

db = DatabaseManager()
db.initialize()
service = GuidanceService(db)
print(f"AI enabled: {service.ai_enabled} | model: {service.model} | daily limit: {service.daily_limit}\n")

for label in ("glass jar", "glass jar", "battery", "rubber duck"):
    result = service.explain(label)
    print(f"[{result['source']:8}] {label}: {result['explanation']}")
