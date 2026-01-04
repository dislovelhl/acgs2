# Integrations ticket_mapping.py Structure Analysis

**File:** `integration-service/src/integrations/ticket_mapping.py`
**Line Count:** 1127 lines
**Purpose:** Ticket field mapping configuration and validation framework for ACGS-2 Integration Service

## Executive Summary

This file provides a comprehensive framework for mapping governance events to ticketing system fields (Jira, ServiceNow). It supports template-based field values, severity/priority mapping, custom field transformations, and validation. The file is well-structured with clear separation of concerns between models, validators, transformers, and the main mapper class, making it an excellent candidate for splitting into focused modules.

## File Structure Overview

```
ticket_mapping.py (1127 lines)
├── Imports (lines 16-24)
├── Enums (lines 34-79) - 5 enum classes
├── Default Mappings (lines 86-111) - 3 constant dicts
├── Pydantic Models (lines 119-318) - 6 model classes
├── Field Validators (lines 326-421) - 1 validator class
├── Field Transformers (lines 428-573) - 1 registry class + 10 transform functions
├── Ticket Field Mapper (lines 580-930) - 1 main mapper class
└── Factory Functions (lines 937-1127) - 2 factory functions
```

## Detailed Component Analysis

### 1. Enums (lines 34-79)

**Purpose:** Define types and standard values for ticket mapping

| Enum Class | Lines | Values | Purpose |
|------------|-------|--------|---------|
| `TicketingProvider` | 34-38 | JIRA, SERVICENOW | Supported ticketing providers |
| `FieldMappingType` | 41-48 | STATIC, TEMPLATE, EVENT_FIELD, TRANSFORM, CONDITIONAL | Types of field mapping strategies |
| `FieldValidationType` | 51-60 | REQUIRED, MAX_LENGTH, MIN_LENGTH, REGEX, ALLOWED_VALUES, NUMERIC_RANGE, DATE_FORMAT | Types of field validation |
| `JiraPriority` | 63-70 | HIGHEST, HIGH, MEDIUM, LOW, LOWEST | Standard Jira priority levels |
| `ServiceNowImpactUrgency` | 73-78 | HIGH="1", MEDIUM="2", LOW="3" | ServiceNow impact/urgency values |

**Dependencies:**
- `enum.Enum` (standard library)

**Used by:**
- Models (FieldMapping, TicketMappingConfig)
- Validators (FieldValidator)
- Transformers (severity mapping functions)
- Factory functions

### 2. Default Mappings (lines 86-111)

**Purpose:** Pre-defined severity-to-priority/impact/urgency mappings

| Constant | Lines | Type | Purpose |
|----------|-------|------|---------|
| `DEFAULT_JIRA_PRIORITY_MAP` | 87-93 | `Dict[EventSeverity, JiraPriority]` | Maps EventSeverity to JiraPriority |
| `DEFAULT_SERVICENOW_IMPACT_MAP` | 96-102 | `Dict[EventSeverity, ServiceNowImpactUrgency]` | Maps EventSeverity to ServiceNow impact |
| `DEFAULT_SERVICENOW_URGENCY_MAP` | 105-111 | `Dict[EventSeverity, ServiceNowImpactUrgency]` | Maps EventSeverity to ServiceNow urgency |

**Dependencies:**
- `EventSeverity` (from `.base`)
- `JiraPriority`, `ServiceNowImpactUrgency` (from enums above)

**Used by:**
- Transform functions (severity_to_jira_priority, severity_to_servicenow_impact, etc.)
- TicketFieldMapper.get_priority()

### 3. Pydantic Models (lines 119-318)

#### 3.1 FieldValidationRule (lines 119-130)

**Purpose:** Validation rule for a ticket field

**Fields:**
- `validation_type: FieldValidationType` - Type of validation to perform
- `value: Optional[Any]` - Value for the validation (e.g., max length, regex pattern)
- `error_message: Optional[str]` - Custom error message for validation failure

**Configuration:**
- `model_config = ConfigDict(frozen=True)` - Immutable after creation

**Dependencies:**
- `pydantic.BaseModel`, `ConfigDict`, `Field`
- `FieldValidationType` enum

