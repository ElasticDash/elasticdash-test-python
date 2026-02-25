# elasticdash_test

Python port of the Elasticdash AI test framework.

## Install

```
pip install elasticdash_test
```

## Usage

```bash
elasticdash test
elasticdash test ./examples
elasticdash run examples/simple_flow.ai_test.py
```

`OPENAI_API_KEY` is required for semantic matchers that call an LLM judge.

See [docs/test-writing-guidelines.md](docs/test-writing-guidelines.md) for authoring tips.

## Writing a test

### Minimal template

```python
# examples/simple_flow.ai_test.py
from elasticdash_test import ai_test, expect

@ai_test("simple trace")
async def test_simple(ctx):
    ctx.trace.record_llm_step(model="gpt-4o-mini", provider="openai", prompt="hi", completion="hello")
    expect(ctx.trace).to_have_llm_step(model="gpt-4o-mini", contains="hello")
```

### Using hooks and interceptors

```python
# examples/checkout_flow.ai_test.py
from elasticdash_test import ai_test, before_all, after_each, install_ai_interceptor, expect

@before_all
def setup_suite():
    install_ai_interceptor()  # auto-captures httpx/requests LLM calls

@after_each
def teardown_each(ctx):
    ctx.trace.record_custom_step(kind="teardown", name="after-each")

@ai_test("flow with hooks")
async def test_flow(ctx):
    # Your app code runs here; below is simulated trace data
    ctx.trace.record_llm_step(model="gpt-4o-mini", provider="openai", prompt="confirm?", completion="confirmed")
    ctx.trace.record_tool_call(name="chargeCard", args={"amount": 100})

    expect(ctx.trace).to_have_llm_step(contains="confirmed")
    expect(ctx.trace).to_call_tool("chargeCard")
```

### Asserting specific steps of a workflow

Match a specific prompt by index or filter:

```python
expect(ctx.trace).to_have_prompt_where(filter_contains="order", nth=0)
expect(ctx.trace).to_have_prompt_where(require_contains="address", require_not_contains="password")
```

Count occurrences of steps:

```python
expect(ctx.trace).to_have_llm_step(model="gpt-4o-mini", min_times=2)
expect(ctx.trace).to_have_custom_step(kind="rag", min_times=1)
expect(ctx.trace).to_call_tool("chargeCard", min_times=1)
```

### Evaluating outputs semantically

Semantic match (requires `OPENAI_API_KEY`):

```python
await expect(ctx.trace).to_match_semantic_output("order confirmed")
```

Score an output against a metric:

```python
score = await expect(ctx.trace).to_evaluate_output_metric(
    evaluation_prompt="Rate clarity 0-1",
    nth=0,
    condition={"at_least": 0.8},
)
```

Run a test file:

```
elasticdash run examples/checkout_flow.ai_test.py
```

## Tips

- Name files `*.ai_test.py` so the CLI auto-discovers them.
- Prefer async tests when calling I/O-bound code.
- Use `before_all`/`after_all` hooks to install and uninstall the AI interceptor once per suite.
- Keep `OPENAI_API_KEY` in your environment for semantic checks.
