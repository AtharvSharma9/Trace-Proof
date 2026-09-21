from typing import List, Optional
from domain.models import Case

def create_case(case_number: str, title: str, created_by: str) -> Case:
    """
    Creates a new case, setting up the case folder and initial SQLite file.
    """
    return Case(
        id="case_1",
        case_number=case_number,
        title=title,
        created_by_badge=created_by,
        created_by_name="Test Officer",
        created_at="2026-09-21T10:00:00Z"
    )

def list_cases() -> List[Case]:
    """
    Retrieves all registered cases for the Case List screen.
    """
    return []

def get_case(case_id: str) -> Optional[Case]:
    """
    Retrieves a single case's metadata by its unique ID.
    """
    return None
