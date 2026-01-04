"""
Factory functions for creating default ticket mapping configurations.

This module provides factory functions for quickly creating standard mapping
configurations for Jira and ServiceNow ticketing systems. These configurations
can be used as-is or customized for specific organizational needs.
"""

from typing import Any, Dict, List, Optional

from .enums import FieldMappingType, FieldValidationType, TicketingProvider
from .models import FieldMapping, FieldValidationRule, TicketMappingConfig


def create_jira_mapping_config(
    name: str = "Default Jira Mapping",
    project_key: str = "GOV",
    issue_type: str = "Bug",
    labels: Optional[List[str]] = None,
    summary_template: str = "[ACGS-2] {title}",
    severity_mapping: Optional[Dict[str, str]] = None,
    custom_fields: Optional[Dict[str, Any]] = None,
) -> TicketMappingConfig:
    """
    Create a default Jira ticket mapping configuration.

    Args:
        name: Configuration name
        project_key: Jira project key
        issue_type: Jira issue type
        labels: Labels to add to tickets
        summary_template: Template for ticket summary
        severity_mapping: Custom severity to priority mapping
        custom_fields: Additional custom field mappings

    Returns:
        TicketMappingConfig for Jira
    """
    if labels is None:
        labels = ["governance", "acgs2"]

    field_mappings = [
        FieldMapping(
            target_field="project",
            mapping_type=FieldMappingType.STATIC,
            static_value={"key": project_key},
            required=True,
        ),
        FieldMapping(
            target_field="issuetype",
            mapping_type=FieldMappingType.STATIC,
            static_value={"name": issue_type},
            required=True,
        ),
        FieldMapping(
            target_field="summary",
            mapping_type=FieldMappingType.TEMPLATE,
            template=summary_template,
            required=True,
            validation_rules=[
                FieldValidationRule(
                    validation_type=FieldValidationType.MAX_LENGTH,
                    value=255,
                    error_message="Jira summary must be 255 characters or less",
                ),
            ],
        ),
        FieldMapping(
            target_field="priority",
            mapping_type=FieldMappingType.TRANSFORM,
            transform_name="severity_to_jira_priority",
            transform_params={"mapping": severity_mapping or {}},
        ),
        FieldMapping(
            target_field="labels",
            mapping_type=FieldMappingType.TRANSFORM,
            transform_name="build_labels",
            transform_params={
                "base_labels": labels,
                "include_severity": True,
                "include_event_type": True,
            },
        ),
    ]

    # Add custom field mappings
    if custom_fields:
        for field_id, value in custom_fields.items():
            field_mappings.append(
                FieldMapping(
                    target_field=field_id,
                    mapping_type=FieldMappingType.STATIC,
                    static_value=value,
                )
            )

    return TicketMappingConfig(
        name=name,
        provider=TicketingProvider.JIRA,
        summary_template=summary_template,
        field_mappings=field_mappings,
        jira_settings={
            "project_key": project_key,
            "issue_type": issue_type,
        },
    )


def create_servicenow_mapping_config(
    name: str = "Default ServiceNow Mapping",
    category: str = "Governance",
    subcategory: Optional[str] = None,
    assignment_group: Optional[str] = None,
    summary_template: str = "[ACGS-2] {title}",
    severity_mapping: Optional[Dict[str, str]] = None,
    additional_fields: Optional[Dict[str, Any]] = None,
) -> TicketMappingConfig:
    """
    Create a default ServiceNow incident mapping configuration.

    Args:
        name: Configuration name
        category: Incident category
        subcategory: Incident subcategory
        assignment_group: Assignment group for incidents
        summary_template: Template for short description
        severity_mapping: Custom severity to impact/urgency mapping
        additional_fields: Additional field mappings

    Returns:
        TicketMappingConfig for ServiceNow
    """
    field_mappings = [
        FieldMapping(
            target_field="short_description",
            mapping_type=FieldMappingType.TEMPLATE,
            template=summary_template,
            required=True,
            validation_rules=[
                FieldValidationRule(
                    validation_type=FieldValidationType.MAX_LENGTH,
                    value=160,
                    error_message="ServiceNow short_description must be 160 characters or less",
                ),
            ],
        ),
        FieldMapping(
            target_field="category",
            mapping_type=FieldMappingType.STATIC,
            static_value=category,
        ),
        FieldMapping(
            target_field="impact",
            mapping_type=FieldMappingType.TRANSFORM,
            transform_name="severity_to_servicenow_impact",
            transform_params={"mapping": severity_mapping or {}},
        ),
        FieldMapping(
            target_field="urgency",
            mapping_type=FieldMappingType.TRANSFORM,
            transform_name="severity_to_servicenow_urgency",
            transform_params={"mapping": severity_mapping or {}},
        ),
    ]

    if subcategory:
        field_mappings.append(
            FieldMapping(
                target_field="subcategory",
                mapping_type=FieldMappingType.STATIC,
                static_value=subcategory,
            )
        )

    if assignment_group:
        field_mappings.append(
            FieldMapping(
                target_field="assignment_group",
                mapping_type=FieldMappingType.STATIC,
                static_value=assignment_group,
            )
        )

    # Add additional field mappings
    if additional_fields:
        for field_name, value in additional_fields.items():
            field_mappings.append(
                FieldMapping(
                    target_field=field_name,
                    mapping_type=FieldMappingType.STATIC,
                    static_value=value,
                )
            )

    return TicketMappingConfig(
        name=name,
        provider=TicketingProvider.SERVICENOW,
        summary_template=summary_template,
        field_mappings=field_mappings,
        servicenow_settings={
            "category": category,
            "subcategory": subcategory,
            "assignment_group": assignment_group,
        },
    )


__all__ = [
    "create_jira_mapping_config",
    "create_servicenow_mapping_config",
]
