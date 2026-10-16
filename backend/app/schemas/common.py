"""
Common Error and Response Schemas.
"""

from typing import Any, List
from pydantic import BaseModel, Field


class ErrorDetail(BaseModel):
    field: str
    type: str
    message: str


class StandardErrorResponse(BaseModel):
    """Standardized machine-readable error response."""

    status: str = Field(default="error", examples=["error"])
    code: str = Field(..., examples=["VALIDATION_ERROR", "INTERNAL_SERVER_ERROR"])
    message: str = Field(..., examples=["Human-readable explanation of error."])
    details: List[Any] = Field(default_factory=list)
