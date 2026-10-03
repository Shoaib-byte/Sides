import tiktoken

# $ per 1M tokens (input, output), Standard tier.
# Source: https://developers.openai.com/api/docs/pricing (checked 2026-10-03). Prices change, re-check them.
PRICES = {
    "gpt-6-luna": (0.10, 0.50),     # cheapest, good default while learning
    "gpt-6.1-sol": (2.00, 10.00),   # smarter, 20x the price
    "gpt-5.4-mini": (0.75, 4.50),
}


def get_encoding(model: str) -> tiktoken.Encoding:
    try:
        return tiktoken.encoding_for_model(model)
    except KeyError:
        # tiktoken doesn't know the GPT-6 tokenizer yet, so this is an estimate.
        # The real count comes back from the API in response.usage.
        return tiktoken.get_encoding("o200k_base")


def count_tokens(text: str, model: str) -> int:
    return len(get_encoding(model).encode(text))


def cost(input_tokens: int, output_tokens: int, model: str) -> float:
    price_in, price_out = PRICES[model]
    return input_tokens / 1_000_000 * price_in + output_tokens / 1_000_000 * price_out


def estimate_cost(text: str, model: str, expected_output_tokens: int = 2000) -> tuple[int, float]:
    """Estimate (input tokens, $) before sending. Output is a guess: you only know it afterwards."""
    input_tokens = count_tokens(text, model)
    return input_tokens, cost(input_tokens, expected_output_tokens, model)