**Used by:**
- `FieldMapping` (validation_rules field)
- `FieldValidator` class

#### 3.2 FieldMapping (lines 133-199)

**Purpose:** Configuration for mapping a single field

**Fields:**
- `target_field: str` - Name of the target field in the ticketing system
- `mapping_type: FieldMappingType` - How the field value should be determined
- `static_value: Optional[Any]` - Static value (for STATIC type)
- `template: Optional[str]` - Template string with {placeholders} (for TEMPLATE type)
- `source_field: Optional[str]` - Event field to map from (for EVENT_FIELD type)
- `transform_name: Optional[str]` - Name of transform function (for TRANSFORM type)
- `transform_params: Dict[str, Any]` - Parameters for transform function
- `conditions: List[Dict[str, Any]]` - Conditions for CONDITIONAL mapping
- `default_value: Optional[Any]` - Default value if no condition matches
- `validation_rules: List[FieldValidationRule]` - Validation rules
- `required: bool` - Whether this field is required
- `description: Optional[str]` - Description of this field mapping
- `provider_specific: Dict[str, Any]` - Provider-specific configuration

**Validators:**
- `validate_mapping_config()` (lines 181-199) - Ensures appropriate values for mapping type

**Dependencies:**
- `pydantic.BaseModel`, `ConfigDict`, `Field`, `model_validator`
- `FieldMappingType` enum
- `FieldValidationRule` model

**Used by:**
- `TicketMappingConfig` (field_mappings list)
- `TicketFieldMapper._map_field()`

#### 3.3 SeverityMapping (lines 202-222)

**Purpose:** Mapping configuration for severity to priority/impact/urgency

**Fields:**
- `critical: str` - Value for CRITICAL severity
- `high: str` - Value for HIGH severity
- `medium: str` - Value for MEDIUM severity
- `low: str` - Value for LOW severity
- `info: str` - Value for INFO severity

**Methods:**
- `get_value(severity: EventSeverity) -> str` - Get the mapped value for a severity level

**Configuration:**
- `model_config = ConfigDict(frozen=True)` - Immutable after creation

**Dependencies:**
- `pydantic.BaseModel`, `ConfigDict`, `Field`
- `EventSeverity` (from `.base`)

**Used by:**
- `TicketMappingConfig` (severity_mapping field)
- `TicketFieldMapper.get_priority()`

#### 3.4 TicketMappingConfig (lines 225-288)

**Purpose:** Complete ticket field mapping configuration

**Fields:**
- `id: str` - Unique identifier for this mapping configuration
- `name: str` - Name of this mapping configuration
- `provider: TicketingProvider` - Ticketing provider this configuration is for
- `description: Optional[str]` - Description of this mapping configuration
- `field_mappings: List[FieldMapping]` - List of field mappings to apply
- `severity_mapping: Optional[SeverityMapping]` - Custom severity to priority/impact mapping
- `summary_template: str` - Template for ticket summary/short description (default: "[ACGS-2] {title}")
- `description_template: Optional[str]` - Template for ticket description
- `jira_settings: Dict[str, Any]` - Jira-specific settings
- `servicenow_settings: Dict[str, Any]` - ServiceNow-specific settings
- `enabled: bool` - Whether this mapping is enabled
- `created_at: datetime` - Creation timestamp
- `updated_at: datetime` - Last update timestamp

**Methods:**
- `get_field_mapping(target_field: str) -> Optional[FieldMapping]` - Get mapping for specific field

**Dependencies:**
- `pydantic.BaseModel`, `ConfigDict`, `Field`
- `datetime`, `timezone`
- `TicketingProvider` enum
- `FieldMapping`, `SeverityMapping` models

**Used by:**
- `TicketFieldMapper` (config parameter)
- Factory functions (return type)

#### 3.5 FieldMappingResult (lines 291-302)

**Purpose:** Result of applying a field mapping

**Fields:**
- `field_name: str` - Name of the mapped field
- `value: Any` - Computed value for the field
- `success: bool` - Whether mapping succeeded (default: True)
- `error_message: Optional[str]` - Error message if mapping failed
- `validation_errors: List[str]` - List of validation errors

