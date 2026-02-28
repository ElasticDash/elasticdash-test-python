# elasticdash_test

An AI-native test runner for ElasticDash workflow testing. Built for async AI pipelines — not a general-purpose test runner.

- Trace-first: every test receives a `ctx.trace` to record and assert on LLM calls and tool invocations
- Automatic interception for OpenAI, Gemini, and Grok via `httpx`/`requests` — no manual instrumentation required
- AI-specific matchers: `to_have_llm_step`, `to_call_tool`, `to_match_semantic_output`, `to_have_custom_step`, `to_have_prompt_where`, `to_evaluate_output_metric`
- Sequential execution, no parallelism overhead
- No pytest dependency

---

## Installation

```bash
pip install elasticdash_test
```

Requires Python 3.10+.

---

## Quick Start

**1. Write a test file** (`my_flow.ai_test.py`):

```python
from elasticdash_test import ai_test, expect

@ai_test("checkout flow")
async def test_checkout(ctx):
    await run_checkout(ctx)

    expect(ctx.trace).to_have_llm_step(model="gpt-4o", contains="order confirmed")
    expect(ctx.trace).to_call_tool("chargeCard")
```

**2. Run it:**

```bash
elasticdash test              # discover all *.ai_test.py files
elasticdash test ./ai_tests   # discover in a specific directory
elasticdash run my_flow.ai_test.py  # run a single file
elasticdash dashboard         # open workflows dashboard
```

**3. Read the output:**

```
  ✓ checkout flow (1.2s)
  ✗ refund flow (0.8s)
    → Expected tool "chargeCard" to be called, but no tool calls were recorded

2 passed
1 failed
Total: 3
Duration: 3.4s
```

---

## Writing Tests

See the full guide in [docs/test-writing-guidelines.md](docs/test-writing-guidelines.md).

### Decorators

Import from `elasticdash_test` and apply to functions — no global injection needed:

| Decorator | Description |
|---|---|
| `@ai_test(name)` | Register a test |
| `@before_all` | Run once before all tests in the file |
| `@before_each` | Run before every test in the file |
| `@after_each` | Run after every test in the file (runs even if the test fails) |
| `@after_all` | Run once after all tests in the file |

### Test context

Each test function receives a `ctx: AITestContext` argument:

```python
@ai_test("my test")
async def test_my_flow(ctx):
    # ctx.trace — record and inspect LLM steps and tool calls
```

### Recording trace data

