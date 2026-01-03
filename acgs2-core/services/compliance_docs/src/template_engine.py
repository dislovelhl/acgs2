"""
ACGS-2 Compliance Documentation Template Engine

Configures Jinja2 template engine with security-focused autoescaping
and performance optimization for enterprise compliance documentation.
"""

from datetime import datetime, timezone
from functools import lru_cache
from os import getenv
from pathlib import Path
from typing import Any, Optional

from jinja2 import (
    Environment,
    FileSystemLoader,
    select_autoescape,
    TemplateNotFound,
)


# Default templates path relative to service directory
_DEFAULT_TEMPLATES_PATH = Path(__file__).parent / "templates"


def _get_templates_path() -> Path:
    """
    Resolve templates path from environment or use default.

    Returns:
        Path to templates directory.
    """
    templates_path = getenv("COMPLIANCE_TEMPLATES_PATH")
    if templates_path:
        return Path(templates_path)
    return _DEFAULT_TEMPLATES_PATH


def _format_date(value: datetime, format_str: str = "%Y-%m-%d") -> str:
    """
    Format a datetime object to string.

    Args:
        value: The datetime to format.
        format_str: strftime format string.

    Returns:
        Formatted date string.
    """
    if value is None:
        return "N/A"
    if isinstance(value, str):
        return value
    return value.strftime(format_str)


def _format_datetime(value: datetime, format_str: str = "%Y-%m-%d %H:%M:%S UTC") -> str:
    """
    Format a datetime object with time to string.

    Args:
        value: The datetime to format.
        format_str: strftime format string.

    Returns:
        Formatted datetime string.
    """
    if value is None:
        return "N/A"
    if isinstance(value, str):
        return value
    return value.strftime(format_str)


def _default_value(value: Any, default: str = "N/A") -> str:
    """
    Return a default value if the input is None or empty.

    This filter ensures graceful handling of missing compliance data.

    Args:
        value: The value to check.
        default: The default string to return if value is None/empty.

    Returns:
        The value or default string.
    """
    if value is None or value == "":
        return default
    return str(value)


def _status_badge(status: str) -> str:
    """
    Convert status to a display badge format.

    Args:
        status: The status string (e.g., 'compliant', 'non_compliant', 'pending').

    Returns:
        HTML-safe badge representation.
    """
    status_map = {
        "compliant": "[COMPLIANT]",
        "non_compliant": "[NON-COMPLIANT]",
        "not_compliant": "[NON-COMPLIANT]",
        "pending": "[PENDING]",
        "in_progress": "[IN PROGRESS]",
        "not_applicable": "[N/A]",
        "partial": "[PARTIAL]",
    }
    normalized = str(status).lower().replace("-", "_").replace(" ", "_")
    return status_map.get(normalized, f"[{str(status).upper()}]")


def _control_id_format(control_id: str, framework: str = "") -> str:
    """
    Format control ID for consistent display.

    Args:
        control_id: The raw control ID.
        framework: Optional framework prefix.

    Returns:
        Formatted control ID string.
    """
    if not control_id:
        return "N/A"
    if framework:
        return f"{framework.upper()}-{control_id}"
    return str(control_id)


def _pluralize(count: int, singular: str, plural: Optional[str] = None) -> str:
    """
    Return singular or plural form based on count.

    Args:
        count: The count to check.
        singular: Singular form of the word.
        plural: Plural form (defaults to singular + 's').

    Returns:
        Appropriate form of the word with count.
    """
    if plural is None:
        plural = singular + "s"
    word = singular if count == 1 else plural
    return f"{count} {word}"


def _now_utc() -> datetime:
    """
    Return current UTC datetime.

    Returns:
        Current datetime in UTC.
    """
    return datetime.now(timezone.utc)


def _current_year() -> int:
    """
    Return current year.

    Returns:
        Current year as integer.
    """
    return datetime.now(timezone.utc).year


