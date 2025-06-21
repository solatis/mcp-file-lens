# Documentation guidelines

## Function Documentation

Start every function with a single sentence: "This function [action] [what it operates on] to produce [result]."

Then add these lines:
- "It requires: [prerequisites or dependencies, or 'nothing special']"
- "Side effects: [external changes, or 'none']"
- "Commonly used by: [function names that consume this output]"
- "Typical usage: [brief example pattern]"

## Parameter Documentation

For each parameter, write: "[name] must be [constraint], used to [purpose]"
- Constraints: type, range, format (e.g., "a positive integer", "an existing file path")
- Purpose: why this parameter exists in plain language

## Inline Comments

Before complex logic blocks:
"This section [what it does] because [reason]. It modifies [what state]."

At decision points:
"We choose [option] here because [reason]."

For error handling:
"This handles [error type] which occurs when [condition]."

## Marking Relationships

When a function's output feeds another:
"The result from this function goes to [function name]."

When requiring another function's output:
"This needs output from [function name] to work."

For alternative approaches:
"See also [function name] for a different approach."

## State Changes

Document state transitions:
"Before this block: [state description]"
"After this block: [state description]"
"Throughout: [what remains constant]"
