# Local LLM Compatibility Reference

**Last tested**: 2026-06-06
**Hardware**: RTX 4090 (24 GB VRAM), Intel i9-14900K, 128 GB RAM, Ubuntu, CUDA 12.8

## Installed Versions

| Component | Version | Install Method | Path |
|---|---|---|---|
| Ollama | v0.30.6 | system package | systemd service |
| llama.cpp (llama-server) | b9542 | built from source | `/usr/local/bin/llama-server` |
| vLLM | 0.19.1 | `uv tool install vllm` | `~/.local/share/uv/tools/vllm/` |
| SGLang | (latest as of 2026-06-06) | `uv tool install sglang` | `~/.local/share/uv/tools/sglang/` |
| transformers (in vLLM env) | 5.5.4 | bundled | |
| transformers (in SGLang env) | 4.57.1 | bundled | |
| CUDA | 12.8 | system | |
| Python | 3.12 | system | |

## Working Configurations (Vision Verified)

| Model | Framework | Result | Speed |
|---|---|---|---|
| gemma4-12b | llama-cpp | ✅ PASS | 76 tok/s, 7s total |
| gemma4-12b | ollama | ✅ PASS | 18s total |
| gemma4-26b | ollama | ✅ PASS | 12s total |
| qwen3-vl-32b | ollama | ✅ PASS | 298s total |

## Failing Configurations

### gemma4-12b + vLLM — `gemma4_unified` architecture not recognized
- The Gemma 4 12B is a "unified" multimodal model (`Gemma4UnifiedForConditionalGeneration`)
- vLLM's bundled transformers 5.5.4 doesn't know this architecture
- Error: `The checkpoint you are trying to load has model type gemma4_unified but Transformers does not recognize this architecture`
- **To fix**: Upgrade transformers inside vLLM's virtualenv: `~/.local/share/uv/tools/vllm/bin/pip install --upgrade transformers` — but this may break vLLM

### gemma4-12b + SGLang — same `gemma4_unified` issue
- SGLang's transformers 4.57.1 is even older
- Same error as vLLM

