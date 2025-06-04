# Python Coding Style Guidelines

The following coding style rules, extracted from analyzing the codebase, represent best practices applicable to this Python project:

## 1. Module Organization
- Group imports into three sections: standard library, third-party packages, local modules
- Place all constants at module top level using UPPERCASE
- Use clear section headers (e.g., "Constants", "Classes", "Functions")
- Order classes/functions: public first, private (with underscore prefix) last

## 2. Documentation
- Include detailed module docstrings explaining purpose and functionality
- Document all functions/methods with Args, Returns, Raises sections
- Add examples in docstrings showing typical usage
- Use inline comments sparingly, only for complex logic explanation

## 3. Types and Type Hints
- Use type hints consistently for function parameters and return values
- Employ Optional[] for nullable values and Union[] for multiple types
- Apply dataclasses for data-focused classes
- Include generic types when needed (e.g., TypeVar)

## 4. Function and Method Design
- Follow single responsibility principle
- Keep functions focused and under 50 lines where possible
- Use descriptive parameter names
- Provide default values for optional parameters
- Validate inputs early
- Return explicit values (avoid implicit None returns)

## 5. Error Handling
- Use custom exceptions for domain-specific errors
- Always include context in error messages
- Chain exceptions with "raise ... from exc"
- Use context managers (with statements) for resource handling
- Avoid bare except clauses

## 6. Code Style
- Follow 4-space indentation
- Limit line length to 79 characters (88 for modern projects)
- Use vertical whitespace to group related code
- Apply consistent naming: PascalCase for classes, lowercase_with_underscores for functions/variables
- Keep functions/methods short and focused
- Place related code in contiguous blocks

## 7. Testing and Maintainability
- Write testable functions with clear inputs/outputs
- Avoid global state
- Use dependency injection where appropriate
- Make dependencies explicit
- Keep interfaces stable and well-documented
- Consider edge cases in design

## 8. File Operations
- Use pathlib instead of os.path
- Handle paths as Path objects rather than strings
- Always use context managers for file operations
- Validate file operations and handle errors explicitly
- Apply proper encoding/decoding for file content

## 9. Performance Considerations
- Use list comprehensions over map() or filter()
- Employ generators for large data sets
- Consider memory usage in data structures
- Cache expensive computations when appropriate
- Profile before optimizing

## 10. Security Best Practices
- Sanitize all file paths and names
- Validate all inputs before processing
- Use secure defaults
- Never trust external data
- Handle secrets and credentials securely