**Dependencies:**
- `pydantic.BaseModel`, `ConfigDict`, `Field`

**Used by:**
- `TicketMappingResult` (field_results list)
- `TicketFieldMapper._map_field()` (return type)

#### 3.6 TicketMappingResult (lines 305-318)

**Purpose:** Result of applying all field mappings for a ticket

**Fields:**
- `success: bool` - Whether all required mappings succeeded (default: True)
- `fields: Dict[str, Any]` - Mapped field values
- `field_results: List[FieldMappingResult]` - Individual field mapping results
- `validation_errors: List[str]` - Overall validation errors
- `warnings: List[str]` - Non-fatal warnings

**Dependencies:**
- `pydantic.BaseModel`, `ConfigDict`, `Field`
- `FieldMappingResult` model

**Used by:**
- `TicketFieldMapper.map_event()` (return type)

### 4. Field Validators (lines 326-421)

#### 4.1 FieldValidator (lines 326-420)

**Purpose:** Validates field values against rules

**Methods:**
| Method | Lines | Type | Purpose |
|--------|-------|------|---------|
| `validate()` | 329-353 | @staticmethod | Validate a value against a list of rules |
| `_validate_rule()` | 355-420 | @staticmethod | Validate a single rule |

**Validation Logic:**
- `REQUIRED`: Value not None/empty
- `MAX_LENGTH`: String length <= max
- `MIN_LENGTH`: String length >= min
- `REGEX`: Value matches regex pattern
- `ALLOWED_VALUES`: Value in allowed list
- `NUMERIC_RANGE`: Numeric value within min/max range

**Dependencies:**
- `re` (regex matching)
- `FieldValidationRule` model
- `FieldValidationType` enum

**Used by:**
- `TicketFieldMapper._map_field()` - Field value validation

### 5. Field Transformers (lines 428-573)

#### 5.1 FieldTransformers (lines 432-455)

**Purpose:** Registry for transform functions

**Class Attributes:**
- `_registry: Dict[str, TransformFunc]` - Registered transform functions

**Methods:**
| Method | Lines | Type | Purpose |
|--------|-------|------|---------|
| `register()` | 437-445 | @classmethod | Decorator to register a transform function |
| `get()` | 447-450 | @classmethod | Get a registered transform function by name |
| `list_transforms()` | 452-455 | @classmethod | List all registered transform names |

**Dependencies:**
- `TransformFunc` type alias (line 429)
- `IntegrationEvent` (from `.base`)

**Used by:**
- Transform functions (decorator)
- `TicketFieldMapper._apply_transform()`

#### 5.2 Built-in Transform Functions (lines 459-573)

**Purpose:** Pre-registered transform functions for common operations

| Transform Function | Lines | Returns | Purpose |
|-------------------|-------|---------|---------|
| `severity_to_jira_priority` | 459-465 | `str` | Convert event severity to Jira priority name |
| `severity_to_servicenow_impact` | 468-474 | `str` | Convert event severity to ServiceNow impact value |
| `severity_to_servicenow_urgency` | 477-483 | `str` | Convert event severity to ServiceNow urgency value |
| `format_timestamp` | 486-490 | `str` | Format event timestamp to a specific format |
| `format_tags` | 493-497 | `str` | Format event tags as a string |
| `build_labels` | 500-515 | `List[str]` | Build a list of labels from event data |
| `truncate` | 518-528 | `str` | Truncate a field value to max length |
| `json_details` | 531-544 | `str` | Format event details as JSON string |
| `concatenate` | 547-559 | `str` | Concatenate multiple event fields |
| `map_value` | 562-572 | `Any` | Map a field value using a lookup table |

**Dependencies:**
- `IntegrationEvent` (from `.base`)
- `json` module (for json_details)
- Default mapping constants

**Used by:**
- `TicketFieldMapper._apply_transform()` - Called by name
- Factory functions (referenced in field mappings)

### 6. Ticket Field Mapper (lines 580-930)

#### 6.1 TicketFieldMapper (lines 580-929)

**Purpose:** Maps governance events to ticket fields using configurable mappings

**Class Attributes:**
- `TEMPLATE_PATTERN: re.Pattern` - Regex pattern for template placeholders `{field}`

