# Split Large Integration Adapter Files (>1000 lines each)

## Overview

Multiple integration adapter files in integration-service exceed 1000 lines: webhooks/auth.py (1192), integrations/ticket_mapping.py (1127), integrations/servicenow_adapter.py (1103), consumers/event_consumer.py (1066), integrations/jira_adapter.py (1061). These large files mix multiple concerns and are difficult to maintain.

## Rationale

Large files violate Single Responsibility Principle and increase merge conflict probability. The adapter files contain credentials handling, API communication, event formatting, rate limiting, and error handling - each of which could be a separate module. Smaller modules improve testability and enable parallel development.

---
*This spec was created from ideation and is pending detailed specification.*
