"""
AI service for Groq API integration.
Handles intent extraction, executive summaries, leadership updates,
and executive-friendly data quality messaging.
"""

import json
import logging
import httpx
from typing import Dict, Any, List, Optional
from datetime import datetime

from ..config import get_settings
from ..models.schemas import (
    IntentExtraction,
    MetricType,
    MetricSummary,
    TimeRange,
    DataQualityWarning,
)
from .prompts import PromptTemplates

logger = logging.getLogger(__name__)


class AIServiceError(Exception):
    """Custom exception for AI service errors."""

    def __init__(self, message: str, status_code: int = None, response_data: dict = None):
        super().__init__(message)
        self.status_code = status_code
        self.response_data = response_data


# ---------------------------------------------------------------------------
#  Executive-friendly data quality warning formatter
# ---------------------------------------------------------------------------
_WARNING_TEMPLATES = {
    "deal_value": "About {pct}% of deals ({count} records) don't have a deal value attached — pipeline totals may be understated.",
    "sector": "Roughly {pct}% of records ({count}) are missing sector tags, so sector breakdowns are approximate.",
    "status": "{count} deals have no status set — they're excluded from open/closed ratios.",
    "invoiced_amount": "{count} work orders are missing invoice amounts, which affects revenue and collection figures.",
    "collected_amount": "{count} work orders have no collection data recorded — collection efficiency may appear lower than reality.",
    "close_date": "{count} deals don't have a close date, limiting time-based filtering.",
    "probability": "{count} deals are missing a closure probability, so weighted pipeline can't be computed for those.",
}


def format_warnings_for_executive(
    warnings: List[DataQualityWarning],
    total_deals: int,
    total_work_orders: int,
) -> List[DataQualityWarning]:
    """
    Convert technical data-quality warnings into founder-friendly language.

    Returns a new list of DataQualityWarning with rewritten ``issue`` text.
    Only includes warnings where ≥5% of records are affected.
    """
    formatted: List[DataQualityWarning] = []
    for w in warnings:
        field_key = w.field.lower().replace(" ", "_")
        total = total_deals if field_key in ("deal_value", "sector", "status", "close_date", "probability") else total_work_orders
        if total == 0:
            continue
        pct = round(w.affected_records / total * 100)
        if pct < 5:
            continue  # suppress trivial warnings

        template = _WARNING_TEMPLATES.get(field_key)
        if template:
            friendly_issue = template.format(pct=pct, count=w.affected_records)
        else:
            friendly_issue = f"{pct}% of records ({w.affected_records}) have incomplete {w.field} data."

        severity = "info" if pct < 20 else ("warning" if pct < 50 else "error")
        formatted.append(DataQualityWarning(
            field=w.field,
            issue=friendly_issue,
            affected_records=w.affected_records,
            severity=severity,
            details=w.details,
        ))
    return formatted


