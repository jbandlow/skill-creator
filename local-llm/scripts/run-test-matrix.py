#!/usr/bin/env python3
"""run-test-matrix.py — Test the 4 working model×framework combinations with vision.

Tested configurations:
  1. gemma4-12b  + llama-cpp
  2. gemma4-12b  + ollama
  3. gemma4-26b  + ollama
  4. qwen3-vl-32b + ollama

Usage: python3 run-test-matrix.py <image_path> [results_file]
"""

import base64
import json
import os
import subprocess
import sys
import time
import urllib.request
import urllib.error

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
WORK_DIR = "/tmp/llm-serve"

TESTS = [
    {"model": "gemma4-12b",   "framework": "llama-cpp", "port": 8080},
    {"model": "gemma4-12b",   "framework": "ollama",    "port": 11434},
    {"model": "gemma4-26b",   "framework": "ollama",    "port": 11434},
    {"model": "qwen3-vl-32b", "framework": "ollama",    "port": 11434},
]

OLLAMA_TAGS = {
    "gemma4-12b": "gemma4:12b",
    "gemma4-26b": "gemma4:26b",
    "qwen3-vl-32b": "qwen3-vl:32b",
}


def log(msg: str) -> None:
    print(msg, flush=True)


def encode_image(path: str) -> str:
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()


def wait_for_server(port: int, max_wait: int = 120) -> bool:
    endpoints = [f"http://localhost:{port}/health", f"http://localhost:{port}/v1/models"]
    if port == 11434:
        endpoints.append(f"http://localhost:{port}/api/tags")
    waited = 0
    while waited < max_wait:
        for url in endpoints:
            try:
                with urllib.request.urlopen(urllib.request.Request(url), timeout=3) as resp:
                    if resp.status == 200:
                        return True
            except Exception:
                pass
        time.sleep(3)
        waited += 3
    return False


def unload_ollama() -> None:
    for tag in OLLAMA_TAGS.values():
        try:
            payload = json.dumps({"model": tag, "keep_alive": 0}).encode()
            req = urllib.request.Request(
                "http://localhost:11434/api/generate",
                data=payload,
                headers={"Content-Type": "application/json"},
            )
            urllib.request.urlopen(req, timeout=10)
        except Exception:
            pass
    time.sleep(3)


def detect_model_name(port: int) -> str:
    try:
        with urllib.request.urlopen(
            urllib.request.Request(f"http://localhost:{port}/v1/models"), timeout=5
        ) as resp:
            return json.loads(resp.read())["data"][0]["id"]
    except Exception:
        return "default"


def send_vision_openai(port: int, model_name: str, image_b64: str) -> dict:
    payload = {
        "model": model_name,
        "messages": [{
            "role": "user",
            "content": [
                {"type": "text", "text": "Describe this image in detail. What do you see?"},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"}},
            ],
        }],
        "max_tokens": 512,
        "temperature": 0,
    }
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        f"http://localhost:{port}/v1/chat/completions",
        data=data,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=600) as resp:
        return json.loads(resp.read())


def send_vision_ollama(model_name: str, image_b64: str) -> dict:
    payload = {
        "model": model_name,
        "messages": [{
            "role": "user",
            "content": "Describe this image in detail. What do you see?",
            "images": [image_b64],
        }],
        "stream": False,
        "options": {"num_predict": 1024, "temperature": 0},
    }
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        "http://localhost:11434/api/chat",
        data=data,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=600) as resp:
        return json.loads(resp.read())


def extract_text(response: dict, is_ollama: bool = False) -> str:
    """Extract response text, handling content, reasoning_content, and thinking fields."""
    if is_ollama:
        msg = response.get("message", {})
        content = msg.get("content", "")
        thinking = msg.get("thinking", "")
        return content if len(content) > len(thinking) else (content or thinking)

    msg = response.get("choices", [{}])[0].get("message", {})
    content = msg.get("content", "")
    reasoning = msg.get("reasoning_content", "")
    return content if len(content) > len(reasoning) else (content or reasoning)


