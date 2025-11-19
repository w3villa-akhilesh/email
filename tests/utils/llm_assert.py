import uuid
import json
import os
import openai
from typing import List, Dict, Optional


async def assert_intent_equals(statement1: str, statement2: str) -> bool:
    """
    Uses a direct OpenAI call to compare two statements and determine if their intent is the same.

    Args:
        statement1: The first statement.
        statement2: The second statement.

    Returns:
        True if the intent is the same, False otherwise.
    """
    client = openai.AsyncOpenAI(
        api_key=os.getenv("API_KEY"),
        base_url=os.getenv("API_BASE")
    )
    model = os.getenv("ASSERTION_TOOL_MODEL", "default-model")

    system_prompt = """
You are an expert at comparing the semantic intent of two statements.
Analyze the two statements provided and determine if they have the same core meaning.
Respond with a JSON object with a single boolean field: `{"same_intent": true}` if they have the same intent, and `{"same_intent": false}` otherwise.
"""

    user_prompt = f"""
Statement 1: "{statement1}"
Statement 2: "{statement2}"
"""

    try:
        response = await client.chat.completions.create(
            model=model,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.0
        )
        
        response_text = response.choices[0].message.content
        result = json.loads(response_text)
        return result.get("same_intent", False)

    except (json.JSONDecodeError, AttributeError, openai.APIError) as e:
        print(f"\nAssertion failed due to an error in 'assert_intent_equals': {type(e).__name__}\nDetails: {e}")
        return False


async def assert_intent_present(statement: str, intent: str) -> bool:
    """
    Uses a simple agent to check if a specific intent is present in a statement.

    Args:
        statement: The text to check.
        intent: The intent or information that should be present.

    Returns:
        True if the intent is present, False otherwise.
    """
    return await assert_intents_present(statement, [intent])


async def assert_intents_present(statement: str, intents: List[str]) -> bool:
    """
    Uses a simple agent to check if a list of intents are present in a statement.

    Args:
        statement: The text to check.
        intents: A list of intents or information that should be present.

    Returns:
        True if all intents are present, False otherwise.
    """
    client = openai.AsyncOpenAI(
        api_key=os.getenv("API_KEY"),
        base_url=os.getenv("API_BASE")
    )
    model = os.getenv("ASSERTION_TOOL_MODEL", "default-model")
    
    intent_list_str = "\n".join([f'- "{i}"' for i in intents])

    system_prompt = f"""
You are an expert at analyzing text for specific intents. Your task is to determine if a list of intents is present in a given statement.

You must respond in a JSON format that adheres to the following Pydantic schema:

```python
from pydantic import BaseModel, Field
from typing import Dict, Optional

class VerificationResult(BaseModel):
    present: bool = Field(description="True if the intent is present, False otherwise.")
    reason: Optional[str] = Field(
        default=None,
        description="A brief explanation of why the intent was marked as false. This must be omitted if the intent is present."
    )

class IntentVerification(BaseModel):
    results: Dict[str, VerificationResult]
```

For each intent, you will check for its presence in the statement.
- If an intent is present, set `present` to `true`.
- If an intent is not present, set `present` to `false` and provide a concise `reason`.

Your analysis must be based solely on the provided statement.
"""
    
    user_prompt = f"""
Please verify the following intents:
{intent_list_str}

Based on this statement:
"{statement}"
"""

    try:
        response = await client.chat.completions.create(
            model=model,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.0
        )
        
        response_text = response.choices[0].message.content
        results_dict = json.loads(response_text)

        if "results" in results_dict and isinstance(results_dict["results"], dict):
            results_dict = results_dict["results"]
        else:
             # If the top-level keys match the intents, we can assume the `results` nesting was omitted.
            if all(intent in results_dict for intent in intents):
                pass # The structure is already flat, which is acceptable.
            else:
                 print(f"\nAssertion failed: LLM response JSON does not contain the expected 'results' field.\nResponse: {response_text}")
                 return False

        missing_or_false_intents = []
        for intent in intents:
            result = results_dict.get(intent)
            if not result or not isinstance(result, dict) or not result.get("present"):
                reason = result.get("reason", "No reason provided.") if isinstance(result, dict) else "The assertion agent did not return a valid result for this intent."
                missing_or_false_intents.append((intent, reason))

        if not missing_or_false_intents:
            return True
        else:
            print("\n\n" + "="*80)
            print("LLM-based assertion failed.")
            print("Original statement:")
            print(f"---\n{statement}\n---\n")
            print("The following intents were not found or were marked as false:")
            for intent, reason in missing_or_false_intents:
                print(f"- Intent: {intent}")
                print(f"  Reason: {reason}")
            
            print("\nFailure details from assertion agent:")
            # To avoid re-printing the whole object, we'll just show the failed parts.
            failed_details = {intent: results_dict.get(intent, "Not found") for intent, _ in missing_or_false_intents}
            print(json.dumps(failed_details, indent=2))
            print("="*80 + "\n")
            return False

    except (json.JSONDecodeError, AttributeError, openai.APIError) as e:
        error_message = f"\nAssertion failed due to an error: {type(e).__name__}\nDetails: {e}"
        if hasattr(e, 'response') and e.response:
             error_message += f"\nAPI Response: {e.response.text}"
        print(error_message)
        return False 