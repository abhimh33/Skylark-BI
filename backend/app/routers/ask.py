"""
API router for the /ask endpoint.
"""

import time
import logging
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends

from ..models.schemas import (
    AskRequest,
    AskResponse,
    ErrorResponse,
    DataQualityWarning,
    MetricType,
    IntentExtraction,
)
from ..monday_client import MondayClient
from ..data_cleaner import DataCleaner
from ..business_logic import MetricsEngine
from ..ai_service import AIService
from ..ai_service.service import format_warnings_for_executive
from ..cache import board_cache, response_cache, make_response_key, BOARD_DATA_KEY
from ..config import get_settings
from ..dependencies import (
    get_monday_client,
    get_data_cleaner,
    get_ai_service,
)

logger = logging.getLogger(__name__)

router = APIRouter()


# ------------------------------------------------------------------
#  Helper: fetch board data (with cache)
# ------------------------------------------------------------------
async def _get_boards_data(
    monday_client: MondayClient,
    data_cleaner: DataCleaner,
) -> tuple[dict, bool]:
    """
    Return (boards_data_dict, from_cache).

    Checks ``board_cache`` first; on miss, fetches live from monday.com,
    cleans the data, and stores the result.
    """
    settings = get_settings()
    cached = board_cache.get(BOARD_DATA_KEY)
    if cached is not None:
        logger.info("Board data served from cache")
        return cached, True

    boards_data = await monday_client.get_all_boards_data()
    board_cache.set(BOARD_DATA_KEY, boards_data, ttl=settings.CACHE_BOARD_TTL)
    logger.info("Board data fetched live & cached")
    return boards_data, False


@router.post(
    "/ask",
    response_model=AskResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Bad request"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
        503: {"model": ErrorResponse, "description": "Service unavailable"},
    },
    summary="Ask a business intelligence question",
    description="Accepts a natural language business question and returns executive-level insights with key metrics.",
)
async def ask_question(
    request: AskRequest,
    monday_client: MondayClient = Depends(get_monday_client),
    data_cleaner: DataCleaner = Depends(get_data_cleaner),
    ai_service: AIService = Depends(get_ai_service),
) -> AskResponse:
    """
    Process a natural language business question.

    Pipeline:
    1. Fetch data from monday.com boards
    2. Clean and normalize data
    3. Extract structured intent via Groq
    4. Compute relevant metrics
    5. Generate executive summary / leadership update via Groq
    6. Format warnings for executive audience
    7. Generate follow-up suggestions
    8. Return structured response
    """
    start_time = time.time()
    settings = get_settings()

    # ----- Check response cache first -----
    cache_key = make_response_key(request.question)
    cached_response = response_cache.get(cache_key)
    if cached_response is not None:
        processing_time = int((time.time() - start_time) * 1000)
        cached_response.processing_time_ms = processing_time
        cached_response.source = "cache"
        logger.info(f"Response served from cache in {processing_time}ms (key={cache_key})")
        return cached_response

    try:
        # ----- Step 1: Fetch data (board cache) -----
        logger.info(f"Processing question: {request.question[:100]}...")
        try:
            boards_data, board_from_cache = await _get_boards_data(monday_client, data_cleaner)
        except Exception as e:
            logger.error(f"Failed to fetch monday.com data: {e}")
            raise HTTPException(
                status_code=503,
                detail={"error": "Failed to fetch data from monday.com", "detail": str(e), "code": "MONDAY_API_ERROR"},
            )

        # ----- Step 2: Clean data -----
        logger.info("Cleaning board data...")
        board_data = data_cleaner.clean_board_data(
            deals_raw=boards_data["deals"]["items"],
            work_orders_raw=boards_data["work_orders"]["items"],
        )

        # ----- Step 3: Initialize metrics engine & get stats -----
        metrics_engine = MetricsEngine(board_data)
        summary_stats = metrics_engine.get_summary_stats()
        available_sectors = summary_stats.get("unique_sectors", [])

        # ----- Step 4: Extract intent -----
        logger.info("Extracting intent from question...")
        try:
            intent = await ai_service.extract_intent(
                query=request.question,
                available_sectors=available_sectors,
            )
        except Exception as e:
            logger.error(f"Failed to extract intent: {e}")
            intent = IntentExtraction(
                metric_type=MetricType.GENERAL,
                confidence=0.5,
                raw_query=request.question,
            )

        # ----- Step 5: Format warnings for executive audience -----
        exec_warnings = format_warnings_for_executive(
            warnings=board_data.warnings,
            total_deals=len(board_data.deals),
            total_work_orders=len(board_data.work_orders),
        )

        # ----- Step 6: Handle clarification -----
        if intent.requires_clarification and intent.clarification_prompt:
            processing_time = int((time.time() - start_time) * 1000)
            return AskResponse(
                insights=intent.clarification_prompt,
                key_metrics=[],
                data_quality_warnings=exec_warnings,
                intent=intent,
                confidence=intent.confidence,
                requires_clarification=True,
                clarification_prompt=intent.clarification_prompt,
                suggested_questions=[
                    "What's our total pipeline value?",
                    "Give me a leadership update",
                    "Show collection efficiency",
                ],
                processing_time_ms=processing_time,
            )

        # ----- Step 7: Compute metrics -----
        logger.info(f"Computing metrics for type: {intent.metric_type}")
        metrics = metrics_engine.compute_metrics_for_intent(
            metric_type=intent.metric_type,
            sector=intent.sector,
            time_range=intent.time_range,
        )

        # ----- Step 8: Generate insights -----
        logger.info("Generating insights...")
        try:
            if intent.metric_type == MetricType.LEADERSHIP_UPDATE:
                insights = await ai_service.generate_leadership_update(
                    metrics=metrics,
                    summary_stats=summary_stats,
                    data_quality_warnings=exec_warnings,
                )
            else:
                insights = await ai_service.generate_executive_summary(
                    question=request.question,
                    metrics=metrics,
                    summary_stats=summary_stats,
                    data_quality_warnings=exec_warnings,
                )
        except Exception as e:
            logger.error(f"Failed to generate summary: {e}")
            insights = "Here's what the numbers show:\n\n"
            for metric in metrics:
                insights += f"**{metric.description}:** {metric.formatted_value}\n\n"

        # ----- Step 9: Generate follow-up suggestions -----
        suggested_questions: list[str] = []
        try:
            suggested_questions = await ai_service.generate_follow_up_suggestions(
                question=request.question,
                metric_type=intent.metric_type.value,
                available_sectors=available_sectors,
            )
        except Exception as e:
            logger.warning(f"Failed to generate suggestions: {e}")

        # ----- Step 10: Build response -----
        processing_time = int((time.time() - start_time) * 1000)
        data_source = "cache" if board_from_cache else "live"

        response = AskResponse(
            insights=insights,
            key_metrics=metrics,
            data_quality_warnings=exec_warnings,
            intent=intent,
            confidence=intent.confidence,
            requires_clarification=False,
            suggested_questions=suggested_questions,
            source=data_source,
            processing_time_ms=processing_time,
        )

        if request.include_raw_data:
            response.raw_data = {
                "deals_count": len(board_data.deals),
                "work_orders_count": len(board_data.work_orders),
                "summary_stats": summary_stats,
                "fetched_at": boards_data["fetched_at"],
            }

        # Store full response in cache for identical future questions
        response_cache.set(cache_key, response.model_copy(), ttl=settings.CACHE_RESPONSE_TTL)

        logger.info(f"Request completed in {processing_time}ms (source={data_source})")
        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Unexpected error processing request: {e}")
        raise HTTPException(
            status_code=500,
            detail={"error": "Internal server error", "detail": str(e), "code": "INTERNAL_ERROR"},
        )


