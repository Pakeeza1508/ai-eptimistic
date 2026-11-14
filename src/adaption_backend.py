"""Adaption Responses API backend for SourceCheck.

Use only hosted base-model IDs returned by client.models.list(type="hosted").
Do not enable tools, datasets, agentic memory, or an inference stack for the
closed-book experiment. Keys are read from ADAPTION_API_KEY by the SDK.
"""
import os


def call_adaption(model, messages, temperature):
    if not os.getenv("ADAPTION_API_KEY"):
        raise RuntimeError("ADAPTION_API_KEY is missing; set it locally, never commit it")
    from adaption import Adaption

    # Import at call time to keep offline tests and other backends dependency-free.
    from run_experiment import SYSTEM
    client = Adaption(max_retries=0)
    result = client.responses.create(
        model=model,
        instructions=SYSTEM,
        input=[{"role": m["role"], "content": m["content"]}
               for m in messages if m["role"] != "system"],
        max_output_tokens=512,
        temperature=temperature,
        tools=[],
        tool_choice="none",
        agentic_memory=False,
        store=False,
    )
    if result.status != "completed":
        err = getattr(result, "error", None)
        details = getattr(result, "incomplete_details", None)
        raise RuntimeError(f"Adaption response not completed: {result.status}, error={err}, details={details}")
    txt = (getattr(result, "output_text", "") or "").strip()
    if not txt:
        raise RuntimeError("Adaption returned a completed response with no output_text")
    u = getattr(result, "usage", None)
    usage = {"input_tokens": getattr(u, "input_tokens", None),
             "output_tokens": getattr(u, "output_tokens", None)} if u else {}
    return txt, usage


def list_available_hosted_models():
    if not os.getenv("ADAPTION_API_KEY"):
        raise RuntimeError("ADAPTION_API_KEY is missing")
    from adaption import Adaption
    return [{"id": m.id, "display_name": getattr(m, "display_name", None)}
            for m in Adaption(max_retries=0).models.list(type="hosted").data]