**Automatic interception (recommended):** Call `install_ai_interceptor()` once in `@before_all` and the runner patches `httpx`/`requests` to record LLM steps for OpenAI, Gemini, and Grok calls automatically. See [Automatic AI Interception](#automatic-ai-interception) below.

**Manual recording:** Use this for providers not covered by the interceptor, when testing against stubs/mocks, or to capture custom workflow steps:

```python
ctx.trace.record_llm_step(
    model="gpt-4o",
    prompt="What is the order status?",
    completion="The order has been confirmed.",
)

ctx.trace.record_tool_call(
    name="chargeCard",
    args={"amount": 99.99},
)

# Record custom workflow steps (RAG fetches, code/fixed steps, etc.)
ctx.trace.record_custom_step(
    kind="rag",              # 'rag' | 'code' | 'fixed' | 'custom'
    name="pokemon-search",
    tags=["sort:asc", "source:db"],
    payload={"query": "pikachu attack"},
    result={"ids": [25]},
    metadata={"latency_ms": 120},
)
```

### Matchers

#### `to_have_llm_step(config?)`

Assert the trace contains at least one LLM step matching the given config. All fields are optional and combined with AND logic.

```python
expect(ctx.trace).to_have_llm_step(model="gpt-4o")
expect(ctx.trace).to_have_llm_step(contains="order confirmed")        # searches prompt + completion
expect(ctx.trace).to_have_llm_step(prompt_contains="order status")    # searches prompt only
expect(ctx.trace).to_have_llm_step(output_contains="order confirmed") # searches completion only
expect(ctx.trace).to_have_llm_step(provider="openai")
expect(ctx.trace).to_have_llm_step(provider="openai", prompt_contains="order status")
expect(ctx.trace).to_have_llm_step(prompt_contains="retry", times=3)      # exactly 3 matching steps
expect(ctx.trace).to_have_llm_step(provider="openai", min_times=2)        # at least 2 matching steps
expect(ctx.trace).to_have_llm_step(output_contains="error", max_times=1)  # at most 1 matching step
```

| Field | Description |
|---|---|
| `model` | Exact model name match (e.g. `'gpt-4o'`) |
| `contains` | Substring match across prompt + completion (case-insensitive) |
| `prompt_contains` | Substring match in prompt only (case-insensitive) |
| `output_contains` | Substring match in completion only (case-insensitive) |
| `provider` | Provider name: `'openai'`, `'gemini'`, or `'grok'` |
| `times` | Exact match count (fails unless exactly this many steps match) |
| `min_times` | Minimum match count (steps matching must be ≥ this value) |
| `max_times` | Maximum match count (steps matching must be ≤ this value) |

#### `to_call_tool(tool_name)`

Assert the trace contains a tool call with the given name.

```python
expect(ctx.trace).to_call_tool("chargeCard")
```

#### `to_match_semantic_output(expected, **options)`

LLM-judged semantic match of combined LLM output vs. the expected string. Defaults to OpenAI GPT-4.1 with `OPENAI_API_KEY`.

```python
# Minimal, using default OpenAI model
await expect(ctx.trace).to_match_semantic_output("order confirmed")

# Use a different provider
await expect(ctx.trace).to_match_semantic_output(
    "attack stat",
    provider="claude",
    model="claude-3-opus-20240229",
)

# OpenAI-compatible endpoint (e.g., Moonshot/Kimi) via base_url + api_key
await expect(ctx.trace).to_match_semantic_output(
    "order confirmed",
    provider="openai",
    model="kimi-k2-turbo-preview",
    api_key=os.environ["KIMI_API_KEY"],
    base_url="https://api.moonshot.ai/v1",
)
```

Environment keys by provider: `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GEMINI_API_KEY` (or `GOOGLE_API_KEY`), `GROK_API_KEY`.

#### `to_evaluate_output_metric(config)`

Evaluate one LLM step's prompt or result using an LLM and assert a numeric metric condition in the range 0.0–1.0. Defaults: target=`result`, condition=`at_least 0.7`, provider=`openai`, model=`gpt-4.1`.

```python
# Evaluate the last LLM result; default condition at_least 0.7
await expect(ctx.trace).to_evaluate_output_metric(
    evaluation_prompt="Rate how well this answers the user question.",
)

# Check a specific step (3rd LLM prompt), target the prompt text, require >= 0.8
await expect(ctx.trace).to_evaluate_output_metric(
    evaluation_prompt="Score coherence of this prompt between 0 and 1.",
    target="prompt",
    nth=3,
    condition={"at_least": 0.8},
    provider="claude",
    model="claude-3-opus-20240229",
)

# Custom comparator: score must be < 0.3
await expect(ctx.trace).to_evaluate_output_metric(
    evaluation_prompt="Rate hallucination risk (0=none, 1=high).",
    condition={"less_than": 0.3},
)
```

Options:
- `evaluation_prompt` (required): your scoring instructions; model is asked to return only a number between 0 and 1.
- `target`: `'result'` (default) or `'prompt'`. Evaluates that text only.
- `nth`: pick which LLM step to score (1-based). Defaults to the last LLM step.
- `condition`: one of `greater_than`, `less_than`, `at_least`, `at_most`, `equals`; default is `{"at_least": 0.7}`. Fails if the score is outside 0.0–1.0 or cannot be parsed.
- `provider` / `model` / `api_key` / `base_url`: supports OpenAI, Claude, Gemini, Grok, and OpenAI-compatible endpoints via `base_url`.

#### `to_have_custom_step(config?)`

Assert a recorded custom step (RAG/code/fixed/custom) matches filters.

```python
expect(ctx.trace).to_have_custom_step(kind="rag", name="pokemon-search")
expect(ctx.trace).to_have_custom_step(tag="sort:asc")
expect(ctx.trace).to_have_custom_step(contains="pikachu")
expect(ctx.trace).to_have_custom_step(result_contains="25")
expect(ctx.trace).to_have_custom_step(kind="rag", min_times=1, max_times=2)
```

#### `to_have_prompt_where(config)`

Filter prompts, then assert additional constraints. Example: "all prompts containing A must also contain B".

```python
# Prompts that contain "order" must also contain "confirmed"
expect(ctx.trace).to_have_prompt_where(filter_contains="order", require_contains="confirmed")

# Prompts containing "retry" must NOT contain "cancel"
expect(ctx.trace).to_have_prompt_where(filter_contains="retry", require_not_contains="cancel")

# Control counts on the filtered subset
expect(ctx.trace).to_have_prompt_where(
    filter_contains="order",
    require_contains="confirmed",
    min_times=1,
    max_times=3,
)

# Check a specific prompt position (1-based nth)
expect(ctx.trace).to_have_prompt_where(
    filter_contains="order",
    require_contains="confirmed",
    nth=3,  # the 3rd prompt among those containing "order"
)
```

---

## Automatic AI Interception

Call `install_ai_interceptor()` in a `@before_all` hook and the runner patches `httpx` and `requests` before tests run, automatically recording LLM steps for:

| Provider | Endpoints intercepted |
|---|---|
| **OpenAI** | `api.openai.com/v1/chat/completions`, `/v1/completions` |
| **Gemini** | `generativelanguage.googleapis.com/.../models/...:generateContent` |
| **Grok** (xAI) | `api.x.ai/v1/chat/completions` |

Each intercepted call records `model`, `provider`, `prompt`, and `completion` into `ctx.trace` automatically. Your workflow code needs no changes.

```python
from elasticdash_test import ai_test, before_all, after_all, install_ai_interceptor, uninstall_ai_interceptor, expect

@before_all
def setup():
    install_ai_interceptor()

@after_all
def teardown():
    uninstall_ai_interceptor()

@ai_test("user lookup flow")
async def test_user_lookup(ctx):
    # This makes a real OpenAI call — intercepted automatically
    await my_workflow.run("Find all active users")

    # Works without any ctx.trace.record_llm_step() in your workflow
    expect(ctx.trace).to_have_llm_step(prompt_contains="Find all active users")
    expect(ctx.trace).to_have_llm_step(provider="openai")
```

**Streaming:** When `stream=True` is set on a request, the completion is recorded as `"(streamed)"` — the prompt and model are still captured.

### Recording trace steps without passing `ctx.trace` (contextvars)

The runner sets a per-test `current_trace` using Python's `contextvars`, so your app code can record steps without threading `ctx.trace` through every function:

```python
# In your test
from elasticdash_test import ai_test, set_current_trace, expect

@ai_test("flow test")
async def test_flow(ctx):
    set_current_trace(ctx.trace)        # bind the trace to the current async context
    await run_flow_without_trace_arg()  # your existing code
    expect(ctx.trace).to_have_custom_step(kind="rag", name="pokemon-search")

# In your app/flow code (called during the test)
from elasticdash_test import get_current_trace

async def run_flow_without_trace_arg():
    trace = get_current_trace()
    if trace:
        trace.record_custom_step(
            kind="rag",
            name="pokemon-search",
            payload={"query": "pikachu attack"},
            result={"ids": [25]},
            tags=["source:db", "sort:asc"],
        )
```

---

## Configuration

Create an optional `elasticdash.config.py` at the project root:

```python
config = {
    "test_match": ["**/*.ai_test.py"],
    "trace_mode": "local",
}
```

| Option | Default | Description |
|---|---|---|
| `test_match` | `['**/*.ai_test.py']` | Glob patterns for test discovery |
| `trace_mode` | `'local'` | `'local'` (stub) or `'remote'` (future ElasticDash backend) |

### `ed_agents.py`, `ed_workflows.py`, `ed_tools.py`

These optional files are thin wrappers that bundle and re-export existing functions from your codebase. Load them automatically during test runs to provide agents, workflows, and tools to your test environment.

#### `ed_agents.py`

Re-export agent functions or create a config dict for easy reference:

```python
# ed_agents.py — import from your app
from my_app.agents import checkout_agent, payment_agent

config = {
    "checkout": checkout_agent,
    "payment": payment_agent,
}
```

Access in tests:

```python
@ai_test("checkout flow")
async def test_checkout(ctx, config):
    agents = config.get("agents", {})
    result = await agents["checkout"]("order-123")
```

#### `ed_workflows.py`

Re-export workflow functions from your application:

```python
# ed_workflows.py
from my_app.workflows import order_workflow, refund_workflow

# Re-export directly — the runner will import this module
```

Access in tests:

```python
@ai_test("full order workflow")
async def test_workflow(ctx):
    from ed_workflows import order_workflow
    result = await order_workflow("order-123", "cust-456")
    expect(ctx.trace).to_call_tool("chargeCard")
```

#### `ed_tools.py`

Re-export tool functions that agents or workflows can invoke:

```python
# ed_tools.py
from my_app.tools import charge_card, fetch_order_status, send_notification
```

Access in tests or workflows:

```python
@ai_test("tool integration")
async def test_tools(ctx):
    from ed_tools import fetch_order_status
    status = await fetch_order_status("order-123")
    expect(ctx.trace).to_have_custom_step(kind="external", name="fetch_order_status")
```

These files are loaded automatically if present in the project root.

## Workflows Dashboard

Browse and search all available workflow functions in your project:

```bash
elasticdash dashboard         # open dashboard at http://localhost:4573
elasticdash dashboard --port 4572  # use custom port
elasticdash dashboard --no-open    # skip auto-opening browser
```

The dashboard scans `ed_workflows.py` and displays:
- **Function names** — all callable functions in the module
- **Signatures** — function parameters and return types
- **Async indicator** — marks async vs sync functions
- **Source module** — where the function is imported from (if not locally defined)
- **File path** — location of `ed_workflows.py`

Use the search field to filter workflows by:
- **Name** — find workflow by function name (e.g., `checkout_flow`)
- **Source module** — find all workflows from a specific module (e.g., `app_workflows`)
- **File path** — filter by location in your codebase

This is useful for discovering available workflows, understanding their signatures, and identifying where functions are defined before calling them in tests.

## Project Structure

```
elasticdash_test/
  cli.py                CLI entry point (click + glob)
  runner.py             Sequential test runner engine
  reporter.py           Color-coded terminal output
  registry.py           ai_test / before_all / after_all registry
  trace.py              TraceHandle, AITestContext, contextvars support
  matchers.py           Custom expect matchers
  interceptors/
    ai_interceptor.py   Automatic httpx/requests interceptor for OpenAI / Gemini / Grok
```

---

## Programmatic API

```python
from elasticdash_test import install_ai_interceptor, uninstall_ai_interceptor
from elasticdash_test.runner import run_files
from elasticdash_test.reporter import print_results

install_ai_interceptor()  # patch httpx/requests for automatic LLM tracing

results = await run_files(["./tests/flow.ai_test.py"])
print_results(results)

uninstall_ai_interceptor()  # restore original transports when done
```

---

## Non-Goals

This runner intentionally does not support:

- Parallel execution
- Watch mode
- Snapshot testing
- Coverage reporting
- pytest compatibility

---

## License

MIT
