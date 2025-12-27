# ACGS-2 Code Style & Conventions

## Python Code Style
- **Type Hints**: Strict typing enforced throughout
- **Imports**: Absolute imports preferred; relative for fallbacks
- **Async/Await**: Comprehensive async support required
- **Naming**: snake_case for functions/variables, CamelCase for classes

## Error Handling
- Use specific exceptions from `enhanced_agent_bus/exceptions.py`
- 22 custom exception types available:
  - `ConstitutionalError` - Constitutional violations
  - `MessageError` - Message processing issues
  - `AgentError` - Agent-related errors
  - `PolicyError` - Policy enforcement failures

## Constitutional References
- Always include constitutional hash in docstrings and comments
- Hash: `cdd01ef066bc6cf2`
- Required in all message processing and file headers

## Documentation
- Docstrings for all public functions
- Type hints for all parameters and return values
- Constitutional context in class-level docstrings
