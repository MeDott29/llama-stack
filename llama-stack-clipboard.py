import pyperclip
import time
import os
import shutil
from PIL import Image
import hashlib
import base64
import json
from datetime import datetime
from pathlib import Path
import colorama
from colorama import Fore, Style
from typing import List, Dict
from llama_stack_client import LlamaStackClient
from collections import deque
from threading import Thread, Lock
from queue import Queue, Empty as QueueEmpty
import signal
from experimental.novelty_tracker import NoveltyTracker, PERFORMANCE_CONFIG as NOVELTY_CONFIG
import yaml

# Configuration
ASSETS_DIR = os.path.expanduser("~/Desktop/llama-pile/assets")
LOG_FILE = os.path.expanduser("~/Desktop/llama-pile/clipboard_log.txt")
DATASET_FILE = os.path.expanduser("~/Desktop/llama-pile/clipboard_dataset.jsonl")
SCREENSHOTS_DIR = os.path.expanduser("~/Screenshots")

# Performance Configuration
PERFORMANCE_CONFIG = {
    "batch_size": 5,
    "poll_interval": 0.5,
    "max_queue_size": 100,
    "min_content_length": 10,
    
    "concurrent_agents": 2,
    "history_size": 1000
}

# Update with novelty settings
PERFORMANCE_CONFIG.update(NOVELTY_CONFIG)

# Llama Stack Configuration
AI_CONFIG = {
    "provider": "meta-reference",
    "model_id": "meta-llama/Llama-3.2-1B-Instruct",
    "environment": "single-node",
    "fallback": {
        "enabled": True,
        "retry_attempts": 3,
        "retry_delay": 5,
        "error_message": "Llama Stack server unavailable - please install required dependencies (pip install pyyaml) and ensure server is running"
    },
    "system_message": "You are a poetic assistant, skilled in explaining complex programming concepts with creative flair.",
    "inference_params": {
        "sampling_params": {
            "strategy": "greedy",
            "temperature": 0.0,
            "top_p": 0.95,
            "top_k": 0,
            "max_tokens": 512,
            "repetition_penalty": 1.0
        },
        "stream": True,
        "tools": [],
        "tool_choice": "auto",
        "tool_prompt_format": "json"
    }
}

# Agent Configuration
AGENT_CONFIG = {
    "curator": {
        "name": "Curator",
        "color": Fore.MAGENTA,
        "personality": "A detail-oriented observer who detects content type and topic shifts",
        "prompt_template": """Analyze content for type and topic changes. Pay special attention to:
            - Programming code vs natural language
            - Technical documentation vs conversational text
            - Structured data vs prose
            - Major subject matter shifts
            
            Rules:
            - Each key and value should be 1-3 words maximum
            - ALWAYS start with 'content_type' and 'context_shift'
            - If content type changes (e.g. code vs text), ALWAYS mark context_shift as true
            - Format as 'key: value'
            
            Previous context: {prev_thoughts}
            
            List the key-value pairs for this content:"""
    },
    "analyst": {
        "name": "Analyst",
        "color": Fore.YELLOW,
        "personality": "A technical analyzer who identifies structural patterns",
        "prompt_template": """Analyze content structure and complexity while tracking shifts.
            
            Rules:
            - Each key and value should be 1-3 words maximum
            - ALWAYS start with 'structure_type' and 'complexity_level'
            - Note dramatic shifts in content structure
            - Format as 'key: value'
            
            Previous flow: {prev_thoughts}
            
            List the key-value pairs for this analysis:"""
    },
    "synthesizer": {
        "name": "Synthesizer",
        "color": Fore.GREEN,
        "personality": "An integrator who identifies significant transitions",
        "prompt_template": """Synthesize shifts in content type and structure.
            
            Rules:
            - Each key and value should be 1-3 words maximum
            - ALWAYS evaluate significance of change
            - Format as 'key: value'
            - Add change metrics
            
            Previous synthesis: {prev_thoughts}
            
            List the key-value pairs for your synthesis:"""
    }
}

# Ensure directories exist
os.makedirs(ASSETS_DIR, exist_ok=True)
os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
os.makedirs(os.path.dirname(DATASET_FILE), exist_ok=True)
os.makedirs(SCREENSHOTS_DIR, exist_ok=True)

# Initialize Llama Stack client
client = LlamaStackClient(base_url="http://localhost:5001")

# Initialize processing queues and locks
content_queue = Queue(maxsize=PERFORMANCE_CONFIG["max_queue_size"])
result_queue = Queue()
clipboard_lock = Lock()
last_content_hash = None