def run_test(test: dict, image_b64: str) -> dict:
    model = test["model"]
    framework = test["framework"]
    port = test["port"]
    is_ollama = framework == "ollama"

    result = {"model": model, "framework": framework, "status": "FAIL", "time_s": 0, "response": "", "error": ""}

    log(f"\n{'='*50}")
    log(f"Testing: {model} + {framework}")
    log(f"{'='*50}")

    if framework == "llama-cpp":
        unload_ollama()
        log("Starting llama-server...")
        subprocess.run(
            [os.path.join(SCRIPT_DIR, "llm-serve.sh"), model, framework, "--context", "4096"],
            capture_output=True, text=True, timeout=30,
        )
        log(f"Waiting for server on port {port}...")
        if not wait_for_server(port, max_wait=120):
            result["error"] = "Server did not start in 120s"
            log(f"  FAIL: {result['error']}")
            subprocess.run(["pkill", "-f", "llama-server"], capture_output=True)
            return result
    else:
        log(f"Using Ollama with {OLLAMA_TAGS[model]}...")
        if not wait_for_server(port, max_wait=10):
            result["error"] = "Ollama service not running"
            log(f"  FAIL: {result['error']}")
            return result

    log("Server ready! Sending vision query...")
    start_time = time.time()
    try:
        if is_ollama:
            raw = send_vision_ollama(OLLAMA_TAGS[model], image_b64)
        else:
            model_name = detect_model_name(port)
            raw = send_vision_openai(port, model_name, image_b64)
        response_text = extract_text(raw, is_ollama=is_ollama)
    except Exception as e:
        result["error"] = str(e)
        result["time_s"] = int(time.time() - start_time)
        log(f"  FAIL: {e}")
        if framework == "llama-cpp":
            subprocess.run(["pkill", "-f", "llama-server"], capture_output=True)
        return result

    elapsed = int(time.time() - start_time)
    result["time_s"] = elapsed
    result["response"] = response_text
    if len(response_text) > 10:
        result["status"] = "PASS"

    log(f"Result: {result['status']} ({elapsed}s, {len(response_text)} chars)")
    log(f"Response: {response_text[:300]}...")

    if framework == "llama-cpp":
        subprocess.run(["pkill", "-f", "llama-server"], capture_output=True)
        time.sleep(5)
    else:
        unload_ollama()

    return result


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 run-test-matrix.py <image_path> [results_file]")
        sys.exit(1)

    image_path = sys.argv[1]
    results_file = sys.argv[2] if len(sys.argv) > 2 else "/tmp/llm-serve/test-results.txt"

    log(f"Encoding image: {image_path}")
    image_b64 = encode_image(image_path)
    log(f"Image encoded ({len(image_b64)} bytes base64)")

    os.makedirs(WORK_DIR, exist_ok=True)
    results: list[dict] = []

    log(f"\nTesting {len(TESTS)} verified configurations...\n")

    for test in TESTS:
        r = run_test(test, image_b64)
        results.append(r)

    log(f"\n{'='*60}")
    log("TEST MATRIX COMPLETE")
    log(f"{'='*60}\n")

    header = f"{'MODEL':<16} {'FRAMEWORK':<12} {'RESULT':<8} {'TIME':<8} EXCERPT"
    separator = f"{'-----':<16} {'--------':<12} {'------':<8} {'----':<8} -------"
    lines = [
        f"# Test Matrix Results — {time.strftime('%Y-%m-%d %H:%M:%S')}",
        f"# Image: {image_path}",
        "",
        header,
        separator,
    ]
    for r in results:
        excerpt = r["response"][:100].replace("\n", " ") if r["response"] else r["error"][:100]
        lines.append(f"{r['model']:<16} {r['framework']:<12} {r['status']:<8} {r['time_s']:<8} {excerpt}")

    table = "\n".join(lines)
    log(table)

    with open(results_file, "w") as f:
        f.write(table + "\n")

    passed = sum(1 for r in results if r["status"] == "PASS")
    log(f"\nPassed: {passed}/{len(results)}")


if __name__ == "__main__":
    main()
