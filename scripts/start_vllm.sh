#!/bin/bash
# ============================================================================
# Quick Start Script for vLLM
# ============================================================================
#
# LEARNING NOTES:
#
# This script helps you get started with self-hosted LLM inference.
# It supports three modes:
#   1. Docker (recommended for production)
#   2. Direct Python (for development)
#   3. Local with Ollama (easiest for dev)
#
# Prerequisites:
#   - NVIDIA GPU with CUDA support
#   - nvidia-container-toolkit (for Docker)
#   - At least 24GB VRAM for Llama 8B
#
# Usage:
#   ./scripts/start_vllm.sh docker    # Start with Docker
#   ./scripts/start_vllm.sh python    # Start directly
#   ./scripts/start_vllm.sh ollama    # Use Ollama instead
#
# ============================================================================

set -e

# Default settings
MODEL="${VLLM_MODEL:-meta-llama/Llama-3.1-8B-Instruct}"
MAX_MODEL_LEN="${VLLM_MAX_MODEL_LEN:-8192}"
GPU_MEMORY="${VLLM_GPU_MEMORY:-0.90}"
TENSOR_PARALLEL="${VLLM_TENSOR_PARALLEL:-1}"
PORT="${VLLM_PORT:-8000}"

print_banner() {
    echo "╔════════════════════════════════════════════════════════════════╗"
    echo "║              Self-Hosted LLM Quick Start                       ║"
    echo "╠════════════════════════════════════════════════════════════════╣"
    echo "║  Model: $MODEL"
    echo "║  Context: $MAX_MODEL_LEN tokens"
    echo "║  Port: $PORT"
    echo "╚════════════════════════════════════════════════════════════════╝"
}

check_gpu() {
    echo "🔍 Checking GPU..."
    if command -v nvidia-smi &> /dev/null; then
        nvidia-smi --query-gpu=name,memory.total --format=csv,noheader
    else
        echo "❌ nvidia-smi not found. Make sure NVIDIA drivers are installed."
        exit 1
    fi
}

start_docker() {
    echo "🐳 Starting vLLM with Docker..."
    
    # Check if nvidia-container-toolkit is installed
    if ! docker info 2>/dev/null | grep -q "Runtimes.*nvidia"; then
        echo "❌ nvidia-container-toolkit not detected."
        echo "Install with: https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html"
        exit 1
    fi
    
    # Pull image if not exists
    docker pull vllm/vllm-openai:latest
    
    # Start container
    docker run -d \
        --name character-chat-vllm \
        --gpus all \
        -p $PORT:8000 \
        -v ~/.cache/huggingface:/root/.cache/huggingface \
        -e HUGGING_FACE_HUB_TOKEN="${HUGGING_FACE_HUB_TOKEN:-}" \
        vllm/vllm-openai:latest \
        --model "$MODEL" \
        --max-model-len "$MAX_MODEL_LEN" \
        --gpu-memory-utilization "$GPU_MEMORY" \
        --tensor-parallel-size "$TENSOR_PARALLEL" \
        --trust-remote-code
    
    echo "✅ vLLM started in Docker container 'character-chat-vllm'"
    echo "📡 API available at: http://localhost:$PORT/v1"
    echo ""
    echo "Test with:"
    echo "  curl http://localhost:$PORT/v1/models"
}

start_python() {
    echo "🐍 Starting vLLM directly with Python..."
    
    # Check if vllm is installed
    if ! python -c "import vllm" 2>/dev/null; then
        echo "Installing vLLM..."
        pip install vllm
    fi
    
    # Start server
    python -m vllm.entrypoints.openai.api_server \
        --model "$MODEL" \
        --max-model-len "$MAX_MODEL_LEN" \
        --gpu-memory-utilization "$GPU_MEMORY" \
        --tensor-parallel-size "$TENSOR_PARALLEL" \
        --host 0.0.0.0 \
        --port "$PORT" \
        --trust-remote-code
}

start_ollama() {
    echo "🦙 Starting with Ollama (local development mode)..."
    
    # Check if ollama is installed
    if ! command -v ollama &> /dev/null; then
        echo "Installing Ollama..."
        curl -fsSL https://ollama.com/install.sh | sh
    fi
    
    # Pull model
    OLLAMA_MODEL="${OLLAMA_MODEL:-llama3.1:8b}"
    echo "Pulling model: $OLLAMA_MODEL"
    ollama pull "$OLLAMA_MODEL"
    
    # Start server
    echo "Starting Ollama server..."
    ollama serve &
    
    echo "✅ Ollama started"
    echo "📡 API available at: http://localhost:11434"
    echo ""
    echo "Test with:"
    echo "  ollama run $OLLAMA_MODEL 'Hello!'"
}

stop_all() {
    echo "🛑 Stopping all LLM servers..."
    docker stop character-chat-vllm 2>/dev/null || true
    docker rm character-chat-vllm 2>/dev/null || true
    pkill -f "vllm.entrypoints" 2>/dev/null || true
    pkill -f "ollama serve" 2>/dev/null || true
    echo "✅ Stopped"
}

health_check() {
    echo "🏥 Checking health..."
    
    # vLLM
    if curl -s http://localhost:$PORT/v1/models > /dev/null 2>&1; then
        echo "✅ vLLM is running at http://localhost:$PORT"
        curl -s http://localhost:$PORT/v1/models | python -m json.tool
    else
        echo "❌ vLLM not responding"
    fi
    
    # Ollama
    if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
        echo "✅ Ollama is running at http://localhost:11434"
        curl -s http://localhost:11434/api/tags | python -m json.tool
    else
        echo "❌ Ollama not responding"
    fi
}

# Main
case "${1:-help}" in
    docker)
        print_banner
        check_gpu
        start_docker
        ;;
    python)
        print_banner
        check_gpu
        start_python
        ;;
    ollama)
        start_ollama
        ;;
    stop)
        stop_all
        ;;
    health)
        health_check
        ;;
    *)
        echo "Usage: $0 {docker|python|ollama|stop|health}"
        echo ""
        echo "Commands:"
        echo "  docker  - Start vLLM in Docker container (recommended)"
        echo "  python  - Start vLLM directly with Python"
        echo "  ollama  - Use Ollama for local development"
        echo "  stop    - Stop all LLM servers"
        echo "  health  - Check server health"
        echo ""
        echo "Environment variables:"
        echo "  VLLM_MODEL       - Model to serve (default: meta-llama/Llama-3.1-8B-Instruct)"
        echo "  VLLM_MAX_MODEL_LEN - Context length (default: 8192)"
        echo "  VLLM_GPU_MEMORY  - GPU memory utilization (default: 0.90)"
        echo "  VLLM_PORT        - Port to listen on (default: 8000)"
        echo "  HUGGING_FACE_HUB_TOKEN - For gated models (Llama, Mistral)"
        ;;
esac

