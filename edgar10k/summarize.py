from typing import Literal
from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel

from tokens import cost, estimate_cost

load_dotenv()
client = OpenAI()

DEFAULT_MODEL = "gpt-6-luna"

INSTRUCTIONS = (
    "You are a financial analyst. Summarize the given section of a company's 10-K "
    "filing for an investor. key_points: the 5-8 most important facts or developments, "
    "with numbers where the text gives them. risks: the most material risks or concerns "
    "raised. sentiment: management's overall tone in this section."
)


# The JSON shape we want back. The SDK turns this into a JSON schema the model must follow.
# (A docstring here would be sent to the model as the schema's description, so this is a comment.)
class SectionSummary(BaseModel):
    section: str
    key_points: list[str]
    risks: list[str]
    sentiment: Literal["positive", "neutral", "negative"]


def summarize(client: OpenAI, name: str, text: str, model: str = DEFAULT_MODEL):
    """Stream a structured summary of one section. Returns (SectionSummary, usage)."""
    with client.responses.stream(
        model=model,
        instructions=INSTRUCTIONS,
        input=f"Section: {name}\n\n{text}",
        text_format=SectionSummary,  # structured outputs: the reply is guaranteed to match the schema
    ) as stream:
        for event in stream:
            if event.type == "response.output_text.delta":
                print(event.delta, end="", flush=True)  # the JSON arrives piece by piece
        response = stream.get_final_response()
    print()

    if response.status != "completed":  # e.g. hit the output limit, so the JSON is cut off
        raise RuntimeError(f"{name}: response {response.status}: {response.incomplete_details}")
    if response.output_parsed is None:  # the model refused instead of answering
        raise RuntimeError(f"{name}: no parsed output (refusal?)")
    return response.output_parsed, response.usage


if __name__ == "__main__":
    import sys

    from sections import split_sections

    with open(sys.argv[1], encoding="utf-8") as f:
        sections = split_sections(f.read())

    client = OpenAI()  # reads OPENAI_API_KEY from the environment
    total = 0.0
    for name, text in sections.items():
        est_tokens, est_cost = estimate_cost(text, DEFAULT_MODEL)
        print(f"\n=== {name}: ~{est_tokens:,} tokens (tiktoken), est. ${est_cost:.4f} ===")

        summary, usage = summarize(client, name, text)
        actual = cost(usage.input_tokens, usage.output_tokens, DEFAULT_MODEL)
        total += actual
        print(
            f"actual: {usage.input_tokens:,} in / {usage.output_tokens:,} out "
            f"({usage.output_tokens_details.reasoning_tokens:,} of those reasoning) = ${actual:.4f}"
        )
        print(summary.model_dump_json(indent=2))

    print(f"\nTotal cost for this filing: ${total:.4f}")
