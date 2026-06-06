#!/usr/bin/env bash
set -euo pipefail

# llm-serve.sh — Start a local LLM server with a specific model and framework.
#
# Usage:
#   llm-serve.sh <model> <framework> [--context <size>]
#
# Models:     gemma4-12b, gemma4-26b, qwen3-vl-32b
# Frameworks: llama-cpp, ollama
#
# Examples:
#   llm-serve.sh gemma4-12b llama-cpp
#   llm-serve.sh gemma4-12b ollama
#   llm-serve.sh gemma4-26b ollama

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# --- Configuration ---
# Ollama v0.30+ with systemd stores models under /usr/share/ollama/.ollama/models/
# Older versions or user-mode use ~/.ollama/models/
if [[ -d "/usr/share/ollama/.ollama/models/manifests" ]]; then
    OLLAMA_BASE="/usr/share/ollama/.ollama/models"
elif [[ -d "$HOME/.ollama/models/manifests" ]]; then
    OLLAMA_BASE="$HOME/.ollama/models"
else
    echo "Error: Cannot find Ollama models directory" >&2
    echo "Checked: /usr/share/ollama/.ollama/models/ and ~/.ollama/models/" >&2
    exit 1
fi
OLLAMA_MANIFEST_BASE="$OLLAMA_BASE/manifests/registry.ollama.ai/library"

# Model name → Ollama tag mapping
declare -A OLLAMA_TAGS=(
    [gemma4-12b]="gemma4:12b"
    [gemma4-26b]="gemma4:26b"
    [qwen3-vl-32b]="qwen3-vl:32b"
)

# Framework → default port mapping
declare -A FRAMEWORK_PORTS=(
    [llama-cpp]=8080
    [ollama]=11434
)

# PID file location
PID_DIR="/tmp/llm-serve"
mkdir -p "$PID_DIR"

# --- Argument Parsing ---
if [[ $# -lt 2 ]]; then
    echo "Usage: llm-serve.sh <model> <framework> [--context <size>]"
    echo ""
    echo "Models:     gemma4-12b, gemma4-26b, qwen3-vl-32b"
    echo "Frameworks: llama-cpp, ollama"
    echo ""
    echo "Default ports: llama-cpp=8080, ollama=11434"
    exit 1
fi

MODEL="$1"
FRAMEWORK="$2"
shift 2

CONTEXT_SIZE=8192
while [[ $# -gt 0 ]]; do
    case "$1" in
        --context) CONTEXT_SIZE="$2"; shift 2 ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
done

# Validate model
if [[ -z "${OLLAMA_TAGS[$MODEL]+x}" ]]; then
    echo "Error: Unknown model '$MODEL'. Valid: ${!OLLAMA_TAGS[*]}"
    exit 1
fi

# Validate framework
if [[ -z "${FRAMEWORK_PORTS[$FRAMEWORK]+x}" ]]; then
    echo "Error: Unknown framework '$FRAMEWORK'. Valid: ${!FRAMEWORK_PORTS[*]}"
    exit 1
fi

PORT="${FRAMEWORK_PORTS[$FRAMEWORK]}"

# --- Helper: Resolve Ollama blob paths ---
resolve_ollama_blob() {
    local model_tag="$1"
    local media_type="$2"
    local model_name="${model_tag%%:*}"
    local tag="${model_tag##*:}"
    local manifest="$OLLAMA_MANIFEST_BASE/$model_name/$tag"

    if [[ ! -f "$manifest" ]]; then
        echo "Error: Ollama manifest not found at $manifest" >&2
        echo "Run: ollama pull $model_tag" >&2
        return 1
    fi

    local digest
    digest=$(jq -r ".layers[] | select(.mediaType == \"$media_type\") | .digest" "$manifest" | head -1)

    if [[ -z "$digest" || "$digest" == "null" ]]; then
        return 1
    fi

    local blob_path="$OLLAMA_BASE/blobs/${digest//:/-}"
    if [[ ! -f "$blob_path" ]]; then
        echo "Error: Blob file not found at $blob_path" >&2
        return 1
    fi

    echo "$blob_path"
}

# --- Check if port is already in use ---
check_port() {
    if ss -tlnp 2>/dev/null | grep -q ":$PORT "; then
        echo "Error: Port $PORT is already in use."
        echo "Run: llm-stop.sh $FRAMEWORK"
        exit 1
    fi
}

# --- Start Functions ---

start_llama_cpp() {
    local ollama_tag="${OLLAMA_TAGS[$MODEL]}"
    local model_blob mmproj_blob

    model_blob=$(resolve_ollama_blob "$ollama_tag" "application/vnd.ollama.image.model") || exit 1
    echo "Model GGUF: $model_blob"

    local mmproj_args=()
    mmproj_blob=$(resolve_ollama_blob "$ollama_tag" "application/vnd.ollama.image.projector" 2>/dev/null) || true
    if [[ -n "$mmproj_blob" ]]; then
        echo "Vision mmproj: $mmproj_blob"
        mmproj_args=(--mmproj "$mmproj_blob")
    else
        echo "Warning: No vision projector (mmproj) found. Vision will not work."
    fi

    check_port

    echo "Starting llama-server on port $PORT (context=$CONTEXT_SIZE)..."
    setsid llama-server \
        --host 0.0.0.0 \
        --port "$PORT" \
        -m "$model_blob" \
        "${mmproj_args[@]}" \
        -c "$CONTEXT_SIZE" \
        -np 1 \
        -fa on \
        -dev CUDA0 \
        </dev/null > /tmp/llm-serve/llama-cpp.log 2>&1 &

    local pid=$!
    echo "$pid" > "$PID_DIR/llama-cpp.pid"
    echo "PID: $pid"
    echo "Log: /tmp/llm-serve/llama-cpp.log"
    echo "API: http://localhost:$PORT/v1/chat/completions"
}

start_ollama() {
    local ollama_tag="${OLLAMA_TAGS[$MODEL]}"

    # Ollama runs as a service, just verify it's up
    if ! ollama list &>/dev/null; then
        echo "Error: Ollama service is not running."
        echo "Run: sudo systemctl start ollama"
        exit 1
    fi

    echo "Ollama is running on port $PORT."
    echo "Model: $ollama_tag"
    echo "API: http://localhost:$PORT/v1/chat/completions"
    echo ""
    echo "Note: Ollama loads models on first request and unloads after idle timeout."
    echo "To pre-load: ollama run $ollama_tag '/no_think hi' (then Ctrl-C)"
}

# --- Dispatch ---
case "$FRAMEWORK" in
    llama-cpp) start_llama_cpp ;;
    ollama)    start_ollama ;;
esac
