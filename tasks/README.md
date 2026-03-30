# Task Library

Community-contributed task definitions for Broadside. Each task is a YAML file
that defines a well-scoped unit of work suitable for scatter/gather.

## Schema

```yaml
# Required
prompt: "The instruction each agent receives."

# Optional
context:
  key: "value"              # Grounding data injected into the prompt
output_schema:
  field_name: "type"        # Expected output shape for validation

# Metadata (for the library, not sent to agents)
meta:
  name: "human_readable_name"
  category: "creative|analytical|classification|summarization|code_review"
  recommended_n: 3          # Suggested agent count
  recommended_strategy: "llm|consensus|voting"
  description: "What this task demonstrates"
```

## Contributing a Task

1. Copy `_template.yaml` to a new file
2. Write a task that passes the "can you tell if it's done?" test
3. Run `python -m broadside.task_validator tasks/your_task.yaml`
4. Open a PR — no issue required

## Good Tasks

- Have bounded scope and verifiable outputs
- Demonstrate a specific scatter/gather strength
- Include context when the prompt alone is ambiguous
- Use output_schema when the response should be structured

## Categories

- **creative**: Multiple valid outputs, diversity is the point
- **analytical**: Structured comparison, consensus matters
- **classification**: Discrete answers, voting helps
- **summarization**: Information compression, synthesis adds value
- **code_review**: Finding issues in parallel, gather catches more
