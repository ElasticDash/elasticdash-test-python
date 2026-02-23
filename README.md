# elasticdash-test-py

Python port of the Elasticdash AI test framework.

## Install

```
pip install elasticdash-test
```

## Usage

```bash
elasticdash test
elasticdash test ./examples
elasticdash run examples/simple_flow.ai_test.py
```

`OPENAI_API_KEY` is required for semantic matchers that call an LLM judge.

See [docs/test-writing-guidelines.md](docs/test-writing-guidelines.md) for authoring tips.
