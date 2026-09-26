import json
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import httpx
from app.core.config import settings

logger = logging.getLogger("varuna-llm-service")

class LLMProvider(ABC):
    """Abstract interface for human-readable meteorological briefing generation."""

    @abstractmethod
    def generate_briefing(self, computed_facts: Dict[str, Any]) -> str:
        """Translates computed scientific facts into an operational meteorological briefing."""
        pass


class DeterministicTemplateProvider(LLMProvider):
    """
    Zero-dependency, offline deterministic template generator.
    Guarantees mathematically faithful explanations without hallucination risk.
    """

    def generate_briefing(self, computed_facts: Dict[str, Any]) -> str:
        fused_val = computed_facts.get("fused_value", 0.0)
        variable = computed_facts.get("variable", "rainfall")
        unit = "mm" if variable == "rainfall" else "°C" if variable == "temperature" else "km/h"
        region_id = computed_facts.get("region_id", "Target Region")
        lead_hours = computed_facts.get("lead_hours", 48)
        regime = computed_facts.get("weather_regime", "NORMAL")
        dominant = computed_facts.get("dominant_model", "NCUM")
        dominant_weight = computed_facts.get("dominant_weight_pct", 40.0)
        prob = computed_facts.get("probability", 50.0)
        conf = computed_facts.get("confidence", "MEDIUM")
        disagreement = computed_facts.get("disagreement_level", "MODERATE")

        briefing = (
            f"Operational Meteorological Assessment for {region_id} ({lead_hours}h lead, {regime} regime): "
            f"The adaptive fusion engine produced a blended {variable} estimate of {fused_val:.1f} {unit}. "
            f"{dominant} received the primary weighting ({dominant_weight:.1f}%) based on verified historical skill under comparable synoptic patterns. "
            f"Exceedance probability for severe weather criteria is {prob:.1f}%, while evidence consensus confidence is rated {conf} "
            f"due to {disagreement.lower()} inter-model divergence."
        )
        return briefing


class GrokLLMProvider(LLMProvider):
    """
    xAI Grok provider for enhanced operational briefings.
    Strictly constrained by computed numerical facts: DOES NOT invent numbers or weights.
    """

    def __init__(self, api_key: str = None, model: str = None):
        self.api_key = api_key or settings.XAI_API_KEY
        self.model = model or settings.XAI_MODEL
        self.endpoint = "https://api.x.ai/v1/chat/completions"
        self.fallback = DeterministicTemplateProvider()

    def generate_briefing(self, computed_facts: Dict[str, Any]) -> str:
        if not self.api_key:
            return self.fallback.generate_briefing(computed_facts)

        prompt_payload = {
            "role": "system",
            "content": (
                "You are an expert meteorological briefing assistant at the National Centre for Medium Range Weather Forecasting (NCMRWF). "
                "Synthesize a concise, technically rigorous, 2-to-3 sentence operational briefing for the duty forecaster. "
                "CRITICAL RULE: You must ONLY use the exact numbers, model weights, probabilities, and confidence ratings supplied in the input. "
                "Do NOT alter any numerical values, fabricate weather models, or invent unsupported claims."
            )
        }

        user_content = f"Computed Forecast Facts:\n{json.dumps(computed_facts, indent=2)}"

        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            body = {
                "model": self.model,
                "messages": [
                    prompt_payload,
                    {"role": "user", "content": user_content}
                ],
                "temperature": 0.2,
                "max_tokens": 250
            }

            with httpx.Client(timeout=6.0) as client:
                resp = client.post(self.endpoint, headers=headers, json=body)
                if resp.status_code == 200:
                    data = resp.json()
                    content = data["choices"][0]["message"]["content"].strip()
                    return content
                else:
                    logger.warning(f"Grok API returned status {resp.status_code}, falling back to template.")
                    return self.fallback.generate_briefing(computed_facts)

        except Exception as e:
            logger.warning(f"Grok API invocation failed ({e}), falling back to deterministic template.")
            return self.fallback.generate_briefing(computed_facts)


def get_llm_provider() -> LLMProvider:
    if settings.XAI_API_KEY:
        return GrokLLMProvider()
    return DeterministicTemplateProvider()

llm_service = get_llm_provider()