def query_llama_stack(prompt: str) -> dict:
    """Query Llama Stack with enhanced error handling and fallback"""
    for attempt in range(AI_CONFIG["fallback"]["retry_attempts"]):
        try:
            response = client.inference.chat_completion(
                model_id=AI_CONFIG["model_id"],
                messages=[
                    {
                        "role": "system",
                        "content": AI_CONFIG["system_message"]
                    },
                    {
                        "role": "user",
                        "content": prompt + "\n\nIMPORTANT: Keep responses concise. No repetition."
                    }
                ],
                **AI_CONFIG["inference_params"]
            )
            
            full_response = ""
            seen_facts = set()  # Track unique facts to prevent loops
            
            try:
                for chunk in response:
                    # Handle both streaming and non-streaming responses
                    if hasattr(chunk, 'event') and hasattr(chunk.event, 'delta'):
                        new_text = chunk.event.delta
                    elif hasattr(chunk, 'choices') and chunk.choices:
                        new_text = chunk.choices[0].message.content
                    else:
                        continue
                        
                    # Prevent repetitive content
                    if new_text not in seen_facts:
                        seen_facts.add(new_text)
                        full_response += new_text
                    
                    # Break if response gets too long
                    if len(full_response) > 1000:  # Reasonable limit
                        break
                        
            except Exception as stream_error:
                print(f"{Fore.YELLOW}[Stream Warning] {str(stream_error)}{Style.RESET_ALL}")
                
            return {
                'response': full_response.strip(),
                'metadata': {
                    'provider': AI_CONFIG["provider"],
                    'model': AI_CONFIG["model_id"],
                    'timestamp': datetime.now().isoformat()
                }
            }
            
        except Exception as e:
            print(f"{Fore.YELLOW}[Attempt {attempt + 1}] Llama Stack Error: {str(e)}{Style.RESET_ALL}")
            if attempt < AI_CONFIG["fallback"]["retry_attempts"] - 1:
                time.sleep(AI_CONFIG["fallback"]["retry_delay"])
            else:
                print(f"{Fore.RED}{AI_CONFIG['fallback']['error_message']}{Style.RESET_ALL}")
                return {
                    'response': "Error: Llama Stack server unavailable",
                    'metadata': {'error': str(e)}
                }

def analyze_content_type(content: dict) -> str:
    """Detect content type and characteristics"""
    if content["type"] != "text":
        return content["type"]
        
    text = content["content"]
    
    # Check for code indicators
    code_indicators = {
        'import ': 5,
        'def ': 3,
        'class ': 3,
        'return ': 3,
        '    ': 2,  # Indentation
        ');': 2,
        '};': 2
    }
    
    code_score = sum(text.count(indicator) * weight 
                    for indicator, weight in code_indicators.items())
    
    # Check for structured data indicators
    structured_indicators = {
        '{': 1,
        '}': 1,
        '[': 1,
        ']': 1,
        '"key"': 2,
        '"value"': 2
    }
    
    structured_score = sum(text.count(indicator) * weight 
                         for indicator, weight in structured_indicators.items())
    
    if code_score > 10:
        return "code"
    elif structured_score > 10:
        return "structured_data"
    else:
        return "natural_text"

def get_content_hash(content):
    """Generate hash for content to avoid duplicates"""
    return hashlib.md5(str(content).encode()).hexdigest()

def process_clipboard_content():
    """Process clipboard content with duplicate detection"""
    global last_content_hash
    
    with clipboard_lock:
        text_content = pyperclip.paste()
        latest_screenshot = get_latest_screenshot()
        
        current_hash = get_content_hash(text_content if text_content else latest_screenshot)
        
        if (current_hash == last_content_hash or 
            (text_content and len(text_content) < PERFORMANCE_CONFIG["min_content_length"])):
            return None
            
        last_content_hash = current_hash
        
        if text_content:
            return {"type": "text", "content": text_content, "hash": current_hash}
        elif latest_screenshot:
            file_path = save_image(latest_screenshot)
            return {"type": "image", "content": file_path, "hash": current_hash}
    return None

def get_latest_screenshot():
    """Get the most recent screenshot from the screenshots directory"""
    screenshots = sorted(Path(SCREENSHOTS_DIR).glob("*.png"), key=os.path.getmtime, reverse=True)
    return screenshots[0] if screenshots else None

def save_image(image_path):
    """Save image with hash-based filename"""
    image_hash = get_image_hash(image_path)
    new_path = os.path.join(ASSETS_DIR, f"{image_hash}.png")
    shutil.copy(image_path, new_path)
    return new_path

def get_image_hash(image_path):
    """Generate hash for image file"""
    with open(image_path, "rb") as f:
        return hashlib.md5(f.read()).hexdigest()

def encode_image(image_path):
    """Encode image as base64"""
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")

