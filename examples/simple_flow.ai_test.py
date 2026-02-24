from elasticdash_test import ai_test, before_all, after_all, before_each, after_each, expect, install_ai_interceptor, uninstall_ai_interceptor


@before_all
def setup_suite():
    install_ai_interceptor()


@after_all
def teardown_suite():
    uninstall_ai_interceptor()


@before_each
def before_each_test(ctx):
    ctx.trace.record_custom_step(kind="setup", name="before-each")


@after_each
def after_each_test(ctx):
    ctx.trace.record_custom_step(kind="teardown", name="after-each")


@ai_test("dummy flow")
async def test_dummy(ctx):
    # Simulate trace data
    ctx.trace.record_llm_step(model="gpt-4o-mini", provider="openai", prompt="hello", completion="world")
    ctx.trace.record_tool_call(name="chargeCard", args={"amount": 100})
    expect(ctx.trace).to_have_llm_step(model="gpt-4o-mini")
    expect(ctx.trace).to_call_tool("chargeCard")


# Failing example: wrong prompt order
@ai_test("failing prompt order")
async def test_failing_prompt_order(ctx):
    ctx.trace.record_llm_step(model="gpt-4o-mini", provider="openai", prompt="step B", completion="done B")
    ctx.trace.record_llm_step(model="gpt-4o-mini", provider="openai", prompt="step A", completion="done A")
    # Expect step A first, this will fail
    expect(ctx.trace).to_have_prompt_where(filter_contains="step A", nth=0)


# Failing example: missing tool call
@ai_test("failing missing tool")
async def test_failing_missing_tool(ctx):
    ctx.trace.record_llm_step(model="gpt-4o-mini", provider="openai", prompt="hello", completion="world")
    # Expecting a tool call that never happened
    expect(ctx.trace).to_call_tool("nonexistentTool")