**Constructor Parameters:**
- `config: TicketMappingConfig` - Ticket mapping configuration

**Instance Variables:**
- `config: TicketMappingConfig`
- `_custom_transforms: Dict[str, TransformFunc]` - Custom transform functions

**Properties:**
- `provider: TicketingProvider` (lines 607-610) - Get the ticketing provider

**Methods:**
| Method | Lines | Visibility | Purpose |
|--------|-------|-----------|---------|
| `register_transform()` | 612-620 | Public | Register a custom transform function |
| `map_event()` | 622-664 | Public | Map an event to ticket fields |
| `_map_field()` | 666-696 | Private | Map a single field |
| `_compute_value()` | 698-717 | Private | Compute field value based on mapping type |
| `_apply_template()` | 719-738 | Private | Apply template with event field placeholders |
| `_get_event_field()` | 740-762 | Private | Get field value from event (supports nested paths) |
| `_apply_transform()` | 764-790 | Private | Apply a transform function |
| `_apply_conditional()` | 792-830 | Private | Apply conditional logic |
| `_evaluate_condition()` | 832-856 | Private | Evaluate a single condition |
| `get_summary()` | 858-868 | Public | Get ticket summary using configured template |
| `get_priority()` | 870-888 | Public | Get priority value for a severity level |
| `validate_config()` | 890-929 | Public | Validate the mapping configuration |

**Dependencies:**
- `re` (template pattern matching)
- `logging.logger`
- `TicketMappingConfig`, `TicketMappingResult`, `FieldMappingResult`
- `FieldValidator`
- `FieldTransformers`
- `FieldMappingType` enum
- `IntegrationEvent` (from `.base`)
- `EventSeverity` (from `.base`)
- Default mapping constants

**Used by:**
- Would be used by jira_adapter.py and servicenow_adapter.py
- Tests (once created)

**Conditional Operators Supported:**
- `eq`: equals
- `ne`: not equals
- `gt`, `gte`, `lt`, `lte`: comparison
- `in`: value in list
- `contains`: string contains
- `regex`: regex match

### 7. Factory Functions (lines 937-1127)

**Purpose:** Convenient constructor functions for common mapping configurations

#### 7.1 create_jira_mapping_config() (lines 937-1028)

**Purpose:** Create a default Jira ticket mapping configuration

**Parameters:**
- `name: str` - Configuration name (default: "Default Jira Mapping")
- `project_key: str` - Jira project key (default: "GOV")
- `issue_type: str` - Jira issue type (default: "Bug")
- `labels: Optional[List[str]]` - Labels to add to tickets (default: ["governance", "acgs2"])
- `summary_template: str` - Template for ticket summary (default: "[ACGS-2] {title}")
- `severity_mapping: Optional[Dict[str, str]]` - Custom severity to priority mapping
- `custom_fields: Optional[Dict[str, Any]]` - Additional custom field mappings

**Returns:** `TicketMappingConfig` for Jira

**Field Mappings Created:**
1. `project` - STATIC mapping with project key
2. `issuetype` - STATIC mapping with issue type
3. `summary` - TEMPLATE mapping with max length validation (255 chars)
4. `priority` - TRANSFORM mapping using `severity_to_jira_priority`
5. `labels` - TRANSFORM mapping using `build_labels`
6. Custom fields (if provided)

**Dependencies:**
- `TicketMappingConfig`, `FieldMapping`, `FieldValidationRule`
- `TicketingProvider`, `FieldMappingType`, `FieldValidationType` enums

#### 7.2 create_servicenow_mapping_config() (lines 1031-1127)

**Purpose:** Create a default ServiceNow incident mapping configuration

**Parameters:**
- `name: str` - Configuration name (default: "Default ServiceNow Mapping")
- `category: str` - Incident category (default: "Governance")
- `subcategory: Optional[str]` - Incident subcategory
- `assignment_group: Optional[str]` - Assignment group for incidents
- `summary_template: str` - Template for short description (default: "[ACGS-2] {title}")
- `severity_mapping: Optional[Dict[str, str]]` - Custom severity to impact/urgency mapping
- `additional_fields: Optional[Dict[str, Any]]` - Additional field mappings

