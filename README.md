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

## Writing a test (quick example)

```python
# examples/checkout_flow.ai_test.py
from elasticdash_test import ai_test, before_all, before_each, after_each, install_ai_interceptor, uninstall_ai_interceptor, expect

@before_all
def setup_suite():
	# Capture httpx/requests LLM calls automatically
	install_ai_interceptor()

@after_each
def teardown_each(ctx):
	# You can assert cleanup steps here
	ctx.trace.record_custom_step(kind="teardown", name="after-each")

@ai_test("checkout confirms order")
async def test_checkout(ctx):
	# Your app code runs here (sync or async). Simulate trace records:
	ctx.trace.record_llm_step(model="gpt-4o-mini", provider="openai", prompt="confirm order?", completion="order confirmed")
	ctx.trace.record_tool_call(name="chargeCard", args={"amount": 42})

	# Assertions on trace
	expect(ctx.trace).to_have_llm_step(model="gpt-4o-mini", contains="confirmed")
	expect(ctx.trace).to_call_tool("chargeCard")

	# Optional semantic judge (needs OPENAI_API_KEY)
	await expect(ctx.trace).to_match_semantic_output("order confirmed")
```

Run it:

```
elasticdash run examples/checkout_flow.ai_test.py
```
