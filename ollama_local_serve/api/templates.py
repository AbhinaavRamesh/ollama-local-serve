"""
Prompt template library and management engine.

Provides template CRUD operations, variable detection,
versioning, and rendering with {variable} placeholder substitution.
"""

import re
import threading
import time
import uuid
from dataclasses import dataclass, field


# ============================================================================
# Data Models
# ============================================================================


@dataclass
class TemplateVersion:
    """A snapshot of a template's content at a specific version."""

    version: int
    content: str
    updated_at: float


@dataclass
class PromptTemplate:
    """A prompt template with variable placeholders and version history."""

    template_id: str
    name: str
    content: str
    description: str | None = None
    category: str | None = None
    tags: list[str] = field(default_factory=list)
    variables: list[str] = field(default_factory=list)
    version: int = 1
    versions: list[TemplateVersion] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)


# ============================================================================
# Template Manager
# ============================================================================


class TemplateManager:
    """
    Thread-safe manager for prompt templates.

    Handles creation, retrieval, update, deletion, versioning,
    and rendering of prompt templates with {variable} placeholders.
    """

    def __init__(self, max_templates: int = 500, enable_versioning: bool = True):
        self.max_templates = max_templates
        self.enable_versioning = enable_versioning
        self._templates: dict[str, PromptTemplate] = {}
        self._name_index: dict[str, str] = {}  # name -> template_id
        self._lock = threading.Lock()

    def create_template(
        self,
        name: str,
        content: str,
        description: str | None = None,
        category: str | None = None,
        tags: list[str] | None = None,
        variables: list[str] | None = None,
    ) -> PromptTemplate:
        """
        Create a new prompt template.

        Args:
            name: Unique template name.
            content: Template content with {variable} placeholders.
            description: Optional description.
            category: Optional category for organization.
            tags: Optional tags for filtering.
            variables: Variable names. Auto-detected from content if empty.

        Returns:
            The created PromptTemplate.

        Raises:
            ValueError: If name is duplicate or max templates exceeded.
        """
        if tags is None:
            tags = []
        if not variables:
            variables = re.findall(r"\{(\w+)\}", content)

        with self._lock:
            if name in self._name_index:
                raise ValueError(f"Template with name '{name}' already exists")

            if len(self._templates) >= self.max_templates:
                raise ValueError(
                    f"Maximum number of templates ({self.max_templates}) exceeded"
                )

            template_id = str(uuid.uuid4())
            now = time.time()

            initial_version = TemplateVersion(
                version=1,
                content=content,
                updated_at=now,
            )

            template = PromptTemplate(
                template_id=template_id,
                name=name,
                content=content,
                description=description,
                category=category,
                tags=tags,
                variables=variables,
                version=1,
                versions=[initial_version],
                created_at=now,
                updated_at=now,
            )

            self._templates[template_id] = template
            self._name_index[name] = template_id

            return template

    def get_template(self, template_id: str) -> PromptTemplate | None:
        """Get a template by ID."""
        with self._lock:
            return self._templates.get(template_id)

    def get_template_by_name(self, name: str) -> PromptTemplate | None:
        """Get a template by name."""
        with self._lock:
            tid = self._name_index.get(name)
            if tid is None:
                return None
            return self._templates.get(tid)

    def list_templates(
        self,
        category: str | None = None,
        tag: str | None = None,
    ) -> list[PromptTemplate]:
        """
        List templates, optionally filtered by category and/or tag.

        Args:
            category: Filter by category if provided.
            tag: Filter by tag if provided.

        Returns:
            List of matching templates.
        """
        with self._lock:
            templates = list(self._templates.values())

        if category is not None:
            templates = [t for t in templates if t.category == category]
        if tag is not None:
            templates = [t for t in templates if tag in t.tags]

        return templates

    def update_template(
        self,
        template_id: str,
        content: str | None = None,
        description: str | None = None,
        category: str | None = None,
        tags: list[str] | None = None,
        variables: list[str] | None = None,
    ) -> PromptTemplate | None:
        """
        Update an existing template.

        If content changes and versioning is enabled, the old content
        is saved as a version and the version number is incremented.

        Args:
            template_id: ID of the template to update.
            content: New content (optional).
            description: New description (optional).
            category: New category (optional).
            tags: New tags (optional).
            variables: New variables (optional). Auto-detected if content
                       changes and variables not provided.

        Returns:
            The updated template, or None if not found.
        """
        with self._lock:
            template = self._templates.get(template_id)
            if template is None:
                return None

            now = time.time()

            if content is not None and content != template.content:
                if self.enable_versioning:
                    old_version = TemplateVersion(
                        version=template.version,
                        content=template.content,
                        updated_at=template.updated_at,
                    )
                    template.versions.append(old_version)

                template.content = content
                template.version += 1

                # Re-detect variables if not explicitly provided
                if variables is None:
                    template.variables = re.findall(r"\{(\w+)\}", content)

            if description is not None:
                template.description = description
            if category is not None:
                template.category = category
            if tags is not None:
                template.tags = tags
            if variables is not None:
                template.variables = variables

            template.updated_at = now

            return template

    def delete_template(self, template_id: str) -> bool:
        """
        Delete a template by ID.

        Returns:
            True if the template was deleted, False if not found.
        """
        with self._lock:
            template = self._templates.pop(template_id, None)
            if template is None:
                return False
            self._name_index.pop(template.name, None)
            return True

    def get_versions(self, template_id: str) -> list[TemplateVersion]:
        """
        Get version history for a template.

        Returns:
            List of TemplateVersion objects, or empty list if not found.
        """
        with self._lock:
            template = self._templates.get(template_id)
            if template is None:
                return []
            return list(template.versions)

    @staticmethod
    def render(template_content: str, variables: dict[str, str]) -> str:
        """
        Render a template by substituting {variable} placeholders.

        Args:
            template_content: Template string with {variable} placeholders.
            variables: Mapping of variable names to values.

        Returns:
            Rendered string with all placeholders substituted.

        Raises:
            ValueError: If any required variable is missing from the dict.
        """
        found_vars = re.findall(r"\{(\w+)\}", template_content)
        missing = [v for v in found_vars if v not in variables]
        if missing:
            raise ValueError(f"Missing required variables: {', '.join(missing)}")

        result = template_content
        for var in found_vars:
            result = result.replace("{" + var + "}", variables[var])
        return result

    def render_template(self, template_id: str, variables: dict[str, str]) -> str:
        """
        Render a template by ID with the given variables.

        Args:
            template_id: ID of the template to render.
            variables: Variable values to substitute.

        Returns:
            Rendered string.

        Raises:
            ValueError: If template not found or variables missing.
        """
        template = self.get_template(template_id)
        if template is None:
            raise ValueError(f"Template '{template_id}' not found")
        return self.render(template.content, variables)


# ============================================================================
# Module-level Singleton
# ============================================================================

_template_manager: TemplateManager | None = None
_manager_lock = threading.Lock()


def get_template_manager() -> TemplateManager:
    """
    Get or create the global TemplateManager singleton.

    Configuration is read from AppConfig().templates.
    """
    global _template_manager
    if _template_manager is None:
        with _manager_lock:
            if _template_manager is None:
                from ollama_local_serve.config import AppConfig

                config = AppConfig()
                tmpl_config = config.templates
                _template_manager = TemplateManager(
                    max_templates=tmpl_config.max_templates,
                    enable_versioning=tmpl_config.enable_versioning,
                )
    return _template_manager
