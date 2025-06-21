# Code guidelines

## Function Design
- Keep functions under 20 lines
- One function, one purpose
- Return early on error conditions
- Make dependencies explicit as parameters

## Code Structure
- Extract common patterns into functions
- Group related functionality in modules
- Prefer composition over inheritance
- Fail fast with clear errors

## Naming
- Use descriptive names that explain purpose
- Avoid abbreviations and acronyms
- Be consistent with naming patterns
- Boolean names should ask questions (is_valid, has_data)

## Error Handling
- Validate inputs at boundaries
- Throw specific exceptions
- Handle errors at the right level
- Never silence errors without logging

## State Management
- Minimize mutable state
- Make state changes explicit
- Avoid global variables
- Prefer immutable data structures

## Dependencies
- Inject dependencies, don't hard-code
- Keep external dependencies minimal
- Mock external services in tests
- Version lock all dependencies