def _create_environment(templates_path: Path) -> Environment:
    """
    Create and configure a Jinja2 Environment.

    Args:
        templates_path: Path to templates directory.

    Returns:
        Configured Jinja2 Environment with autoescaping and custom filters.
    """
    env = Environment(
        loader=FileSystemLoader(str(templates_path)),
        autoescape=select_autoescape(
            enabled_extensions=["html", "htm", "xml", "xhtml"],
            default_for_string=True,
            default=True,
        ),
        # Performance: Enable bytecode caching
        auto_reload=True,  # Development: reload templates on change
        trim_blocks=True,
        lstrip_blocks=True,
        keep_trailing_newline=True,
    )

    # Register custom filters
    env.filters["format_date"] = _format_date
    env.filters["format_datetime"] = _format_datetime
    env.filters["default_value"] = _default_value
    env.filters["status_badge"] = _status_badge
    env.filters["control_id"] = _control_id_format
    env.filters["pluralize"] = _pluralize

    # Register global functions/variables
    env.globals["now_utc"] = _now_utc
    env.globals["current_year"] = _current_year

    return env


@lru_cache(maxsize=1)
def get_template_env() -> Environment:
    """
    Get or create the cached Jinja2 template environment.

    This function is cached to ensure a single Environment instance
    is reused across the application for optimal performance.

    Returns:
        Configured Jinja2 Environment with autoescaping enabled.

    Example:
        >>> env = get_template_env()
        >>> template = env.get_template("soc2/control_mapping.html.j2")
        >>> html = template.render(controls=controls_data)
    """
    templates_path = _get_templates_path()

    # Ensure templates directory exists
    if not templates_path.exists():
        templates_path.mkdir(parents=True, exist_ok=True)

    return _create_environment(templates_path)


def render_template(
    template_name: str,
    context: dict[str, Any],
    framework: Optional[str] = None,
) -> str:
    """
    Render a compliance template with the given context.

    Args:
        template_name: Name of the template file (e.g., 'control_mapping.html.j2').
        context: Dictionary of variables to pass to the template.
        framework: Optional framework subdirectory (e.g., 'soc2', 'iso27001').

    Returns:
        Rendered template as string.

    Raises:
        TemplateNotFound: If the template does not exist.

    Example:
        >>> html = render_template(
        ...     "control_mapping.html.j2",
        ...     {"controls": controls},
        ...     framework="soc2"
        ... )
    """
    env = get_template_env()

    # Build full template path
    if framework:
        full_template_name = f"{framework}/{template_name}"
    else:
        full_template_name = template_name

    template = env.get_template(full_template_name)

    # Add framework to context if provided
    render_context = dict(context)
    if framework:
        render_context.setdefault("framework", framework)

    # Add generation metadata
    render_context.setdefault("generated_at", _now_utc())
    render_context.setdefault("generator_version", "1.0.0")

    return template.render(**render_context)


def template_exists(template_name: str, framework: Optional[str] = None) -> bool:
    """
    Check if a template exists.

    Args:
        template_name: Name of the template file.
        framework: Optional framework subdirectory.

    Returns:
        True if template exists, False otherwise.
    """
    env = get_template_env()

    if framework:
        full_template_name = f"{framework}/{template_name}"
    else:
        full_template_name = template_name

    try:
        env.get_template(full_template_name)
        return True
    except TemplateNotFound:
        return False


def list_templates(framework: Optional[str] = None) -> list[str]:
    """
    List available templates, optionally filtered by framework.

    Args:
        framework: Optional framework to filter by (e.g., 'soc2', 'iso27001').

    Returns:
        List of template names.
    """
    env = get_template_env()
    all_templates = env.loader.list_templates()

    if framework:
        prefix = f"{framework}/"
        return [t for t in all_templates if t.startswith(prefix)]

    return all_templates


def clear_template_cache() -> None:
    """
    Clear the template environment cache.

    This is useful for testing or when templates are updated at runtime.
    """
    get_template_env.cache_clear()
