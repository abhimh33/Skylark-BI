"""
Pydantic schemas for request/response models and data structures.
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class MetricType(str, Enum):
    """Types of metrics that can be computed."""
    PIPELINE_VALUE = "pipeline_value"
    PIPELINE_BY_SECTOR = "pipeline_by_sector"
    DEAL_RATIO = "deal_ratio"
    REVENUE_BY_SECTOR = "revenue_by_sector"
    INVOICED_VS_COLLECTED = "invoiced_vs_collected"
    COLLECTION_EFFICIENCY = "collection_efficiency"
    PIPELINE_VS_REVENUE = "pipeline_vs_revenue"
    LEADERSHIP_UPDATE = "leadership_update"
    GENERAL = "general"


class TimeRange(BaseModel):
    """Time range for filtering data."""
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    period: Optional[str] = None  # e.g., "last_quarter", "ytd", "last_month"


class IntentExtraction(BaseModel):
    """Structured intent extracted from natural language query."""
    sector: Optional[str] = None
    time_range: Optional[TimeRange] = None
    metric_type: MetricType = MetricType.GENERAL
    entities: List[str] = Field(default_factory=list)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    requires_clarification: bool = False
    clarification_prompt: Optional[str] = None
    raw_query: str = ""


class DealItem(BaseModel):
    """Structured representation of a Deal from monday.com."""
    id: str
    name: str
    sector: Optional[str] = None
    deal_value: Optional[float] = None
    status: Optional[str] = None
    close_date: Optional[datetime] = None
    created_at: Optional[datetime] = None
    owner: Optional[str] = None
    probability: Optional[float] = None
    raw_data: Dict[str, Any] = Field(default_factory=dict)


class WorkOrderItem(BaseModel):
    """Structured representation of a Work Order from monday.com."""
    id: str
    name: str
    sector: Optional[str] = None
    invoiced_amount: Optional[float] = None
    collected_amount: Optional[float] = None
    status: Optional[str] = None
    invoice_date: Optional[datetime] = None
    collection_date: Optional[datetime] = None
    deal_id: Optional[str] = None
    raw_data: Dict[str, Any] = Field(default_factory=dict)


class DataQualityWarning(BaseModel):
    """Warning about data quality issues."""
    field: str
    issue: str
    affected_records: int
    severity: str = "warning"  # "warning", "error", "info"
    details: Optional[str] = None


class MetricSummary(BaseModel):
    """Summary of computed business metrics."""
    name: str
    value: Any
    formatted_value: str
    description: str
    trend: Optional[str] = None  # "up", "down", "stable"
    change_percentage: Optional[float] = None


class BoardData(BaseModel):
    """Combined data from monday.com boards."""
    deals: List[DealItem] = Field(default_factory=list)
    work_orders: List[WorkOrderItem] = Field(default_factory=list)
    fetch_timestamp: datetime = Field(default_factory=datetime.utcnow)
    warnings: List[DataQualityWarning] = Field(default_factory=list)


class AskRequest(BaseModel):
    """Request model for the /ask endpoint."""
    question: str = Field(..., min_length=1, max_length=2000)
    context: Optional[Dict[str, Any]] = None
    include_raw_data: bool = False


class AskResponse(BaseModel):
    """Response model for the /ask endpoint."""
    insights: str
    key_metrics: List[MetricSummary] = Field(default_factory=list)
    data_quality_warnings: List[DataQualityWarning] = Field(default_factory=list)
    intent: Optional[IntentExtraction] = None
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    requires_clarification: bool = False
    clarification_prompt: Optional[str] = None
    suggested_questions: List[str] = Field(default_factory=list)
    source: str = Field(default="live", description="'live' or 'cache' — indicates whether this response was freshly computed or served from cache")
    raw_data: Optional[Dict[str, Any]] = None
    processing_time_ms: Optional[int] = None


class ErrorResponse(BaseModel):
    """Standard error response model."""
    error: str
    detail: Optional[str] = None
    code: str = "UNKNOWN_ERROR"