**Returns:** `TicketMappingConfig` for ServiceNow

**Field Mappings Created:**
1. `short_description` - TEMPLATE mapping with max length validation (160 chars)
2. `category` - STATIC mapping with category value
3. `impact` - TRANSFORM mapping using `severity_to_servicenow_impact`
4. `urgency` - TRANSFORM mapping using `severity_to_servicenow_urgency`
5. `subcategory` - STATIC mapping (if provided)
6. `assignment_group` - STATIC mapping (if provided)
7. Additional fields (if provided)

**Dependencies:**
- `TicketMappingConfig`, `FieldMapping`, `FieldValidationRule`
- `TicketingProvider`, `FieldMappingType`, `FieldValidationType` enums

## External Dependencies

### Imported from Other Modules:
1. **`.base.EventSeverity`** - Enum defining event severity levels
   - Used by: Default mappings, SeverityMapping, transform functions, TicketFieldMapper
   - Location: `integration-service/src/integrations/base.py`

2. **`.base.IntegrationEvent`** - Event model to be mapped
   - Used by: Transform functions, TicketFieldMapper
   - Location: `integration-service/src/integrations/base.py`

### Standard Library:
- `logging` - Logging
- `re` - Regular expressions (template placeholders, conditional regex)
- `datetime`, `timezone` - Timestamps
- `enum.Enum` - Enum definitions
- `typing` - Type hints (Any, Callable, Dict, List, Optional)

### Third-Party:
- `pydantic` - Data validation and models
  - `BaseModel`, `ConfigDict`, `Field`, `model_validator`

## Files That Likely Import from ticket_mapping.py

Based on the implementation plan and code structure:

1. **`integration-service/src/integrations/jira_adapter.py`** (to be updated)
   - Would import:
     - `TicketFieldMapper`
     - `TicketMappingConfig`
     - `create_jira_mapping_config`
     - `TicketingProvider`

2. **`integration-service/src/integrations/servicenow_adapter.py`** (to be updated)
   - Would import:
     - `TicketFieldMapper`
     - `TicketMappingConfig`
     - `create_servicenow_mapping_config`
     - `TicketingProvider`

3. **Future test file** `integration-service/tests/integrations/test_ticket_mapping.py`
   - Would import most classes for testing

## Proposed Split Strategy

Based on the analysis, here's the recommended module structure:

```
integrations/ticket_mapping/
├── __init__.py                  # Public API exports
├── enums.py                     # All 5 enums + default mappings (lines 34-111)
├── models.py                    # 6 pydantic models (lines 119-318)
├── validators.py                # FieldValidator class (lines 326-421)
├── transformers.py              # FieldTransformers class + 10 transform functions (lines 428-573)
├── mapper.py                    # TicketFieldMapper class (lines 580-930)
└── defaults.py                  # Factory functions (lines 937-1127)
```

### Module Size Estimates:

| Module | Estimated Lines | Primary Concerns |
|--------|----------------|------------------|
| `enums.py` | ~100 | Enums + default mapping constants |
| `models.py` | ~230 | 6 pydantic models with validators |
| `validators.py` | ~110 | FieldValidator class with validation logic |
| `transformers.py` | ~170 | Registry + 10 transform functions |
| `mapper.py` | ~380 | TicketFieldMapper with all mapping logic |
| `defaults.py` | ~220 | 2 factory functions |
| `__init__.py` | ~70 | Public API exports |
| **Total** | **~1,280** | (includes imports, docstrings) |

### Import Dependencies Between Modules:

```
enums.py
├── .base (EventSeverity)
└── (standard library only)

models.py
├── enums.py (all enums)
├── .base (EventSeverity)
└── pydantic

validators.py
├── models.py (FieldValidationRule)
├── enums.py (FieldValidationType)
└── re

transformers.py
├── .base (IntegrationEvent, EventSeverity)
├── enums.py (default mappings, JiraPriority, ServiceNowImpactUrgency)
└── json

mapper.py
├── models.py (all models)
├── validators.py (FieldValidator)
├── transformers.py (FieldTransformers, TransformFunc)
├── enums.py (FieldMappingType, TicketingProvider, default mappings)
└── .base (IntegrationEvent, EventSeverity)

defaults.py
├── models.py (TicketMappingConfig, FieldMapping, FieldValidationRule)
├── enums.py (TicketingProvider, FieldMappingType, FieldValidationType)
└── typing

__init__.py
└── (imports from all modules for backward compatibility)
```

