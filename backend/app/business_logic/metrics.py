"""
Business metrics computation engine.
Computes founder-level metrics from cleaned board data.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from collections import defaultdict

from ..models.schemas import (
    BoardData,
    DealItem,
    WorkOrderItem,
    MetricSummary,
    MetricType,
    TimeRange,
)

logger = logging.getLogger(__name__)


class MetricsEngine:
    """
    Business metrics computation engine.
    
    Computes founder-level metrics including:
    - Total pipeline value
    - Pipeline by sector
    - Open vs closed deal ratio
    - Revenue by sector
    - Total invoiced vs total collected
    - Collection efficiency percentage
    - Cross-board comparisons (pipeline vs executed revenue)
    """
    
    def __init__(self, board_data: BoardData):
        """
        Initialize the metrics engine with cleaned board data.
        
        Args:
            board_data: Cleaned BoardData from DataCleaner
        """
        self.data = board_data
        self.deals = board_data.deals
        self.work_orders = board_data.work_orders
    
    def _filter_by_time_range(
        self,
        items: List[Any],
        time_range: Optional[TimeRange],
        date_field: str = "created_at"
    ) -> List[Any]:
        """
        Filter items by time range.
        
        Args:
            items: List of items to filter
            time_range: Time range filter
            date_field: Field name to use for date filtering
        
        Returns:
            Filtered list of items
        """
        if not time_range:
            return items
        
        now = datetime.utcnow()
        start_date = time_range.start_date
        end_date = time_range.end_date
        
        # Handle period-based time ranges
        if time_range.period:
            period = time_range.period.lower()
            if period == "ytd" or period == "year_to_date":
                start_date = datetime(now.year, 1, 1)
                end_date = now
            elif period == "last_quarter" or period == "quarter":
                current_quarter = (now.month - 1) // 3
                if current_quarter == 0:
                    start_date = datetime(now.year - 1, 10, 1)
                    end_date = datetime(now.year - 1, 12, 31)
                else:
                    start_month = (current_quarter - 1) * 3 + 1
                    end_month = start_month + 2
                    start_date = datetime(now.year, start_month, 1)
                    end_date = datetime(now.year, end_month + 1, 1) - timedelta(days=1)
            elif period == "last_month" or period == "month":
                if now.month == 1:
                    start_date = datetime(now.year - 1, 12, 1)
                    end_date = datetime(now.year, 1, 1) - timedelta(days=1)
                else:
                    start_date = datetime(now.year, now.month - 1, 1)
                    end_date = datetime(now.year, now.month, 1) - timedelta(days=1)
            elif period == "last_week" or period == "week":
                start_date = now - timedelta(days=now.weekday() + 7)
                end_date = start_date + timedelta(days=6)
            elif period == "last_year" or period == "year":
                start_date = datetime(now.year - 1, 1, 1)
                end_date = datetime(now.year - 1, 12, 31)
        
        # Filter items
        filtered = []
        for item in items:
            item_date = getattr(item, date_field, None)
            if not item_date:
                continue
            
            if start_date and item_date < start_date:
                continue
            if end_date and item_date > end_date:
                continue
            
            filtered.append(item)
        
        return filtered
    
    def _filter_by_sector(
        self,
        items: List[Any],
        sector: Optional[str]
    ) -> List[Any]:
        """
        Filter items by sector.
        
        Args:
            items: List of items to filter
            sector: Sector to filter by
        
        Returns:
            Filtered list of items
        """
        if not sector:
            return items
        
        sector_lower = sector.lower().replace(" ", "_")
        return [
            item for item in items
            if item.sector and sector_lower in item.sector.lower()
        ]
    
    def _format_currency(self, value: float) -> str:
        """Format a number as currency (INR)."""
        if value >= 10_000_000:
            return f"\u20b9{value / 10_000_000:.2f} Cr"
        elif value >= 100_000:
            return f"\u20b9{value / 100_000:.2f} L"
        elif value >= 1_000:
            return f"\u20b9{value / 1_000:.1f}K"
        else:
            return f"\u20b9{value:,.2f}"
    
    def _format_percentage(self, value: float) -> str:
        """Format a number as percentage."""
        return f"{value * 100:.1f}%"
    
    def compute_total_pipeline_value(
        self,
        sector: Optional[str] = None,
        time_range: Optional[TimeRange] = None,
        include_closed: bool = False
    ) -> MetricSummary:
        """
        Compute total pipeline value.
        
        Args:
            sector: Optional sector filter
            time_range: Optional time range filter
            include_closed: Whether to include closed deals
        
        Returns:
            MetricSummary with pipeline value
        """
        deals = self._filter_by_sector(self.deals, sector)
        deals = self._filter_by_time_range(deals, time_range)
        
        # Filter by status if needed
        if not include_closed:
            closed_keywords = ["closed", "won", "lost", "completed", "rejected"]
            deals = [
                d for d in deals
                if not d.status or not any(
                    kw in (d.status or "").lower() for kw in closed_keywords
                )
            ]
        
        # Sum pipeline values
        total = sum(d.deal_value or 0 for d in deals)
        
        description = "Total pipeline value"
        if sector:
            description += f" for {sector} sector"
        if not include_closed:
            description += " (open deals only)"
        
        return MetricSummary(
            name="total_pipeline_value",
            value=total,
            formatted_value=self._format_currency(total),
            description=description
        )
    
    def compute_pipeline_by_sector(
        self,
        time_range: Optional[TimeRange] = None
    ) -> MetricSummary:
        """
        Compute pipeline value broken down by sector.
        
        Args:
            time_range: Optional time range filter
        
        Returns:
            MetricSummary with sector breakdown
        """
        deals = self._filter_by_time_range(self.deals, time_range)
        
        sector_values = defaultdict(float)
        for deal in deals:
            sector = deal.sector or "unknown"
            sector_values[sector] += deal.deal_value or 0
        
        # Sort by value descending
        sorted_sectors = dict(sorted(
            sector_values.items(),
            key=lambda x: x[1],
            reverse=True
        ))
        
        # Format for display
        formatted_breakdown = "\n".join([
            f"  {sector}: {self._format_currency(value)}"
            for sector, value in sorted_sectors.items()
        ])
        
        return MetricSummary(
            name="pipeline_by_sector",
            value=sorted_sectors,
            formatted_value=formatted_breakdown,
            description="Pipeline value breakdown by sector"
        )
    
    def compute_deal_ratio(
        self,
        sector: Optional[str] = None,
        time_range: Optional[TimeRange] = None
    ) -> MetricSummary:
        """
        Compute open vs closed deal ratio.
        
        Args:
            sector: Optional sector filter
            time_range: Optional time range filter
        
        Returns:
            MetricSummary with deal ratio
        """
        deals = self._filter_by_sector(self.deals, sector)
        deals = self._filter_by_time_range(deals, time_range)
        
        if not deals:
            return MetricSummary(
                name="deal_ratio",
                value={"open": 0, "closed": 0, "ratio": 0},
                formatted_value="No deals found",
                description="Open vs closed deal ratio"
            )
        
        closed_statuses = ["closed", "won", "lost", "completed", "closed won", "closed lost", "rejected"]
        won_statuses = ["closed won", "won", "completed"]
        
        closed_count = sum(
            1 for d in deals
            if d.status and any(s in d.status.lower() for s in closed_statuses)
        )
        won_count = sum(
            1 for d in deals
            if d.status and any(s in d.status.lower() for s in won_statuses)
        )
        open_count = len(deals) - closed_count
        
        ratio = open_count / closed_count if closed_count > 0 else float('inf')
        
        return MetricSummary(
            name="deal_ratio",
            value={"open": open_count, "closed": closed_count, "won": won_count, "ratio": ratio},
            formatted_value=f"{open_count} open : {closed_count} closed (won: {won_count}) ({ratio:.2f}:1)",
            description="Open vs closed deal ratio"
        )
    
    def compute_revenue_by_sector(
        self,
        time_range: Optional[TimeRange] = None,
        use_invoiced: bool = True
    ) -> MetricSummary:
        """
        Compute revenue broken down by sector.
        
        Args:
            time_range: Optional time range filter
            use_invoiced: Use invoiced (True) or collected (False) amounts
        
        Returns:
            MetricSummary with sector breakdown
        """
        work_orders = self._filter_by_time_range(
            self.work_orders,
            time_range,
            date_field="invoice_date"
        )
        
        sector_values = defaultdict(float)
        for wo in work_orders:
            sector = wo.sector or "unknown"
            amount = (wo.invoiced_amount if use_invoiced else wo.collected_amount) or 0
            sector_values[sector] += amount
        
        # Sort by value descending
        sorted_sectors = dict(sorted(
            sector_values.items(),
            key=lambda x: x[1],
            reverse=True
        ))
        
        # Format for display
        amount_type = "invoiced" if use_invoiced else "collected"
        formatted_breakdown = "\n".join([
            f"  {sector}: {self._format_currency(value)}"
            for sector, value in sorted_sectors.items()
        ])
        
        return MetricSummary(
            name="revenue_by_sector",
            value=sorted_sectors,
            formatted_value=formatted_breakdown,
            description=f"Revenue ({amount_type}) breakdown by sector"
        )
    
    def compute_invoiced_vs_collected(
        self,
        sector: Optional[str] = None,
        time_range: Optional[TimeRange] = None
    ) -> MetricSummary:
        """
        Compute total invoiced vs total collected amounts.
        
        Args:
            sector: Optional sector filter
            time_range: Optional time range filter
        
        Returns:
            MetricSummary with invoiced vs collected comparison
        """
        work_orders = self._filter_by_sector(self.work_orders, sector)
        work_orders = self._filter_by_time_range(
            work_orders,
            time_range,
            date_field="invoice_date"
        )
        
        total_invoiced = sum(wo.invoiced_amount or 0 for wo in work_orders)
        total_collected = sum(wo.collected_amount or 0 for wo in work_orders)
        outstanding = total_invoiced - total_collected
        
        description = "Invoiced vs collected amounts"
        if sector:
            description += f" for {sector} sector"
        
        return MetricSummary(
            name="invoiced_vs_collected",
            value={
                "invoiced": total_invoiced,
                "collected": total_collected,
                "outstanding": outstanding
            },
            formatted_value=f"Invoiced: {self._format_currency(total_invoiced)} | Collected: {self._format_currency(total_collected)} | Outstanding: {self._format_currency(outstanding)}",
            description=description
        )
    
    def compute_collection_efficiency(
        self,
        sector: Optional[str] = None,
        time_range: Optional[TimeRange] = None
    ) -> MetricSummary:
        """
        Compute collection efficiency percentage.
        
        Args:
            sector: Optional sector filter
            time_range: Optional time range filter
        
        Returns:
            MetricSummary with collection efficiency
        """
        work_orders = self._filter_by_sector(self.work_orders, sector)
        work_orders = self._filter_by_time_range(
            work_orders,
            time_range,
            date_field="invoice_date"
        )
        
        total_invoiced = sum(wo.invoiced_amount or 0 for wo in work_orders)
        total_collected = sum(wo.collected_amount or 0 for wo in work_orders)
        
        if total_invoiced == 0:
            efficiency = 0.0
        else:
            efficiency = total_collected / total_invoiced
        
        # Determine trend (simplified - in production, compare to previous period)
        trend = None
        if efficiency >= 0.9:
            trend = "stable"
        elif efficiency >= 0.7:
            trend = "down"
        
        description = "Collection efficiency"
        if sector:
            description += f" for {sector} sector"
        
        return MetricSummary(
            name="collection_efficiency",
            value=efficiency,
            formatted_value=self._format_percentage(efficiency),
            description=description,
            trend=trend
        )
    
    def compute_pipeline_vs_revenue(
        self,
        sector: Optional[str] = None,
        time_range: Optional[TimeRange] = None
    ) -> MetricSummary:
        """
        Compare pipeline value against executed revenue.
        
        Args:
            sector: Optional sector filter
            time_range: Optional time range filter
        
        Returns:
            MetricSummary with comparison
        """
        # Get pipeline value
        deals = self._filter_by_sector(self.deals, sector)
        deals = self._filter_by_time_range(deals, time_range)
        pipeline_value = sum(d.deal_value or 0 for d in deals)
        
        # Get executed revenue
        work_orders = self._filter_by_sector(self.work_orders, sector)
        work_orders = self._filter_by_time_range(
            work_orders,
            time_range,
            date_field="invoice_date"
        )
        executed_revenue = sum(wo.invoiced_amount or 0 for wo in work_orders)
        
        # Calculate conversion ratio
        conversion_ratio = executed_revenue / pipeline_value if pipeline_value > 0 else 0
        
        description = "Pipeline value vs executed revenue"
        if sector:
            description += f" for {sector} sector"
        
        return MetricSummary(
            name="pipeline_vs_revenue",
            value={
                "pipeline": pipeline_value,
                "revenue": executed_revenue,
                "conversion_ratio": conversion_ratio
            },
            formatted_value=f"Pipeline: {self._format_currency(pipeline_value)} | Revenue: {self._format_currency(executed_revenue)} | Conversion: {self._format_percentage(conversion_ratio)}",
            description=description
        )
    
    def compute_metrics_for_intent(
        self,
        metric_type: MetricType,
        sector: Optional[str] = None,
        time_range: Optional[TimeRange] = None
    ) -> List[MetricSummary]:
        """
        Compute metrics based on extracted intent.
        
        Args:
            metric_type: Type of metric to compute
            sector: Optional sector filter
            time_range: Optional time range filter
        
        Returns:
            List of computed MetricSummary objects
        """
        metrics = []
        
        if metric_type == MetricType.PIPELINE_VALUE:
            metrics.append(self.compute_total_pipeline_value(sector, time_range))
        
        elif metric_type == MetricType.PIPELINE_BY_SECTOR:
            metrics.append(self.compute_pipeline_by_sector(time_range))
        
        elif metric_type == MetricType.DEAL_RATIO:
            metrics.append(self.compute_deal_ratio(sector, time_range))
        
        elif metric_type == MetricType.REVENUE_BY_SECTOR:
            metrics.append(self.compute_revenue_by_sector(time_range))
        
        elif metric_type == MetricType.INVOICED_VS_COLLECTED:
            metrics.append(self.compute_invoiced_vs_collected(sector, time_range))
        
        elif metric_type == MetricType.COLLECTION_EFFICIENCY:
            metrics.append(self.compute_collection_efficiency(sector, time_range))
        
        elif metric_type == MetricType.PIPELINE_VS_REVENUE:
            metrics.append(self.compute_pipeline_vs_revenue(sector, time_range))

        elif metric_type == MetricType.LEADERSHIP_UPDATE:
            # Leadership update needs ALL metrics for comprehensive briefing
            metrics.extend([
                self.compute_total_pipeline_value(sector, time_range),
                self.compute_deal_ratio(sector, time_range),
                self.compute_invoiced_vs_collected(sector, time_range),
                self.compute_collection_efficiency(sector, time_range),
                self.compute_pipeline_by_sector(time_range),
                self.compute_revenue_by_sector(time_range),
                self.compute_pipeline_vs_revenue(sector, time_range),
            ])
        
        elif metric_type == MetricType.GENERAL:
            # For general queries, provide a comprehensive overview
            metrics.extend([
                self.compute_total_pipeline_value(sector, time_range),
                self.compute_collection_efficiency(sector, time_range),
                self.compute_invoiced_vs_collected(sector, time_range),
                self.compute_deal_ratio(sector, time_range),
            ])
        
        return metrics
    
    def get_summary_stats(self) -> Dict[str, Any]:
        """
        Get summary statistics for the board data.
        
        Returns:
            Dictionary with summary statistics
        """
        return {
            "total_deals": len(self.deals),
            "total_work_orders": len(self.work_orders),
            "deals_with_value": sum(1 for d in self.deals if d.deal_value),
            "deals_with_sector": sum(1 for d in self.deals if d.sector),
            "work_orders_with_invoiced": sum(1 for wo in self.work_orders if wo.invoiced_amount),
            "work_orders_with_collected": sum(1 for wo in self.work_orders if wo.collected_amount),
            "unique_sectors": list(set(
                d.sector for d in self.deals if d.sector
            ) | set(
                wo.sector for wo in self.work_orders if wo.sector
            )),
            "data_quality_warnings": len(self.data.warnings)
        }
