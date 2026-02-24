# Test Writing Guidelines

- Name files `*.ai_test.py` so the CLI discovers them.
- Import decorators from `elasticdash_test`: `ai_test`, `before_all`, `after_all`, `before_each`, `after_each`.
- Use the provided `expect` matchers on the per-test `ctx.trace` to assert LLM calls, tool calls, and custom steps.
- Keep tests async when they perform I/O; sync functions are supported but run in the same event loop.
- Optional: call `install_ai_interceptor()` during setup to auto-capture OpenAI/Gemini/Grok requests via `httpx`/`requests`.
- Use `await expect(ctx.trace).to_match_semantic_output("expected text")` for semantic comparisons (requires `OPENAI_API_KEY`).

## Minimal test template

```python
from elasticdash_test import ai_test, expect

@ai_test("simple trace")
async def test_simple(ctx):
    ctx.trace.record_llm_step(model="gpt-4o-mini", provider="openai", prompt="hi", completion="hello")
    expect(ctx.trace).to_have_llm_step(model="gpt-4o-mini", contains="hello")
```

## Using hooks and interceptors

```python
from elasticdash_test import ai_test, before_all, before_each, after_each, install_ai_interceptor, uninstall_ai_interceptor, expect

@before_all
def setup_suite():
    install_ai_interceptor()  # auto-captures httpx/requests LLM calls

@after_each
def teardown_each(ctx):
    ctx.trace.record_custom_step(kind="teardown", name="after-each")

@ai_test("flow with hooks")
async def test_flow(ctx):
    # your app code goes here; below is simulated trace data
    ctx.trace.record_llm_step(model="gpt-4o-mini", provider="openai", prompt="confirm?", completion="confirmed")
    ctx.trace.record_tool_call(name="chargeCard", args={"amount": 100})

    expect(ctx.trace).to_have_llm_step(contains="confirmed")
    expect(ctx.trace).to_call_tool("chargeCard")
```

## Asserting specific steps of a workflow

Match nth prompt or filter prompts:

```python
expect(ctx.trace).to_have_prompt_where(filter_contains="order", nth=0)
expect(ctx.trace).to_have_prompt_where(require_contains="address", require_not_contains="password")
```

Count occurrences:

```python
expect(ctx.trace).to_have_llm_step(model="gpt-4o-mini", min_times=2)
expect(ctx.trace).to_have_custom_step(kind="rag", min_times=1)
```

Validate tool calls:

```python
expect(ctx.trace).to_call_tool("chargeCard", min_times=1)
```

## Evaluating inputs/outputs semantically

Semantic judge (needs `OPENAI_API_KEY`):

```python
await expect(ctx.trace).to_match_semantic_output("order confirmed")
```

Score an output against a metric/prompt:

```python
score = await expect(ctx.trace).to_evaluate_output_metric(
    evaluation_prompt="Rate clarity 0-1",
    nth=0,
    condition={"at_least": 0.8},
)
```

## Tips

- Prefer async tests when calling I/O-bound code.
- Use hooks to set up shared fixtures and interceptors.
- Keep `OPENAI_API_KEY` in your environment for semantic checks.
- For full trace auto-capture, call `install_ai_interceptor()` once in `before_all` and `uninstall_ai_interceptor()` in `after_all` if needed.
