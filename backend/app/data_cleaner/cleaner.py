"""
Data cleaning and normalization utilities.
Handles messy real-world data from monday.com boards.
"""

import logging
import re
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from collections import defaultdict

from ..models.schemas import (
    DealItem,
    WorkOrderItem,
    DataQualityWarning,
    BoardData,
)

logger = logging.getLogger(__name__)


class DataCleaner:
    """
    Data cleaning and normalization for monday.com board data.
    
    Handles:
    - Sector name standardization
    - Numeric value parsing (including scientific notation)
    - Date field parsing and validation
    - Missing/incomplete record handling
    - Data quality tracking and warnings
    """
    
    # Common sector name mappings for standardization
    SECTOR_MAPPINGS = {
        # Domain-specific sectors from SkyLark boards
        "mining": "mining",
        "oil & gas": "oil_and_gas",
        "oil and gas": "oil_and_gas",
        "oil&gas": "oil_and_gas",
        "infrastructure": "infrastructure",
        "infra": "infrastructure",
        "agriculture": "agriculture",
        "agri": "agriculture",
        "forestry": "forestry",
        "forest": "forestry",
        "urban": "urban_planning",
        "urban planning": "urban_planning",
        "defence": "defence",
        "defense": "defence",
        "solar": "solar",
        "renewable": "renewable_energy",
        "renewables": "renewable_energy",
        "renewable energy": "renewable_energy",
        "water": "water",
        "hydro": "water",
        "utilities": "utilities",
        "telecom": "telecommunications",
        "telecommunications": "telecommunications",
        "power": "power",
        "railways": "railways",
        "railway": "railways",
        "road": "road",
        "roads": "road",
        "construction": "construction",
        "survey": "survey",
        "surveying": "survey",
        "mapping": "mapping",
        "gis": "gis",
        "geospatial": "geospatial",
        # General sectors
        "tech": "technology",
        "it": "technology",
        "information technology": "technology",
        "software": "technology",
        "saas": "technology",
        "fintech": "financial_services",
        "finance": "financial_services",
        "banking": "financial_services",
        "financial": "financial_services",
        "health": "healthcare",
        "medical": "healthcare",
        "pharma": "healthcare",
        "pharmaceutical": "healthcare",
        "biotech": "healthcare",
        "retail": "retail",
        "ecommerce": "retail",
        "e-commerce": "retail",
        "consumer": "retail",
        "manufacturing": "manufacturing",
        "industrial": "manufacturing",
        "real estate": "real_estate",
        "realestate": "real_estate",
        "property": "real_estate",
        "energy": "energy",
        "education": "education",
        "edtech": "education",
        "media": "media_entertainment",
        "entertainment": "media_entertainment",
        "transportation": "transportation",
        "logistics": "transportation",
        "government": "government",
        "public sector": "government",
        "nonprofit": "nonprofit",
        "non-profit": "nonprofit",
        "ngo": "nonprofit",
    }
    
    def __init__(self):
        """Initialize the data cleaner."""
        self.warnings: List[DataQualityWarning] = []
        self._sector_cache: Dict[str, str] = {}
        self._warning_counts: Dict[str, int] = defaultdict(int)
    
    def reset_warnings(self):
        """Reset all tracked warnings."""
        self.warnings = []
        self._warning_counts = defaultdict(int)
    
    def _add_warning(
        self,
        field: str,
        issue: str,
        severity: str = "warning",
        details: str = None
    ):
        """
        Track a data quality warning.
        
        Args:
            field: Field name with the issue
            issue: Description of the issue
            severity: Warning severity (info, warning, error)
            details: Additional details
        """
        key = f"{field}:{issue}"
        self._warning_counts[key] += 1
    
    def _finalize_warnings(self):
        """Convert warning counts to DataQualityWarning objects."""
        for key, count in self._warning_counts.items():
            field, issue = key.split(":", 1)
            self.warnings.append(DataQualityWarning(
                field=field,
                issue=issue,
                affected_records=count,
                severity="warning" if count < 10 else "error"
            ))
    
    def standardize_sector(self, sector: Optional[str]) -> Optional[str]:
        """
        Standardize sector name to a consistent format.
        
        Args:
            sector: Raw sector name
        
        Returns:
            Standardized sector name or None
        """
        if not sector:
            return None
        
        # Check cache first
        if sector in self._sector_cache:
            return self._sector_cache[sector]
        
        # Normalize: strip, lowercase, remove extra whitespace
        normalized = sector.strip().lower()
        normalized = re.sub(r'\s+', ' ', normalized)
        
        # Remove special characters except spaces and hyphens
        normalized = re.sub(r'[^\w\s-]', '', normalized)
        
        # Check direct mappings
        if normalized in self.SECTOR_MAPPINGS:
            result = self.SECTOR_MAPPINGS[normalized]
        else:
            # Try partial matching
            result = None
            for key, value in self.SECTOR_MAPPINGS.items():
                if key in normalized or normalized in key:
                    result = value
                    break
            
            if not result:
                # Return cleaned original if no mapping found
                result = normalized.replace(" ", "_")
        
        # Cache the result
        self._sector_cache[sector] = result
        return result
    
    def parse_numeric(self, value: Any) -> Optional[float]:
        """
        Safely parse a numeric value, handling various formats.
        
        Handles:
        - Scientific notation (1.5e6)
        - Currency symbols ($, €, £)
        - Thousands separators (1,000,000)
        - Percentage signs
        - Negative numbers
        
        Args:
            value: Raw value to parse
        
        Returns:
            Parsed float or None
        """
        if value is None:
            return None
        
        # Already a number
        if isinstance(value, (int, float)):
            return float(value)
        
        if not isinstance(value, str):
            try:
                return float(value)
            except (ValueError, TypeError):
                return None
        
        # Clean the string
        cleaned = value.strip()
        
        if not cleaned:
            return None
        
        # Remove currency symbols and whitespace
        for symbol in ["$", "€", "£", "¥", "₹", "kr", "CHF"]:
            cleaned = cleaned.replace(symbol, "")
        
        cleaned = cleaned.strip()
        
        # Handle percentage
        is_percentage = "%" in cleaned
        cleaned = cleaned.replace("%", "")
        
        # Handle parentheses for negative numbers: (1000) -> -1000
        if cleaned.startswith("(") and cleaned.endswith(")"):
            cleaned = "-" + cleaned[1:-1]
        
        # Remove thousands separators (be careful with European format)
        # If there's a comma after a period, it's European format
        if "," in cleaned and "." in cleaned:
            if cleaned.index(",") > cleaned.index("."):
                # European: 1.000.000,50 -> 1000000.50
                cleaned = cleaned.replace(".", "").replace(",", ".")
            else:
                # US: 1,000,000.50 -> 1000000.50
                cleaned = cleaned.replace(",", "")
        elif "," in cleaned:
            # Could be thousands separator or decimal
            parts = cleaned.split(",")
            if len(parts) == 2 and len(parts[1]) == 2:
                # Likely European decimal: 1000,50
                cleaned = cleaned.replace(",", ".")
            else:
                # Thousands separator: 1,000,000
                cleaned = cleaned.replace(",", "")
        
        # Try parsing
        try:
            result = float(cleaned)
            if is_percentage:
                result = result / 100.0
            return result
        except (ValueError, TypeError):
            return None
    
    def parse_date(self, value: Any) -> Optional[datetime]:
        """
        Safely parse a date value, handling various formats.
        
        Args:
            value: Raw date value
        
        Returns:
            Parsed datetime or None
        """
        if value is None:
            return None
        
        if isinstance(value, datetime):
            return value
        
        if not isinstance(value, str):
            return None
        
        cleaned = value.strip()
        
        if not cleaned or cleaned.lower() in ["null", "none", "n/a", "-", ""]:
            return None
        
        # Common date formats to try
        formats = [
            "%Y-%m-%d",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%dT%H:%M:%S.%f",
            "%Y-%m-%dT%H:%M:%SZ",
            "%Y-%m-%dT%H:%M:%S.%fZ",
            "%d/%m/%Y",
            "%m/%d/%Y",
            "%d-%m-%Y",
            "%m-%d-%Y",
            "%Y/%m/%d",
            "%d.%m.%Y",
            "%B %d, %Y",
            "%b %d, %Y",
            "%d %B %Y",
            "%d %b %Y",
        ]
        
        # Handle ISO format with timezone
        if "+" in cleaned or cleaned.endswith("Z"):
            cleaned = cleaned.replace("Z", "+00:00")
            try:
                return datetime.fromisoformat(cleaned)
            except (ValueError, TypeError):
                pass
        
        # Try each format
        for fmt in formats:
            try:
                return datetime.strptime(cleaned, fmt)
            except (ValueError, TypeError):
                continue
        
        return None
    
    def _get_first_not_none(self, raw_item: Dict[str, Any], *keys) -> Any:
        """
        Get the first non-None value from a list of keys.
        Unlike `or`, this treats 0 and 0.0 as valid values.
        """
        for key in keys:
            val = raw_item.get(key)
            if val is not None:
                return val
        return None

    def clean_deal_item(self, raw_item: Dict[str, Any]) -> Tuple[DealItem, List[str]]:
        """
        Clean and normalize a single deal item.
        
        Args:
            raw_item: Raw item dictionary from monday.com
        
        Returns:
            Tuple of (cleaned DealItem, list of issues found)
        """
        issues = []
        
        # Extract and clean fields
        item_id = str(raw_item.get("id", ""))
        name = str(raw_item.get("name", "")).strip()
        
        # Sector - try multiple possible column names
        sector_raw = (
            raw_item.get("sector_service") or
            raw_item.get("Sector/service") or
            raw_item.get("sector") or
            raw_item.get("industry") or
            raw_item.get("vertical") or
            raw_item.get("segment") or
            raw_item.get("category")
        )
        # Extract label if it's a status dict from monday.com
        if isinstance(sector_raw, dict):
            sector_raw = sector_raw.get("label")
        sector = self.standardize_sector(sector_raw)
        
        if not sector and sector_raw:
            issues.append(f"Could not standardize sector: {sector_raw}")
        
        # Deal value - try multiple possible column names
        deal_value_raw = self._get_first_not_none(
            raw_item,
            "masked_deal_value",
            "Masked Deal value",
            "deal_value",
            "value",
            "amount",
            "pipeline_value",
            "contract_value"
        )
        deal_value = self.parse_numeric(deal_value_raw)
        
        if deal_value is None and deal_value_raw:
            issues.append(f"Could not parse deal value: {deal_value_raw}")
            self._add_warning("deal_value", "Could not parse numeric value")
        elif deal_value is None:
            self._add_warning("deal_value", "Missing value")
        
        # Status - extract label if it's a dict
        status_raw = (
            raw_item.get("deal_status") or
            raw_item.get("Deal Status") or
            raw_item.get("status") or
            raw_item.get("stage")
        )
        if isinstance(status_raw, dict):
            status = status_raw.get("label")
        else:
            status = str(status_raw).strip() if status_raw else None
        
        # Close date
        close_date_raw = (
            raw_item.get("tentative_close_date") or
            raw_item.get("Tentative Close Date") or
            raw_item.get("close_date_a") or
            raw_item.get("Close Date (A)") or
            raw_item.get("close_date") or
            raw_item.get("expected_close_date")
        )
        close_date = self.parse_date(close_date_raw)
        
        if close_date is None and close_date_raw:
            issues.append(f"Could not parse close date: {close_date_raw}")
            self._add_warning("close_date", "Could not parse date")
        elif close_date is None:
            self._add_warning("close_date", "Missing value")
        
        # Created at
        created_at_raw = raw_item.get("created_at")
        created_at = self.parse_date(created_at_raw)
        
        # Owner
        owner = (
            raw_item.get("owner_code") or
            raw_item.get("Owner code") or
            raw_item.get("owner") or
            raw_item.get("assigned_to")
        )
        if isinstance(owner, dict):
            owner = owner.get("label")
        if isinstance(owner, list):
            owner = owner[0] if owner else None
        
        # Probability
        probability_raw = (
            raw_item.get("closure_probability") or
            raw_item.get("Closure Probability") or
            raw_item.get("probability")
        )
        # Handle status-dict probability (High/Medium/Low)
        if isinstance(probability_raw, dict):
            label = probability_raw.get("label", "").lower()
            probability_map = {"high": 0.8, "medium": 0.5, "low": 0.2}
            probability = probability_map.get(label, 0.5)
        else:
            probability = self.parse_numeric(probability_raw)
            if probability and probability > 1:
                probability = probability / 100.0
        
        return DealItem(
            id=item_id,
            name=name,
            sector=sector,
            deal_value=deal_value,
            status=status,
            close_date=close_date,
            created_at=created_at,
            owner=owner,
            probability=probability,
            raw_data=raw_item
        ), issues
    
    def clean_work_order_item(self, raw_item: Dict[str, Any]) -> Tuple[WorkOrderItem, List[str]]:
        """
        Clean and normalize a single work order item.
        
        Args:
            raw_item: Raw item dictionary from monday.com
        
        Returns:
            Tuple of (cleaned WorkOrderItem, list of issues found)
        """
        issues = []
        
        # Extract and clean fields
        item_id = str(raw_item.get("id", ""))
        name = str(raw_item.get("name", "")).strip()
        
        # Sector
        sector_raw = (
            raw_item.get("sector") or
            raw_item.get("Sector") or
            raw_item.get("sector_service") or
            raw_item.get("industry") or
            raw_item.get("vertical")
        )
        # Extract label if it's a status dict from monday.com
        if isinstance(sector_raw, dict):
            sector_raw = sector_raw.get("label")
        sector = self.standardize_sector(sector_raw)
        
        # Invoiced amount (total order value excl GST)
        invoiced_raw = self._get_first_not_none(
            raw_item,
            "amount_in_rupees_excl_of_gst_masked",
            "Amount in Rupees (Excl of GST) (Masked)",
            "invoiced_amount",
            "invoiced",
            "invoice_amount"
        )
        invoiced_amount = self.parse_numeric(invoiced_raw)
        
        if invoiced_amount is None and invoiced_raw:
            issues.append(f"Could not parse invoiced amount: {invoiced_raw}")
            self._add_warning("invoiced_amount", "Could not parse numeric value")
        
        # Collected amount (billed value = what's been billed so far)
        collected_raw = self._get_first_not_none(
            raw_item,
            "billed_value_in_rupees_incl_of_gst_masked",
            "Billed Value in Rupees (Incl of GST.) (Masked)",
            "collected_amount",
            "collected",
            "paid_amount"
        )
        collected_amount = self.parse_numeric(collected_raw)
        
        if collected_amount is None and collected_raw:
            issues.append(f"Could not parse collected amount: {collected_raw}")
            self._add_warning("collected_amount", "Could not parse numeric value")
        
        # Status
        status_raw = (
            raw_item.get("execution_status") or
            raw_item.get("Execution Status") or
            raw_item.get("status") or
            raw_item.get("order_status")
        )
        if isinstance(status_raw, dict):
            status = status_raw.get("label")
        else:
            status = str(status_raw).strip() if status_raw else None
        
        # Invoice date
        invoice_date_raw = (
            raw_item.get("last_invoice_date") or
            raw_item.get("Last invoice date") or
            raw_item.get("invoice_date") or
            raw_item.get("invoiced_date")
        )
        invoice_date = self.parse_date(invoice_date_raw)
        
        # Collection date
        collection_date_raw = (
            raw_item.get("data_delivery_date") or
            raw_item.get("Data Delivery Date") or
            raw_item.get("collection_date") or
            raw_item.get("payment_date")
        )
        collection_date = self.parse_date(collection_date_raw)
        
        # Link to deal
        deal_id = (
            raw_item.get("serial") or
            raw_item.get("Serial #") or
            raw_item.get("deal_id") or
            raw_item.get("linked_deal")
        )
        if isinstance(deal_id, dict):
            deal_id = deal_id.get("id")
        elif isinstance(deal_id, list):
            deal_id = deal_id[0] if deal_id else None
        
        return WorkOrderItem(
            id=item_id,
            name=name,
            sector=sector,
            invoiced_amount=invoiced_amount,
            collected_amount=collected_amount,
            status=status,
            invoice_date=invoice_date,
            collection_date=collection_date,
            deal_id=str(deal_id) if deal_id else None,
            raw_data=raw_item
        ), issues
    
    def clean_board_data(
        self,
        deals_raw: List[Dict[str, Any]],
        work_orders_raw: List[Dict[str, Any]]
    ) -> BoardData:
        """
        Clean and normalize data from both boards.
        
        Args:
            deals_raw: Raw deals data from monday.com
            work_orders_raw: Raw work orders data from monday.com
        
        Returns:
            Cleaned BoardData with quality warnings
        """
        self.reset_warnings()
        
        # Clean deals
        deals = []
        deal_issues = []
        for raw_deal in deals_raw:
            deal, issues = self.clean_deal_item(raw_deal)
            deals.append(deal)
            deal_issues.extend(issues)
        
        # Clean work orders
        work_orders = []
        wo_issues = []
        for raw_wo in work_orders_raw:
            wo, issues = self.clean_work_order_item(raw_wo)
            work_orders.append(wo)
            wo_issues.extend(issues)
        
        # Finalize warnings
        self._finalize_warnings()
        
        # Log cleaning summary
        logger.info(f"Cleaned {len(deals)} deals with {len(deal_issues)} issues")
        logger.info(f"Cleaned {len(work_orders)} work orders with {len(wo_issues)} issues")
        logger.info(f"Generated {len(self.warnings)} data quality warnings")
        
        return BoardData(
            deals=deals,
            work_orders=work_orders,
            fetch_timestamp=datetime.utcnow(),
            warnings=self.warnings
        )
