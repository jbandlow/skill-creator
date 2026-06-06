#!/usr/bin/env bash
set -euo pipefail

# llm-stop.sh — Stop a running LLM server.
#
# Usage:
#   llm-stop.sh <framework>   Stop a specific framework's server
#   llm-stop.sh all           Stop all non-Ollama servers
#
# Frameworks: llama-cpp, ollama, all

PID_DIR="/tmp/llm-serve"

stop_by_pid_file() {
    local framework="$1"
    local pid_file="$PID_DIR/${framework}.pid"

    if [[ ! -f "$pid_file" ]]; then
        echo "$framework: no PID file found (not started by llm-serve.sh?)"
        return 1
    fi

    local pid
    pid=$(cat "$pid_file")

    if kill -0 "$pid" 2>/dev/null; then
        echo "$framework: stopping PID $pid..."
        kill "$pid"
        # Wait up to 10 seconds for graceful shutdown
        for i in $(seq 1 10); do
            if ! kill -0 "$pid" 2>/dev/null; then
                echo "$framework: stopped."
                rm -f "$pid_file"
                return 0
            fi
            sleep 1
        done
        echo "$framework: force killing PID $pid..."
        kill -9 "$pid" 2>/dev/null || true
        rm -f "$pid_file"
    else
        echo "$framework: PID $pid is not running (stale PID file)."
        rm -f "$pid_file"
    fi
}

stop_framework() {
    local framework="$1"
    case "$framework" in
        llama-cpp)
            stop_by_pid_file "$framework"
            ;;
        ollama)
            echo "Ollama runs as a system service. To stop:"
            echo "  sudo systemctl stop ollama"
            ;;
        all)
            stop_by_pid_file "llama-cpp" 2>/dev/null || true
            echo "Note: Ollama service not stopped (use 'sudo systemctl stop ollama' if needed)."
            ;;
        *)
            echo "Usage: llm-stop.sh <llama-cpp|ollama|all>"
            exit 1
            ;;
    esac
}

if [[ $# -lt 1 ]]; then
    echo "Usage: llm-stop.sh <framework>"
    echo "Frameworks: llama-cpp, ollama, all"
    exit 1
fi

stop_framework "$1"
