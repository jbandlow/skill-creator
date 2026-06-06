---
name: local-llm
description: Serve and query local LLM models using llama.cpp or Ollama. Use when starting a local model server, sending inference requests, or choosing a model/framework for a task.
---

# Instruction: Local LLM Serving

This skill serves multimodal LLMs on this machine (RTX 4090, 128 GB RAM, CUDA 12.8). Only tested, working combinations are documented here.

## Models

| Short Name | Full Name | Params | Active | VRAM (Q4) | Modalities | Notes |
|---|---|---|---|---|---|---|
| `gemma4-12b` | Gemma 4 12B Instruct (unified) | 12B dense | 12B | ~8 GB | Text, Image, Audio | Only model with mmproj for llama-cpp vision |
| `gemma4-26b` | Gemma 4 26B-A4B Instruct (MoE) | 26B total | 4B | ~18 GB | Text, Image | Fastest inference due to MoE; Ollama only |
| `qwen3-vl-32b` | Qwen3-VL-32B Instruct | 32B dense | 32B | ~20 GB | Text, Image, Video | Best vision quality; Ollama only; slow cold-start |

All models are stored as GGUF in Ollama's blob storage at `/usr/share/ollama/.ollama/models/` (systemd) or `~/.ollama/models/` (user mode). No duplication — llama-server reads blobs directly.

## Frameworks

| Framework | Port | API | Best For |
|---|---|---|---|
| **llama-cpp** | 8080 | OpenAI-compatible (`/v1/chat/completions`) | Direct control; vision for gemma4-12b |
| **Ollama** | 11434 | OpenAI-compatible + native (`/api/chat`) | All models; simplest; auto-loads/unloads |

## Working Combinations

Vision tested and verified 2026-06-06.

| Model | Framework | Vision | Speed | Notes |
|---|---|---|---|---|
| gemma4-12b | llama-cpp | ✅ | 76 tok/s, 7s | Via mmproj projector blob |
| gemma4-12b | ollama | ✅ | ~18s | |
| gemma4-26b | ollama | ✅ | ~12s | Fastest overall |
| qwen3-vl-32b | ollama | ✅ | ~298s | Slow cold-start (20GB load) |

## Quick Start

### Start a server

**llama-cpp:**
```bash
~/.gemini/antigravity/skills/local-llm/scripts/llm-serve.sh gemma4-12b llama-cpp
```

**Ollama:** Runs as a systemd service. Models auto-load on first request.
```bash
# Verify Ollama is running
sudo systemctl status ollama
# Pre-load a model (optional)
ollama run gemma4:12b '/no_think hi'
```

### Send a vision query

**OpenAI-compatible API** (works for both llama-cpp and Ollama):
```bash
IMAGE_B64=$(base64 -w 0 /path/to/image.jpg)
curl http://localhost:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "default",
    "messages": [{
      "role": "user",
      "content": [
        {"type": "text", "text": "Describe this image."},
        {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64,'$IMAGE_B64'"}}
      ]
    }],
    "max_tokens": 512
  }'
```

**Ollama native API:**
```bash
IMAGE_B64=$(base64 -w 0 /path/to/image.jpg)
curl http://localhost:11434/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gemma4:12b",
    "messages": [{"role": "user", "content": "Describe this image.", "images": ["'$IMAGE_B64'"]}],
    "stream": false
  }'
```

### Ollama Thinking Quirk

Gemma 4 models use thinking mode by default. The API response has:
- `message.content`: the final answer
- `message.thinking`: the chain-of-thought reasoning

With limited `num_predict`, all tokens may be consumed by thinking, leaving `content` empty. When parsing responses, always check both fields. Use `num_predict: 1024` or higher for vision tasks.

### Stop a server

```bash
~/.gemini/antigravity/skills/local-llm/scripts/llm-stop.sh llama-cpp
# Ollama: sudo systemctl stop ollama
```

### Test all combinations

```bash
python3 ~/.gemini/antigravity/skills/local-llm/scripts/run-test-matrix.py /path/to/image.jpg
```

Runs the 4 working combinations and reports PASS/FAIL.

## Choosing a Combination

| Task | Recommended | Why |
|---|---|---|
| Quick experiment / chat | `gemma4-12b` + `ollama` | Simplest; auto-loads |
| Image description / tagging | `gemma4-26b` + `ollama` | Fastest; good quality |
| Best vision quality | `qwen3-vl-32b` + `ollama` | Superior OCR/scene analysis; slow |
| Direct API control | `gemma4-12b` + `llama-cpp` | OpenAI API; vision via mmproj |

## Troubleshooting

### Port already in use
```bash
ss -tlnp | grep :8080
llm-stop.sh llama-cpp
```

### CUDA out of memory
- Reduce context size: `--context 4096` or `--context 2048`
- Use a smaller model (`gemma4-12b`)
- Check for other GPU processes: `nvidia-smi`

### Ollama not responding
```bash
sudo systemctl status ollama
sudo systemctl restart ollama
```

## Adding New Models

1. Pull via Ollama: `ollama pull <model:tag>`
2. Add entry to `OLLAMA_TAGS` in `scripts/llm-serve.sh`
3. For llama-cpp vision: check if the Ollama manifest has a `projector` layer

## Compatibility Reference

For details on frameworks and model combinations that were tested but don't work (vLLM, SGLang, llama-cpp with gemma4-26b/qwen3-vl), potential future models to try, and hardware-specific notes, see [COMPATIBILITY.md](./COMPATIBILITY.md).