### gemma4-26b + llama-cpp — wrong number of tensors
- Error: `wrong number of tensors; expected 1014, got 658`
- Ollama's GGUF for the 26B-A4B MoE model only contains the active expert parameters, not the full tensor set. llama-server expects all tensors.
- Also: no mmproj (vision projector) blob in the Ollama manifest, so even if it loaded, vision wouldn't work
- **To fix**: Would need a standalone GGUF from HuggingFace (not Ollama's blob) plus a separate mmproj file. As of 2026-06-06, these don't exist for Gemma 4 26B.

### gemma4-26b + vLLM — Triton compilation crash
- The model loads successfully (16.47 GiB, 10s) but Triton crashes during CUDA graph profiling
- Root cause: Gemma 4 has heterogeneous attention head dimensions (head_dim=256 vs global_head_dim=512) that Triton can't handle
- `--enforce-eager` also fails at KV cache initialization
- The AWQ repo is `cyankiwi/gemma-4-26B-A4B-it-AWQ-4bit`, architecture `Gemma4ForConditionalGeneration`
- **To fix**: Needs vLLM upstream fix for Gemma 4 attention

### gemma4-26b + SGLang — `gemma4` architecture not recognized
- SGLang's transformers 4.57.1 doesn't know `gemma4` (not just `gemma4_unified`)
- **To fix**: Upgrade transformers in SGLang env

### qwen3-vl-32b + llama-cpp — model hyperparameters error
- Error: `key not found in model: qwen3vl.rope.dimension_sections`
- llama-server's GGUF loader doesn't support Qwen3-VL's architecture yet
- Also: no mmproj blob
- **To fix**: Wait for llama.cpp upstream to add Qwen3-VL support

### qwen3-vl-32b + vLLM — OOM
- Model loads (20.83 GiB) but KV cache initialization fails
- Even with `--max-model-len 2048 --gpu-memory-utilization 0.95 --enforce-eager`, free memory (21.82 GiB after Xorg desktop) is less than what vLLM requests (22.33 GiB)
- The 32B AWQ model simply doesn't fit on a 24GB GPU with vLLM's overhead
- **To fix**: Would need tensor parallelism (multi-GPU), a smaller quant, or a smaller model

### qwen3-vl-32b + SGLang — CuDNN version check blocks startup
- SGLang requires CuDNN ≥ 9.15 with PyTorch 2.9.1
- Error message suggests: `pip install nvidia-cudnn-cu12==9.16.0.29` or set `SGLANG_DISABLE_CUDNN_CHECK=1`
- Even if fixed, would likely OOM (same as vLLM)

## Key Technical Notes

### Ollama Model Blobs
- Ollama v0.30+ with systemd stores in `/usr/share/ollama/.ollama/models/`
- Manifests: `.../manifests/registry.ollama.ai/library/<model>/<tag>`
- Blobs: `.../blobs/sha256-<hash>`
- Vision: look for `application/vnd.ollama.image.projector` layer in manifest (only gemma4:12b has one)
- llama-server reads GGUF blobs directly — but not all Ollama GGUFs are compatible (MoE models store partial tensors)

### Ollama Thinking Quirk
- Gemma 4 models return chain-of-thought in a `thinking` field in the response JSON
- `message.content` contains the final answer, `message.thinking` has reasoning
- With low `num_predict`, all tokens may be consumed by thinking, leaving `content` empty
- Always extract from both fields when parsing responses

### VRAM Contention
- Ollama keeps models loaded in VRAM until its idle timeout (default 5 min)
- Before starting llama-cpp, vLLM, or SGLang, unload Ollama models:
  ```bash
  curl -s http://localhost:11434/api/generate -d '{"model":"gemma4:12b","keep_alive":0}'
  ```
- Or check `nvidia-smi` and wait for Ollama to release VRAM

### Model Architecture Types
| Model | HF model_type | HF architectures | Status |
|---|---|---|---|
| gemma4-12b | `gemma4_unified` | `Gemma4UnifiedForConditionalGeneration` | Too new for vLLM/SGLang transformers |
| gemma4-26b | `gemma4` | `Gemma4ForConditionalGeneration` | Too new for SGLang; Triton bug in vLLM |
| qwen3-vl-32b | `qwen3_vl` | `Qwen3VLForConditionalGeneration` | OOM on 24GB for vLLM/SGLang |

## Models Worth Trying in the Future

Smaller or newer models that might work across more frameworks:

| Model | Size | Modalities | Why Try It |
|---|---|---|---|
| Qwen2.5-VL-7B | 7B | Text, Image | Small enough for any framework on 24GB; well-supported in vLLM/SGLang |
| Phi-4-multimodal-14B | 14B | Text, Image, Audio | Microsoft model; potentially good vLLM/SGLang support |
| InternVL3-8B | 8B | Text, Image | Strong vision; well-supported architecture |
| Gemma 4 4B | 4B | Text, Image | Smallest Gemma 4; might work in all frameworks |
| Llama 4 Scout (17B-A4B) | 17B MoE | Text, Image | Meta model; likely good framework support |

## Frameworks Worth Trying in the Future

| Framework | Why |
|---|---|
| **Ollama** (current) | Works for everything; simple |
| **llama.cpp** (current) | Fast; good for single-stream; limited model support |
| **vLLM** (parked) | Best continuous batching; blocked by Gemma 4 bugs; revisit after vLLM 0.20+ |
| **SGLang** (parked) | RadixAttention for shared-prefix batching; blocked by old transformers + CuDNN; revisit when updated |
| **ExLlamaV2** | Fast GPTQ/EXL2 inference; good for interactive use; not tested yet |
| **TensorRT-LLM** | NVIDIA's optimized runtime; complex setup but potentially fastest; not tested |
| **MLC-LLM** | Apache TVM-based; potentially good cross-platform; not tested |

---

*Update this file whenever a new model, framework version, or hardware change is tested.*
