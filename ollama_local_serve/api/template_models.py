"""
Pydantic models for prompt template API request/response schemas.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


# ============================================================================
# Request Models
# ============================================================================


class CreateTemplateRequest(BaseModel):
    """Request to create a new prompt template."""

    name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Unique template name",
    )
    content: str = Field(
        ...,
        min_length=1,
        description="Template with {variable} placeholders",
    )
    description: str | None = Field(
        default=None,
        description="Optional template description",
    )
    category: str | None = Field(
        default=None,
        description="Optional category for organization",
    )
    tags: list[str] = Field(
        default_factory=list,
        description="Tags for filtering and discovery",
    )
    variables: list[str] = Field(
        default_factory=list,
        description="Auto-detected if empty",
    )


class UpdateTemplateRequest(BaseModel):
    """Request to update an existing prompt template."""

    content: str | None = Field(default=None, description="Updated template content")
    description: str | None = Field(default=None, description="Updated description")
    category: str | None = Field(default=None, description="Updated category")
    tags: list[str] | None = Field(default=None, description="Updated tags")
    variables: list[str] | None = Field(default=None, description="Updated variables")


class RenderTemplateRequest(BaseModel):
    """Request to render a template with variables."""

    template_id: str = Field(..., description="Template ID to render")
    variables: dict[str, str] = Field(
        default_factory=dict,
        description="Variable values to substitute",
    )


class TemplateChatRequest(BaseModel):
    """Request to chat using a rendered template."""

    template_id: str = Field(..., description="Template ID to use")
    variables: dict[str, str] = Field(
        default_factory=dict,
        description="Variable values to substitute",
    )
    model: str = Field(..., description="Ollama model to use")
    stream: bool = Field(default=True, description="Whether to stream the response")
    options: dict[str, Any] | None = Field(
        default=None,
        description="Additional Ollama options",
    )


# ============================================================================
# Response Models
# ============================================================================


class TemplateResponse(BaseModel):
    """Response containing a single template."""

    template_id: str
    name: str
    content: str
    description: str | None = None
    category: str | None = None
    tags: list[str] = Field(default_factory=list)
    variables: list[str] = Field(default_factory=list)
    version: int
    created_at: datetime
    updated_at: datetime


class TemplateListResponse(BaseModel):
    """Response containing a list of templates."""

    templates: list[TemplateResponse]
    total: int


class TemplateVersionResponse(BaseModel):
    """Response for a single template version."""

    version: int
    content: str
    updated_at: datetime


class TemplateVersionsListResponse(BaseModel):
    """Response containing version history for a template."""

    template_id: str
    versions: list[TemplateVersionResponse]


class RenderTemplateResponse(BaseModel):
    """Response containing rendered template output."""

    template_id: str
    rendered: str
    variables_used: dict[str, str]
