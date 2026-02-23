# Test Writing Guidelines

- Name files `*.ai_test.py` so the CLI discovers them.
- Import decorators from `elasticdash_test`: `ai_test`, `before_all`, `after_all`, `before_each`, `after_each`.
- Use the provided `expect` matchers on the per-test `ctx.trace` to assert LLM calls, tool calls, and custom steps.
- Keep tests async when they perform I/O; sync functions are supported but run in the same event loop.
- Optional: call `install_ai_interceptor()` during setup to auto-capture OpenAI/Gemini/Grok requests via `httpx`/`requests`.
- Use `await expect(ctx.trace).to_match_semantic_output("expected text")` for semantic comparisons (requires `OPENAI_API_KEY`).