### Backward Compatibility Strategy:

The `__init__.py` will re-export all public APIs to maintain backward compatibility:

```python
# integrations/ticket_mapping/__init__.py
from .enums import (
    TicketingProvider,
    FieldMappingType,
    FieldValidationType,
    JiraPriority,
    ServiceNowImpactUrgency,
    DEFAULT_JIRA_PRIORITY_MAP,
    DEFAULT_SERVICENOW_IMPACT_MAP,
    DEFAULT_SERVICENOW_URGENCY_MAP,
)
from .models import (
    FieldValidationRule,
    FieldMapping,
    SeverityMapping,
    TicketMappingConfig,
    FieldMappingResult,
    TicketMappingResult,
)
from .validators import FieldValidator
from .transformers import FieldTransformers, TransformFunc
from .mapper import TicketFieldMapper
from .defaults import (
    create_jira_mapping_config,
    create_servicenow_mapping_config,
)

__all__ = [
    # Enums
    "TicketingProvider",
    "FieldMappingType",
    "FieldValidationType",
    "JiraPriority",
    "ServiceNowImpactUrgency",
    # Default Mappings
    "DEFAULT_JIRA_PRIORITY_MAP",
    "DEFAULT_SERVICENOW_IMPACT_MAP",
    "DEFAULT_SERVICENOW_URGENCY_MAP",
    # Models
    "FieldValidationRule",
    "FieldMapping",
    "SeverityMapping",
    "TicketMappingConfig",
    "FieldMappingResult",
    "TicketMappingResult",
    # Validators
    "FieldValidator",
    # Transformers
    "FieldTransformers",
    "TransformFunc",
    # Mapper
    "TicketFieldMapper",
    # Factory Functions
    "create_jira_mapping_config",
    "create_servicenow_mapping_config",
]
```

This ensures that existing code like `from integrations.ticket_mapping import TicketFieldMapper` continues to work without changes.

## Key Findings

1. **Well-organized code**: File has clear logical sections with excellent separation of concerns
2. **Clean dependency tree**: No circular dependencies; clear flow from enums -> models -> validators/transformers -> mapper -> factories
3. **Minimal external imports**: Only depends on `EventSeverity` and `IntegrationEvent` from `.base`
4. **Extensible design**: Transform registry allows custom transforms; mapper supports plugin pattern
5. **Comprehensive validation**: Multiple validation types with custom error messages
6. **Type safety**: Extensive use of pydantic models and type hints
7. **Provider agnostic**: Clean abstraction over Jira and ServiceNow differences

## Recommendations

1. **Split in this order**:
   - enums.py (minimal dependencies)
   - models.py (depends on enums)
   - validators.py (depends on models, enums)
   - transformers.py (depends on enums, external base)
   - mapper.py (depends on models, validators, transformers, enums)
   - defaults.py (depends on models, enums)
   - __init__.py (imports everything)

2. **Maintain backward compatibility**: Use __init__.py to re-export all public APIs

3. **Update adapter imports**: After split, update jira_adapter.py and servicenow_adapter.py to import from `ticket_mapping` package

4. **Consider future enhancements**:
   - Add more transform functions (e.g., markdown formatting, HTML escaping)
   - Add additional ticketing providers (Linear, GitHub Issues, etc.)
   - Add caching for frequently used mappings
   - Keep each module under 400 lines

## Conclusion

The `integrations/ticket_mapping.py` file is an excellent candidate for splitting. It has:
- Clear logical sections that map to single responsibilities
- No complex interdependencies between components
- Well-defined interfaces (registry pattern for transforms)
- Strong typing and validation throughout
- Provider-agnostic design with extensibility built in

The proposed 7-module structure will result in all modules being under 400 lines, significantly improving maintainability while preserving all functionality and backward compatibility. The clean separation will also make it easier to add new ticketing providers and transform functions in the future.
