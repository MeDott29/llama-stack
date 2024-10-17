from llama_stack_client import LlamaStackClient
import json

# Define LlamaStack host/port
host = ""
port = 5000
client = LlamaStackClient(base_url=f"http://{host}:{port}")

# Define the model to use for inference
model = "Llama3.2-1B-Instruct"

# Function to communicate with the model and get ARC puzzle JSON
def get_arc_puzzle_json(user_message):
    iterator = client.inference.chat_completion(
        model=model,
        messages=[
            {"role": "system", "content": "You only respond with a valid JSON string representing an ARC puzzle. Do not include any other output."},
            {"role": "user", "content": user_message}
        ],
        stream=True,
        tool_prompt_format='json'
    )

    json_response = ""
    for chunk in iterator:
        json_response += chunk.event.delta
        print(chunk.event.delta, end="", flush=True)
    
    return json_response

# Recovery function for invalid JSON responses
def evaluate_and_retry(user_message, raw_response):
    print("\n\nError detected in JSON format. Sending instructions to correct...")
    
    # Generate feedback message for model correction
    feedback_message = (
        "The previous response was not valid JSON. "
        "Make sure to return *only* a valid JSON object following the structure "
        "of an ARC puzzle, with no extra text, comments, or errors."
    )

    # Retry inference with feedback appended
    return get_arc_puzzle_json(feedback_message)

# Example usage
symmetry = "|decahedric symmetry|"
user_input = f"Create a simple 3x3 ARC puzzle with {symmetry}. Return only valid JSON."
arc_json_string = get_arc_puzzle_json(user_input)

print("\n\nGenerated ARC Puzzle JSON String:")
print(arc_json_string)

try:
    arc_json = json.loads(arc_json_string)
    print("\n\nParsed ARC Puzzle JSON:")
    print(arc_json)
except json.JSONDecodeError as e:
    print(f"\n\nError decoding JSON: {e}")
    print(f"Raw response: {arc_json_string}")
    
    # Invoke the retry mechanism on failure
    arc_json_string = evaluate_and_retry(user_input, arc_json_string)

    try:
        # Attempt parsing again after retry
        arc_json = json.loads(arc_json_string)
        print("\n\nParsed ARC Puzzle JSON after retry:")
        print(arc_json)
    except json.JSONDecodeError as e:
        print(f"\n\nFailed again: {e}")
        print(f"Final raw response: {arc_json_string}")
