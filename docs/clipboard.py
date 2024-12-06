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
from queue import Queue
import asyncio
import signal
from experimental.novelty_tracker import NoveltyTracker, PERFORMANCE_CONFIG as NOVELTY_CONFIG

# Configuration
ASSETS_DIR = os.path.expanduser("~/Desktop/llama-pile/assets")
LOG_FILE = os.path.expanduser("~/Desktop/llama-pile/clipboard_log.txt")
DATASET_FILE = os.path.expanduser("~/Desktop/llama-pile/clipboard_dataset.jsonl")
SCREENSHOTS_DIR = os.path.expanduser("~/Screenshots")

# Add Performance Configuration
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

# AI Configuration
AI_CONFIG = {
    "provider": "meta-reference",
    "model_id": "meta-llama/Llama-3.2-1B-Instruct",
    "environment": "single-node",
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

# Add new configuration
AGENT_CONFIG = {
    "curator": {
        "name": "Curator",
        "color": Fore.MAGENTA,
        "personality": "A context-aware cataloger who detects topic shifts and adapts accordingly.",
        "prompt_template": """Extract key technical elements as concise key-value pairs, with special attention to topic shifts.
            
            Rules:
            - Each key and value should be 1-3 words maximum
            - If content seems unrelated to previous context, start fresh
            - Format as 'key: value'
            - Add 'context_shift: true/false' as first pair if topic changes
            
            Example format:
            context_shift: true
            topic: new subject
            relevance: high
            
            Previous context: {prev_thoughts}
            
            List the key-value pairs for this content:"""
    },
    "analyst": {
        "name": "Analyst",
        "color": Fore.YELLOW,
        "personality": "A pattern detector who tracks conversation flow and topic coherence.",
        "prompt_template": """Map patterns while tracking conversation coherence.
            
            Rules:
            - Each key and value should be 1-3 words maximum
            - Note any context breaks
            - Format as 'key: value'
            - Add 'flow_break: true/false' as first pair if conversation shifts
            
            Example format:
            flow_break: true
            new_direction: mythology
            confidence: high
            
            Previous flow: {prev_thoughts}
            
            List the key-value pairs for this analysis:"""
    },
    "synthesizer": {
        "name": "Synthesizer",
        "color": Fore.GREEN,
        "personality": "An integrator who rewards fresh starts and context awareness.",
        "prompt_template": """Synthesize analysis with focus on conversation flow.
            
            Rules:
            - Each key and value should be 1-3 words maximum
            - Reward topic shifts with 'adaptation_score: high'
            - Format as 'key: value'
            - Add 'reset_success: true/false' as first pair
            
            Example format:
            reset_success: true
            adaptation_score: high
            topic_clarity: excellent
            
            Previous synthesis: {prev_thoughts}
            
            List the key-value pairs for your synthesis:"""
    }
}

# Ensure directories exist
os.makedirs(ASSETS_DIR, exist_ok=True)
os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
os.makedirs(os.path.dirname(DATASET_FILE), exist_ok=True)
os.makedirs(SCREENSHOTS_DIR, exist_ok=True)

# Initialize AI client
client = LlamaStackClient(base_url="http://localhost:5001")

# Initialize novelty tracker
novelty_tracker = NoveltyTracker(PERFORMANCE_CONFIG["history_size"])

def query_ollama(prompt):
    """Enhanced Llama Stack integration with better stream handling and loop prevention"""
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
        print(f"{Fore.RED}[Llama Stack Error] {str(e)}{Style.RESET_ALL}")
        return {
            'response': "Error: Failed to generate response",
            'metadata': {'error': str(e)}
        }

# Initialize colorama
colorama.init(autoreset=True)

def log_event(event_type, content):
    timestamp = datetime.now().isoformat()
    with open(LOG_FILE, "a") as f:
        f.write(f"{timestamp} - {event_type}: {content}\n")

def get_image_hash(image_path):
    with open(image_path, "rb") as f:
        return hashlib.md5(f.read()).hexdigest()

def save_image(image_path):
    image_hash = get_image_hash(image_path)
    new_path = os.path.join(ASSETS_DIR, f"{image_hash}.png")
    shutil.copy(image_path, new_path)
    return new_path

def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")

def get_latest_screenshot():
    screenshots = sorted(Path(SCREENSHOTS_DIR).glob("*.png"), key=os.path.getmtime, reverse=True)
    return screenshots[0] if screenshots else None

# Add processing queues and locks
content_queue = Queue(maxsize=PERFORMANCE_CONFIG["max_queue_size"])
result_queue = Queue()
clipboard_lock = Lock()
last_content_hash = None

def get_content_hash(content):
    """Generate hash for content to avoid duplicates"""
    return hashlib.md5(str(content).encode()).hexdigest()

def process_clipboard_content():
    """Modified to handle batch processing"""
    global last_content_hash
    
    with clipboard_lock:
        text_content = pyperclip.paste()
        latest_screenshot = get_latest_screenshot()
        
        # Generate content hash
        current_hash = get_content_hash(text_content if text_content else latest_screenshot)
        
        # Skip if content hasn't changed or is too short
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

def process_content_batch(batch):
    """Process multiple content items efficiently"""
    results = []
    for content in batch:
        try:
            response = query_ai(content)
            if response:
                results.append((content, response))
                # Save to dataset
                save_to_dataset(content, response)
        except Exception as e:
            print(f"{Fore.RED}Error processing content: {str(e)}{Style.RESET_ALL}")
    return results

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
    """Process content from queue in batches"""
    batch = []
    while True:
        try:
            # Collect batch
            while len(batch) < PERFORMANCE_CONFIG["batch_size"] and not content_queue.empty():
                content = content_queue.get_nowait()
                if content:
                    batch.append(content)
            
            # Process batch if not empty
            if batch:
                results = process_content_batch(batch)
                for content, response in results:
                    result_queue.put((content, response))
                batch = []
            
            # Small sleep to prevent CPU spinning
            time.sleep(0.1)  # Increased sleep time slightly
        except Exception as e:
            print(f"{Fore.RED}Error processing batch: {str(e)}{Style.RESET_ALL}")
            batch = []  # Clear batch on error

def query_ai(content):
    try:
        agents_thoughts = []
        final_response = {}
        
        for agent_id, agent in AGENT_CONFIG.items():
            if content["type"] == "text":
                truncated_content = truncate_content(content['content'])
                prev_thoughts = format_previous_thoughts(agents_thoughts)
                
                prompt = agent['prompt_template'].format(
                    prev_thoughts=prev_thoughts
                ) + f"\n\nContent to analyze:\n{truncated_content}"
                
            elif content["type"] == "image":
                base64_image = encode_image(content["content"])
                prev_thoughts = format_previous_thoughts(agents_thoughts)
                
                prompt = agent['prompt_template'].format(
                    prev_thoughts=prev_thoughts
                ) + "\n\nAnalyze this screenshot: [image data]"

            # Query Llama Stack and handle response
            response = query_ollama(prompt)
            
            # Extract just the response text, ignore attention scores for now
            response_text = response.get('response', '').strip()
            if not response_text or response_text.startswith('Error:'):
                print(f"{Fore.RED}[Agent Error] Failed to get valid response from {agent_id}{Style.RESET_ALL}")
                continue
                
            print(f"\n{agent['color']}{agent['name']}: {response_text}{Style.RESET_ALL}")
            agents_thoughts.append(response_text)
            
            # Store structured response
            final_response[agent_id] = {
                "response": response_text,
                "context": {
                    "previous_thoughts": prev_thoughts,
                    "role": agent['personality']
                }
            }

        return final_response

    except Exception as e:
        print(f"{Fore.RED}Error querying AI: {str(e)}{Style.RESET_ALL}")
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
    """Truncate content to approximately 512 tokens (roughly 2048 characters)"""
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "... [truncated]"

def format_previous_thoughts(thoughts: List[str]) -> str:
    """Format previous thoughts as a compact list of key-value pairs"""
    if not thoughts:
        return "no_previous: true"
    
    formatted = []
    for i, thought in enumerate(thoughts):
        agent_name = list(AGENT_CONFIG.keys())[i]
        # Extract only the key-value lines from the thought
        kv_pairs = [line.strip() for line in thought.split('\n') if ':' in line]
        formatted.append(f"{agent_name}:\n" + "\n".join(kv_pairs))
    
    return "\n".join(formatted)

def main():
    print(f"{Fore.CYAN}Starting optimized clipboard monitor...{Style.RESET_ALL}")
    print(f"Batch size: {PERFORMANCE_CONFIG['batch_size']}")
    print(f"Poll interval: {PERFORMANCE_CONFIG['poll_interval']}s")
    
    # Start collector and processor threads
    collector_thread = Thread(target=content_collector, daemon=True)
    processor_threads = [
        Thread(target=content_processor, daemon=True)
        for _ in range(PERFORMANCE_CONFIG["concurrent_agents"])
    ]
    
    collector_thread.start()
    for thread in processor_threads:
        thread.start()
    
    # Monitor and display results
    try:
        while True:
            try:
                content, response = result_queue.get(timeout=1)
                print(f"\n{Fore.GREEN}Processed content of type: {content['type']}{Style.RESET_ALL}")
                print(f"Queue size: {content_queue.qsize()}")
                
                # Log only the first few characters of content for performance
                log_event("Content Processed", 
                         f"Type: {content['type']}, Hash: {content['hash'][:8]}")
            except:
                continue
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}Shutting down...{Style.RESET_ALL}")

if __name__ == "__main__":
    main()