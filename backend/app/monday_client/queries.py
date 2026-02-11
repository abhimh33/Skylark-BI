"""
GraphQL queries for monday.com API.
"""


class MondayQueries:
    """Collection of GraphQL queries for monday.com API."""
    
    @staticmethod
    def get_board_items_query(board_id: str, cursor: str = None, limit: int = 100) -> str:
        """
        Generate query to fetch items from a board with pagination.
        
        Args:
            board_id: The monday.com board ID
            cursor: Pagination cursor for fetching next page
            limit: Number of items per page
        
        Returns:
            GraphQL query string
        """
        cursor_arg = f', cursor: "{cursor}"' if cursor else ""
        
        return f"""
        query {{
            boards(ids: [{board_id}]) {{
                id
                name
                columns {{
                    id
                    title
                    type
                    settings_str
                }}
                items_page(limit: {limit}{cursor_arg}) {{
                    cursor
                    items {{
                        id
                        name
                        created_at
                        updated_at
                        group {{
                            id
                            title
                        }}
                        column_values {{
                            id
                            type
                            text
                            value
                            ... on StatusValue {{
                                label
                                index
                            }}
                            ... on NumbersValue {{
                                number
                            }}
                            ... on DateValue {{
                                date
                                time
                            }}
                            ... on PersonValue {{
                                person_id
                                text
                            }}
                            ... on DropdownValue {{
                                text
                            }}
                            ... on TextValue {{
                                text
                            }}
                            ... on LinkValue {{
                                url
                                text
                            }}
                            ... on EmailValue {{
                                email
                                text
                            }}
                            ... on PhoneValue {{
                                phone
                                text
                            }}
                        }}
                    }}
                }}
            }}
        }}
        """

    @staticmethod
    def get_board_metadata_query(board_id: str) -> str:
        """
        Generate query to fetch board metadata including columns.
        
        Args:
            board_id: The monday.com board ID
        
        Returns:
            GraphQL query string
        """
        return f"""
        query {{
            boards(ids: [{board_id}]) {{
                id
                name
                description
                state
                board_kind
                columns {{
                    id
                    title
                    type
                    settings_str
                }}
                groups {{
                    id
                    title
                    color
                }}
                owners {{
                    id
                    name
                    email
                }}
            }}
        }}
        """

    @staticmethod
    def get_multiple_boards_query(board_ids: list[str]) -> str:
        """
        Generate query to fetch metadata for multiple boards.
        
        Args:
            board_ids: List of monday.com board IDs
        
        Returns:
            GraphQL query string
        """
        ids_str = ", ".join(board_ids)
        return f"""
        query {{
            boards(ids: [{ids_str}]) {{
                id
                name
                items_count
                columns {{
                    id
                    title
                    type
                }}
            }}
        }}
        """
