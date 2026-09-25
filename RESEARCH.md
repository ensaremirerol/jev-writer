# Jev research notes (2026-09-24)

## What it is
- **Jev** (TypeSafe AI, out of stealth 2026-09-15): the first "System One" model. You give it a **state** and typed **questions**, and it returns typed answers with calibrated probabilities. It does not generate text.
- Trained with **RLCD** (reinforcement learning for calibrated decisions). It is non-autoregressive, so all questions are answered in parallel in one pass.
- Latency is 70–500ms (~100ms typical). Input costs $0.042/MTok, and output is free. The vendor claims it is ~200x faster and ~400x cheaper than LLMs on classification. These are the vendor's own evals and should be treated as a ceiling.
- Jev is not an LLM replacement. The intended pattern is an **LLM for reasoning and generation, with Jev for the fast decisions along the way**.

## Primitives
| Type | Use | Answer |
|---|---|---|
| `Noul` | yes/no | `.noul` = P(yes) |
| `Choice` | pick 1 of N (≤255) | `.choice`, `.probabilities`, `.confidence` |
| `Score` | ordered levels | `.score`, `.legend`, `.probabilities`, `.confidence` |

- State can be a string, a JSON object (preferred), or an array. It is text only and works best in English.
- Confidence = `(n·p_max − 1)/(n − 1)`. Suggested tiers: >0.9 act, 0.5–0.9 act with caution or review, <0.5 route to a human.
- Instructions and criteria accept JSON. You can point at part of the state with backtick paths like `` `ticket.message` ``.

## APIs
- REST: `POST https://api.typesafe.ai/v1/systemone`, with `{state, model:"jev-latest", questions}` and `Authorization: Bearer $TYPESAFE_API_KEY`.
- Python SDK: `pip install typesafe-sdk` → `TypeSafeClient().system_one(state=..., questions=...)`. There is also `AsyncTypeSafeClient`, plus a JS SDK.
- LangChain: `pip install "langchain-typesafe[experimental]"`
  - `TypeSafeClassifier().invoke({"state":..., "questions":{...}})` → `resp.nouls/choices/scores[id]`
  - `ModelRouterMiddleware(choices={name: ModelChoice(model, criteria)}, instructions=...)` routes each request to a model. The chosen route is in `result["model_route"]`.
  - `AutoModeMiddleware(tools=[...], instructions=?, criteria=NoulCriteria(...))` risk-gates tool calls. A call judged risky returns an error `ToolMessage` instead of running.
  - Custom middleware: subclass `AgentMiddleware`, run the classifier in `before_agent`, and write the answer into the agent state.

## Design rules (from the docs)
1. Keep deterministic work in code, because code owns the control flow.
2. Send minimal state. Accuracy drops as irrelevant state grows.
3. Split questions into **atomic** ones. The docs call this the most important rule.
4. Fan out: batch every question, speculative ones included, into one call. In one doc example this was 12.2x cheaper and 10x faster.
5. Combine the answers in code (weights or rules), then gate on confidence.

## Known weak spots (jev-1.13)
- Reads instructions literally.
- Unreliable with counting, math and date arithmetic, so do these in code.
- Struggles with multi-hop reasoning and double negatives.
- Accuracy drops with large irrelevant state.
- Can be steered by adversarial state.
- Gets confused when instructions and criteria contradict each other.
- No P(a)+P(¬a)=1 guarantee across separate questions.
- Poor at text generation.

## Sources
- LangChain post: https://www.langchain.com/blog/building-a-harness-with-jev
- Launch post: https://typesafe.ai/blog/introducing-system-one-models-and-jev
- LangChain integration: https://docs.langchain.com/oss/python/integrations/providers/typesafe
- Docs index: https://docs.typesafe.ai/llms.txt (patterns, 20+ cookbooks, SDK refs)
- Quickstart: https://docs.typesafe.ai/introduction/quickstart
- Build guide: https://docs.typesafe.ai/concepts/how-to-build-with-system-one.md
- Confidence: https://docs.typesafe.ai/confidence
- Jaggedness: https://docs.typesafe.ai/model-jaggedness/jev-1.13.md
- LLM adapter (drop-in `system_one` replacement backed by an LLM, for comparing against Jev): https://github.com/typesafe-ai/system-one-adapter-python
- Agent skill: `claude plugin marketplace add typesafe-ai/skills && claude plugin install typesafe@typesafe-ai`
- Evals: https://evals.typesafe.ai/ · Playground: https://console.typesafe.ai/playground
- Third-party: https://flaviocopes.com/jev/ · https://www.truefoundry.com/blog/typesafe-ai-jev · https://www.mindstudio.ai/blog/jev-system-one-model-launch · https://dev.to/valyuai/how-to-use-jev-a-practical-guide-to-typesafes-system-one-model-g5e · https://www.marktechpost.com/2026/09/19/typesafe-ai-releases-jev/
