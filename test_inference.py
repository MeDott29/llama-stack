from llama_stack_client import LlamaStackClient

def test_text_inference():
    # Initialize client
    client = LlamaStackClient(base_url="http://localhost:5001")
    
    # Test parameters
    model_id = "meta-llama/Llama-3.2-1B-Instruct"
    
    try:
        # Simple text completion test
        print("Testing text inference...")
        response = client.inference.chat_completion(
            model_id=model_id,
            messages=[
                {
                    "role": "user",
                    "content": "Write a short greeting in one sentence."
                }
            ],
            stream=True
        )
        
        print("Response:")
        for chunk in response:
            print(chunk.event.delta, end="", flush=True)
        print("\n")
        
        return True
        
    except Exception as e:
        print(f"Error during inference: {str(e)}")
        return False

if __name__ == "__main__":
    print("Starting Llama Stack inference test...")
    success = test_text_inference()
    print(f"\nTest {'succeeded' if success else 'failed'}") 