class AIService:
    """
    AI service for Groq API integration.

    Handles:
    - Intent extraction from natural language queries
    - Executive summary generation from computed metrics
    - Leadership update generation (structured briefing)
    - Follow-up question suggestion
    - Clarification prompt generation for ambiguous queries
    """

    def __init__(self, api_key: str = None, model: str = None):
        settings = get_settings()
        self.api_key = api_key or settings.GROQ_API_KEY
        self.model = model or settings.GROQ_MODEL
        self.api_url = "https://api.groq.com/openai/v1/chat/completions"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    # ------------------------------------------------------------------
    #  Core Groq API call
    # ------------------------------------------------------------------
    async def _call_groq(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.3,
        max_tokens: int = 1024,
    ) -> str:
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                response = await client.post(self.api_url, headers=self.headers, json=payload)
                response.raise_for_status()
                data = response.json()
                choices = data.get("choices", [])
                if not choices:
                    raise AIServiceError("No response from Groq API")
                return choices[0].get("message", {}).get("content", "")
            except httpx.HTTPStatusError as e:
                logger.error(f"HTTP error from Groq API: {e}")
                raise AIServiceError(f"Groq API error: {e.response.status_code}", status_code=e.response.status_code)
            except httpx.RequestError as e:
                logger.error(f"Request error to Groq API: {e}")
                raise AIServiceError(f"Request failed: {str(e)}")
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse Groq API response: {e}")
                raise AIServiceError("Invalid JSON response from Groq API")

    # ------------------------------------------------------------------
    #  JSON extraction helper
    # ------------------------------------------------------------------
    def _parse_intent_json(self, response: str) -> Dict[str, Any]:
        response = response.strip()
        if response.startswith("```json"):
            response = response[7:]
        elif response.startswith("```"):
            response = response[3:]
        if response.endswith("```"):
            response = response[:-3]
        response = response.strip()
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            start = response.find("{")
            end = response.rfind("}") + 1
            if start >= 0 and end > start:
                try:
                    return json.loads(response[start:end])
                except json.JSONDecodeError:
                    pass
            logger.warning(f"Failed to parse intent JSON: {response[:200]}")
            return {
                "sector": None,
                "time_range": None,
                "metric_type": "general",
                "entities": [],
                "confidence": 0.5,
                "requires_clarification": True,
                "clarification_prompt": "I couldn't fully understand your question. Could you rephrase it?",
            }

    # ------------------------------------------------------------------
    #  Intent extraction
    # ------------------------------------------------------------------
    async def extract_intent(
        self,
        query: str,
        available_sectors: List[str] = None,
    ) -> IntentExtraction:
        prompt = PromptTemplates.INTENT_EXTRACTION.format(
            query=query,
            available_sectors=", ".join(available_sectors or ["unknown"]),
        )
        messages = [
            {"role": "system", "content": "You are a business intelligence intent extraction system. Respond only with valid JSON."},
            {"role": "user", "content": prompt},
        ]
        response = await self._call_groq(messages, temperature=0.1)
        parsed = self._parse_intent_json(response)

        # Build TimeRange
        time_range = None
        if parsed.get("time_range"):
            tr = parsed["time_range"]
            time_range = TimeRange(
                start_date=datetime.fromisoformat(tr["start_date"]) if tr.get("start_date") else None,
                end_date=datetime.fromisoformat(tr["end_date"]) if tr.get("end_date") else None,
                period=tr.get("period"),
            )

        # Map metric type
        metric_type_str = parsed.get("metric_type", "general").lower()
        try:
            metric_type = MetricType(metric_type_str)
        except ValueError:
            metric_type = MetricType.GENERAL

        return IntentExtraction(
            sector=parsed.get("sector"),
            time_range=time_range,
            metric_type=metric_type,
            entities=parsed.get("entities", []),
            confidence=parsed.get("confidence", 0.5),
            requires_clarification=parsed.get("requires_clarification", False),
            clarification_prompt=parsed.get("clarification_prompt"),
            raw_query=query,
        )

    # ------------------------------------------------------------------
    #  Executive summary (standard questions)
    # ------------------------------------------------------------------
    async def generate_executive_summary(
        self,
        question: str,
        metrics: List[MetricSummary],
        summary_stats: Dict[str, Any],
        data_quality_warnings: List[DataQualityWarning] = None,
    ) -> str:
        metrics_json = json.dumps(
            [{"name": m.name, "value": str(m.value), "formatted": m.formatted_value, "description": m.description} for m in metrics],
            indent=2,
        )
        if data_quality_warnings:
            data_quality_notes = "\n".join(
                [f"- {w.issue}" for w in data_quality_warnings]
            )
        else:
            data_quality_notes = "No significant data quality issues."

        prompt = PromptTemplates.EXECUTIVE_SUMMARY.format(
            question=question,
            metrics_json=metrics_json,
            data_quality_notes=data_quality_notes,
            summary_stats=json.dumps(summary_stats, indent=2),
        )
        messages = [
            {"role": "system", "content": "You are SkyLark's senior business analyst. Respond directly to the founder — concise, opinionated, in Indian Rupees."},
            {"role": "user", "content": prompt},
        ]
        response = await self._call_groq(messages, temperature=0.5, max_tokens=1024)
        return response.strip()

    # ------------------------------------------------------------------
    #  Leadership update (structured briefing)
    # ------------------------------------------------------------------
    async def generate_leadership_update(
        self,
        metrics: List[MetricSummary],
        summary_stats: Dict[str, Any],
        data_quality_warnings: List[DataQualityWarning] = None,
    ) -> str:
        metrics_json = json.dumps(
            [{"name": m.name, "value": str(m.value), "formatted": m.formatted_value, "description": m.description} for m in metrics],
            indent=2,
        )
        if data_quality_warnings:
            data_quality_notes = "\n".join(
                [f"- {w.issue}" for w in data_quality_warnings]
            )
        else:
            data_quality_notes = "No significant data quality issues."

        prompt = PromptTemplates.LEADERSHIP_UPDATE.format(
            metrics_json=metrics_json,
            summary_stats=json.dumps(summary_stats, indent=2),
            data_quality_notes=data_quality_notes,
        )
        messages = [
            {"role": "system", "content": "You are SkyLark's Chief of Staff preparing a leadership briefing. Be direct, specific, and opinionated. Use ₹ Cr / ₹ L."},
            {"role": "user", "content": prompt},
        ]
        response = await self._call_groq(messages, temperature=0.4, max_tokens=1500)
        return response.strip()

    # ------------------------------------------------------------------
    #  Follow-up suggestions
    # ------------------------------------------------------------------
    async def generate_follow_up_suggestions(
        self,
        question: str,
        metric_type: str,
        available_sectors: List[str] = None,
    ) -> List[str]:
        prompt = PromptTemplates.FOLLOW_UP_SUGGESTIONS.format(
            question=question,
            metric_type=metric_type,
            available_sectors=", ".join(available_sectors or []),
        )
        messages = [
            {"role": "system", "content": "Respond with only a JSON array of 3 strings."},
            {"role": "user", "content": prompt},
        ]
        try:
            response = await self._call_groq(messages, temperature=0.7, max_tokens=256)
            response = response.strip()
            # Strip markdown fences
            if response.startswith("```"):
                response = response.split("\n", 1)[-1]
            if response.endswith("```"):
                response = response[:-3].strip()
            suggestions = json.loads(response)
            if isinstance(suggestions, list) and all(isinstance(s, str) for s in suggestions):
                return suggestions[:3]
        except Exception as e:
            logger.warning(f"Failed to generate follow-up suggestions: {e}")
        return []

    # ------------------------------------------------------------------
    #  Clarification
    # ------------------------------------------------------------------
    async def generate_clarification(
        self,
        question: str,
        ambiguity_reason: str,
        available_options: List[str] = None,
    ) -> str:
        prompt = PromptTemplates.CLARIFICATION_RESPONSE.format(
            question=question,
            ambiguity_reason=ambiguity_reason,
            available_options=", ".join(available_options or []),
        )
        messages = [
            {"role": "system", "content": "You are SkyLark's business intelligence assistant. Be friendly and specific."},
            {"role": "user", "content": prompt},
        ]
        response = await self._call_groq(messages, temperature=0.7, max_tokens=256)
        return response.strip()