def analyze_content(content: dict) -> dict:
    """Analyze content using all agents"""
    try:
        content_type = analyze_content_type(content)
        agents_thoughts = []
        final_response = {}
        
        for agent_id, agent in AGENT_CONFIG.items():
            truncated_content = truncate_content(content['content'])
            prev_thoughts = format_previous_thoughts(agents_thoughts)
            
            prompt = f"Content type detected: {content_type}\n\n"
            prompt += agent['prompt_template'].format(
                prev_thoughts=prev_thoughts
            ) + f"\n\nContent to analyze:\n{truncated_content}"

            response = query_llama_stack(prompt)
            response_text = response.get('response', '').strip()
            
            if not response_text or response_text.startswith('Error:'):
                print(f"{Fore.RED}[Agent Error] Failed to get response from {agent_id}{Style.RESET_ALL}")
                continue
                
            print(f"\n{agent['color']}{agent['name']}: {response_text}{Style.RESET_ALL}")
            agents_thoughts.append(response_text)
            
            final_response[agent_id] = {
                "response": response_text,
                "context": {
                    "content_type": content_type,
                    "previous_thoughts": prev_thoughts,
                    "role": agent['personality']
                }
            }

        return final_response

    except Exception as e:
        print(f"{Fore.RED}Error in content analysis: {str(e)}{Style.RESET_ALL}")
        return None

def save_to_dataset(content, ai_response):
    """Enhanced dataset storage with Llama Stack metadata"""
    data = {
        "timestamp": datetime.now().isoformat(),
        "content": content,
        "ai_response": ai_response,
        "llama_stack_metadata": {
            "provider": AI_CONFIG["provider"],
            "model": AI_CONFIG["model_id"],
            "environment": AI_CONFIG["environment"],
            "system_message": AI_CONFIG["system_message"],
            "inference_params": AI_CONFIG["inference_params"]
        },
        "analysis_metadata": {
            "agent_count": len(AGENT_CONFIG),
            "content_type": content["type"],
            "content_length": len(str(content["content"]))
        }
    }
    with open(DATASET_FILE, "a") as f:
        json.dump(data, f)
        f.write("\n")

def truncate_content(text: str, max_chars: int = 512) -> str:
    """Truncate content to reasonable length"""
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "... [truncated]"

def format_previous_thoughts(thoughts: List[str]) -> str:
    """Format previous thoughts as key-value pairs"""
    if not thoughts:
        return "no_previous: true"
    
    formatted = []
    for i, thought in enumerate(thoughts):
        agent_name = list(AGENT_CONFIG.keys())[i]
        kv_pairs = [line.strip() for line in thought.split('\n') if ':' in line]
        formatted.append(f"{agent_name}:\n" + "\n".join(kv_pairs))
    
    return "\n".join(formatted)

def content_collector():
    """Continuously collect clipboard content"""
    while True:
        try:
            content = process_clipboard_content()
            if content and not content_queue.full():
                content_queue.put(content)
        except Exception as e:
            print(f"{Fore.RED}Error collecting content: {str(e)}{Style.RESET_ALL}")
        time.sleep(PERFORMANCE_CONFIG["poll_interval"])

def content_processor():
    """Process content from queue"""
    while True:
        try:
            # Use timeout to prevent blocking indefinitely
            content = content_queue.get(timeout=PERFORMANCE_CONFIG["poll_interval"])
            if content:
                analysis = analyze_content(content)
                if analysis:
                    save_to_dataset(content, analysis)
                    result_queue.put((content, analysis))
        except QueueEmpty:
            # Queue is empty, continue polling
            continue
        except Exception as e:
            print(f"{Fore.RED}Error processing content: {str(e)}{Style.RESET_ALL}")
            time.sleep(0.1)  # Brief pause on error

def main():
    """Main function to run the clipboard monitor"""
    print(f"{Fore.CYAN}Starting Llama Stack clipboard monitor...{Style.RESET_ALL}")
    print(f"Batch size: {PERFORMANCE_CONFIG['batch_size']}")
    print(f"Poll interval: {PERFORMANCE_CONFIG['poll_interval']}s")
    
    # Start collector and processor threads
    collector_thread = Thread(target=content_collector, daemon=True)
    processor_threads = [
        Thread(target=content_processor, daemon=True)
        for _ in range(PERFORMANCE_CONFIG["concurrent_agents"])
    ]
    
    try:
        collector_thread.start()
        for thread in processor_threads:
            thread.start()
        
        # Monitor and display results with timeout
        while True:
            try:
                content, analysis = result_queue.get(timeout=1)
                print(f"\n{Fore.GREEN}Processed content of type: {content['type']}{Style.RESET_ALL}")
                print(f"Queue size: {content_queue.qsize()}")
            except QueueEmpty:
                # No results yet, continue monitoring
                continue
            except KeyboardInterrupt:
                raise
            except Exception as e:
                print(f"{Fore.RED}Error in main loop: {str(e)}{Style.RESET_ALL}")
                time.sleep(0.1)
                
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}Shutting down...{Style.RESET_ALL}")
        # Optional: Add cleanup code here
        
    finally:
        # Ensure proper shutdown
        print(f"{Fore.YELLOW}Cleanup complete.{Style.RESET_ALL}")

if __name__ == "__main__":
    main()

"""
docker run -it -p 5001:5001 --gpus all -v ~/.llama:/root/.llama llamastack/distribution-meta-reference-gpu --port 5001 --env INFERENCE_MODEL=meta-llama/Llama-3.2-1B-Instruct
"""