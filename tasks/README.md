# Task Library

Community-contributed task definitions for Broadside-AI. Each task is a YAML
file that defines a well-scoped unit of work suitable for scatter/gather.

## Schema

```yaml
# Required
prompt: "The instruction each agent receives."

# Optional
context:
  key: "value"                    # Grounding data injected into the prompt
output_schema:
  field_name: "type"              # Expected JSON object shape

# Metadata (for the library, not sent to agents)
meta:
  name: "human_readable_name"
  category: "creative|analytical|classification|summarization|code_review"
  recommended_n: 3
  recommended_strategy: "llm|consensus|voting|weighted_merge"
  description: "What this task demonstrates"
```

## Contributing a task

1. Copy `_template.yaml` to a new file.
2. Write a task that passes the "can you tell if it's done?" test.
3. Run `broadside-ai validate-task tasks/your_task.yaml`.
4. Open a PR. No issue is required.

## Good tasks

- have bounded scope and verifiable outputs
- demonstrate a specific scatter/gather strength
- include context when the prompt alone is ambiguous
- use `output_schema` when the response should be structured

## Strategy hints

- `llm`: best when the desired result is one polished final answer
- `consensus`: best when disagreements or outliers are part of the value
- `voting`: best when the result is a discrete choice or majority position
- `weighted_merge`: best when branches return structured JSON-like data

## Categories

- `creative`: multiple valid outputs, diversity is the point
- `analytical`: structured comparison, consensus matters
- `classification`: discrete or structured labels, voting or weighted merge helps
- `summarization`: information compression, synthesis adds value
- `code_review`: finding issues in parallel, gather catches more
