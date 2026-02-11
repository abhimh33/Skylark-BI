"""
monday.com GraphQL API client implementation.
Handles API communication, pagination, and data transformation.
"""

import httpx
import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import json

from ..config import get_settings
from .queries import MondayQueries

logger = logging.getLogger(__name__)


class MondayClientError(Exception):
    """Custom exception for monday.com API errors."""
    
    def __init__(self, message: str, status_code: int = None, response_data: dict = None):
        super().__init__(message)
        self.status_code = status_code
        self.response_data = response_data


class MondayClient:
    """
    Client for interacting with monday.com GraphQL API.
    
    Handles:
    - API authentication
    - GraphQL query execution
    - Pagination for large datasets
    - Error handling and retries
    - Data transformation from column_values to structured dicts
    """
    
    def __init__(self, api_key: str = None, api_url: str = None):
        """
        Initialize the monday.com client.
        
        Args:
            api_key: monday.com API key (optional, uses settings if not provided)
            api_url: API URL (optional, uses settings if not provided)
        """
        settings = get_settings()
        self.api_key = api_key or settings.MONDAY_API_KEY
        self.api_url = api_url or settings.MONDAY_API_URL
        self.page_size = settings.MONDAY_PAGE_SIZE
        
        self.headers = {
            "Authorization": self.api_key,
            "Content-Type": "application/json",
            "API-Version": "2024-01"
        }
    
    async def _execute_query(self, query: str, variables: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Execute a GraphQL query against the monday.com API.
        
        Args:
            query: GraphQL query string
            variables: Optional query variables
        
        Returns:
            API response data
        
        Raises:
            MondayClientError: If API request fails
        """
        payload = {"query": query}
        if variables:
            payload["variables"] = variables
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(
                    self.api_url,
                    headers=self.headers,
                    json=payload
                )
                
                response.raise_for_status()
                data = response.json()
                
                # Check for GraphQL errors
                if "errors" in data:
                    error_messages = [e.get("message", "Unknown error") for e in data["errors"]]
                    raise MondayClientError(
                        f"GraphQL errors: {'; '.join(error_messages)}",
                        response_data=data
                    )
                
                return data.get("data", {})
                
            except httpx.HTTPStatusError as e:
                logger.error(f"HTTP error from monday.com API: {e}")
                raise MondayClientError(
                    f"HTTP error: {e.response.status_code}",
                    status_code=e.response.status_code
                )
            except httpx.RequestError as e:
                logger.error(f"Request error to monday.com API: {e}")
                raise MondayClientError(f"Request failed: {str(e)}")
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse monday.com API response: {e}")
                raise MondayClientError("Invalid JSON response from API")
    
    def _parse_column_value(self, column_value: Dict[str, Any]) -> Any:
        """
        Parse a single column value into a Python-native type.
        
        Args:
            column_value: Raw column value from monday.com API
        
        Returns:
            Parsed value (str, int, float, datetime, dict, or None)
        """
        col_type = column_value.get("type", "")
        text_value = column_value.get("text", "")
        raw_value = column_value.get("value")
        
        # Handle empty values
        if not text_value and not raw_value:
            return None
        
        # Type-specific parsing
        if col_type == "numeric" or col_type == "numbers":
            number = column_value.get("number")
            if number is not None:
                return float(number)
            # Try parsing from text
            if text_value:
                try:
                    # Handle scientific notation and currency symbols
                    cleaned = text_value.replace(",", "").replace("$", "").replace("€", "").strip()
                    return float(cleaned)
                except (ValueError, TypeError):
                    return None
            return None
        
        elif col_type == "date":
            date_value = column_value.get("date")
            if date_value:
                try:
                    time_value = column_value.get("time", "00:00:00")
                    if time_value:
                        return datetime.fromisoformat(f"{date_value}T{time_value}")
                    return datetime.fromisoformat(date_value)
                except (ValueError, TypeError):
                    pass
            # Try parsing from text
            if text_value:
                try:
                    return datetime.fromisoformat(text_value.replace("Z", "+00:00"))
                except (ValueError, TypeError):
                    return None
            return None
        
        elif col_type == "status":
            label = column_value.get("label")
            if label:
                return {"label": label, "index": column_value.get("index")}
            return text_value or None
        
        elif col_type == "person" or col_type == "people":
            return text_value or None
        
        elif col_type == "dropdown":
            values = column_value.get("values", [])
            if values:
                return [v.get("name") for v in values]
            return text_value.split(", ") if text_value else None
        
        elif col_type == "link":
            url = column_value.get("url")
            if url:
                return {"url": url, "text": column_value.get("text", "")}
            return text_value or None
        
        elif col_type == "email":
            email = column_value.get("email")
            if email:
                return email
            return text_value or None
        
        elif col_type == "phone":
            phone = column_value.get("phone")
            if phone:
                return phone
            return text_value or None
        
        # Default: return text value
        return text_value or None
    
    def _transform_item(self, item: Dict[str, Any], columns: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Transform a monday.com item into a structured dictionary.
        
        Args:
            item: Raw item data from API
            columns: Column definitions for the board
        
        Returns:
            Structured dictionary with parsed column values
        """
        # Create column ID to title mapping
        column_map = {col["id"]: col["title"] for col in columns}
        
        # Start with basic item info
        transformed = {
            "id": item.get("id"),
            "name": item.get("name"),
            "created_at": item.get("created_at"),
            "updated_at": item.get("updated_at"),
            "group": item.get("group", {}).get("title"),
        }
        
        # Parse each column value
        for col_value in item.get("column_values", []):
            col_id = col_value.get("id")
            col_title = column_map.get(col_id, col_id)
            
            # Normalize column title to snake_case for consistent access
            normalized_title = self._normalize_column_name(col_title)
            parsed_value = self._parse_column_value(col_value)
            
            transformed[normalized_title] = parsed_value
            
            # Also store with original title for flexibility
            if normalized_title != col_title:
                transformed[col_title] = parsed_value
        
        return transformed
    
    def _normalize_column_name(self, name: str) -> str:
        """
        Normalize a column name to snake_case.
        
        Args:
            name: Original column name
        
        Returns:
            Normalized snake_case name
        """
        # Replace special characters and spaces with underscores
        normalized = name.lower().strip()
        for char in [" ", "-", "/", ".", "(", ")", "#"]:
            normalized = normalized.replace(char, "_")
        
        # Remove consecutive underscores
        while "__" in normalized:
            normalized = normalized.replace("__", "_")
        
        # Remove leading/trailing underscores
        return normalized.strip("_")
    
    async def get_board_items(
        self,
        board_id: str,
        fetch_all: bool = True
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Fetch all items from a monday.com board.
        
        Args:
            board_id: The board ID to fetch items from
            fetch_all: Whether to paginate through all items
        
        Returns:
            Tuple of (items list, columns list)
        
        Raises:
            MondayClientError: If API request fails
        """
        all_items = []
        columns = []
        cursor = None
        page = 0
        
        logger.info(f"Fetching items from board {board_id}")
        
        while True:
            page += 1
            query = MondayQueries.get_board_items_query(
                board_id=board_id,
                cursor=cursor,
                limit=self.page_size
            )
            
            data = await self._execute_query(query)
            
            boards = data.get("boards", [])
            if not boards:
                logger.warning(f"No board found with ID {board_id}")
                break
            
            board = boards[0]
            
            # Get columns on first page
            if page == 1:
                columns = board.get("columns", [])
                logger.info(f"Board '{board.get('name')}' has {len(columns)} columns")
            
            items_page = board.get("items_page", {})
            items = items_page.get("items", [])
            
            # Transform items
            for item in items:
                transformed = self._transform_item(item, columns)
                all_items.append(transformed)
            
            logger.info(f"Page {page}: Fetched {len(items)} items (total: {len(all_items)})")
            
            # Check for more pages
            cursor = items_page.get("cursor")
            if not cursor or not fetch_all or not items:
                break
        
        logger.info(f"Completed fetching {len(all_items)} items from board {board_id}")
        return all_items, columns
    
    async def get_board_metadata(self, board_id: str) -> Dict[str, Any]:
        """
        Fetch metadata for a board (columns, groups, owners).
        
        Args:
            board_id: The board ID
        
        Returns:
            Board metadata dictionary
        """
        query = MondayQueries.get_board_metadata_query(board_id)
        data = await self._execute_query(query)
        
        boards = data.get("boards", [])
        if not boards:
            raise MondayClientError(f"Board not found: {board_id}")
        
        return boards[0]
    
    async def get_deals_board(self, board_id: str = None) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Fetch items from the Deals board.
        
        Args:
            board_id: Optional board ID override
        
        Returns:
            Tuple of (deals items, columns)
        """
        settings = get_settings()
        bid = board_id or settings.DEALS_BOARD_ID
        return await self.get_board_items(bid)
    
    async def get_work_orders_board(self, board_id: str = None) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Fetch items from the Work Orders board.
        
        Args:
            board_id: Optional board ID override
        
        Returns:
            Tuple of (work order items, columns)
        """
        settings = get_settings()
        bid = board_id or settings.WORK_ORDERS_BOARD_ID
        return await self.get_board_items(bid)
    
    async def get_all_boards_data(self) -> Dict[str, Any]:
        """
        Fetch data from both Deals and Work Orders boards.
        
        Returns:
            Dictionary with deals, work_orders, and metadata
        """
        settings = get_settings()
        
        # Fetch both boards in parallel
        import asyncio
        deals_task = self.get_deals_board()
        work_orders_task = self.get_work_orders_board()
        
        (deals_items, deals_columns), (wo_items, wo_columns) = await asyncio.gather(
            deals_task, work_orders_task
        )
        
        return {
            "deals": {
                "items": deals_items,
                "columns": deals_columns,
                "board_id": settings.DEALS_BOARD_ID
            },
            "work_orders": {
                "items": wo_items,
                "columns": wo_columns,
                "board_id": settings.WORK_ORDERS_BOARD_ID
            },
            "fetched_at": datetime.utcnow().isoformat()
        }