@router.get(
    "/health",
    summary="Health check endpoint",
    description="Returns the health status of the API.",
)
async def health_check() -> Dict[str, Any]:
    """Check API health status."""
    return {
        "status": "healthy",
        "timestamp": time.time()
    }


@router.get(
    "/boards/summary",
    summary="Get boards summary",
    description="Fetch and return summary information about the connected monday.com boards.",
)
async def get_boards_summary(
    monday_client: MondayClient = Depends(get_monday_client),
    data_cleaner: DataCleaner = Depends(get_data_cleaner),
) -> Dict[str, Any]:
    """
    Get summary information about the connected boards.
    
    Useful for debugging and verifying data connectivity.
    """
    try:
        boards_data, from_cache = await _get_boards_data(monday_client, data_cleaner)
        
        board_data = data_cleaner.clean_board_data(
            deals_raw=boards_data["deals"]["items"],
            work_orders_raw=boards_data["work_orders"]["items"]
        )
        
        metrics_engine = MetricsEngine(board_data)
        summary_stats = metrics_engine.get_summary_stats()
        
        return {
            "source": "cache" if from_cache else "live",
            "deals_board_id": boards_data["deals"]["board_id"],
            "work_orders_board_id": boards_data["work_orders"]["board_id"],
            "fetched_at": boards_data["fetched_at"],
            "summary": summary_stats,
            "data_quality_warnings": [
                {
                    "field": w.field,
                    "issue": w.issue,
                    "affected_records": w.affected_records,
                    "severity": w.severity
                }
                for w in board_data.warnings
            ]
        }
    except Exception as e:
        logger.exception(f"Failed to get boards summary: {e}")
        raise HTTPException(
            status_code=503,
            detail={
                "error": "Failed to fetch board data",
                "detail": str(e),
                "code": "MONDAY_API_ERROR"
            }
        )


@router.get(
    "/cache/stats",
    summary="Cache statistics",
    description="View hit/miss stats and entry counts for board and response caches.",
)
async def get_cache_stats() -> Dict[str, Any]:
    """Return current cache statistics for monitoring."""
    return {
        "board_cache": board_cache.stats(),
        "response_cache": response_cache.stats(),
    }


@router.delete(
    "/cache/clear",
    summary="Clear caches",
    description="Invalidate all cached board data and responses.",
)
async def clear_caches() -> Dict[str, str]:
    """Flush both caches — next requests will fetch fresh data."""
    board_cache.clear()
    response_cache.clear()
    return {"status": "ok", "detail": "All caches cleared"}
