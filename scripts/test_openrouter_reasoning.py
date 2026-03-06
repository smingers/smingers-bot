import asyncio

from dotenv import load_dotenv
from litellm import acompletion

load_dotenv()


async def main():
    try:
        response = await acompletion(
            model="openrouter/google/gemini-3-flash-preview",
            messages=[
                {
                    "role": "user",
                    "content": "Think step by step and tell me if the word 'apple' is an animal.",
                }
            ],
            max_tokens=500,
            temperature=0.0,
            extra_body={"reasoning": {"max_tokens": 1000}},
        )
        print("--- RESPONSE ---")
        print(response)
        print("\n--- MESSAGE ---")
        print(response.choices[0].message)
        print("\n--- REASONING TOKENS ---")
        print(getattr(response.usage, "completion_tokens_details", None))
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    asyncio.run(main())
