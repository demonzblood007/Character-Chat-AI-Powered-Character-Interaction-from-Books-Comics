# ============================================================================
# Quick Start Script for vLLM (Windows PowerShell)
# ============================================================================
#
# LEARNING NOTES:
#
# This script helps you get started with self-hosted LLM inference on Windows.
# Note: For best performance, use WSL2 with GPU passthrough.
#
# Prerequisites:
#   - NVIDIA GPU with CUDA support
#   - Docker Desktop with WSL2 backend
#   - Or: WSL2 with nvidia-container-toolkit
#
# Usage:
#   .\scripts\start_vllm.ps1 docker    # Start with Docker
#   .\scripts\start_vllm.ps1 ollama    # Use Ollama instead
#   .\scripts\start_vllm.ps1 stop      # Stop servers
#   .\scripts\start_vllm.ps1 health    # Check health
#
# ============================================================================

param(
    [Parameter(Position=0)]
    [ValidateSet("docker", "ollama", "stop", "health", "help")]
    [string]$Command = "help"
)

# Default settings
$env:VLLM_MODEL = if ($env:VLLM_MODEL) { $env:VLLM_MODEL } else { "meta-llama/Llama-3.1-8B-Instruct" }
$env:VLLM_MAX_MODEL_LEN = if ($env:VLLM_MAX_MODEL_LEN) { $env:VLLM_MAX_MODEL_LEN } else { "8192" }
$env:VLLM_GPU_MEMORY = if ($env:VLLM_GPU_MEMORY) { $env:VLLM_GPU_MEMORY } else { "0.90" }
$env:VLLM_PORT = if ($env:VLLM_PORT) { $env:VLLM_PORT } else { "8000" }

function Show-Banner {
    Write-Host @"
╔════════════════════════════════════════════════════════════════╗
║              Self-Hosted LLM Quick Start                       ║
╠════════════════════════════════════════════════════════════════╣
║  Model: $($env:VLLM_MODEL)
║  Context: $($env:VLLM_MAX_MODEL_LEN) tokens
║  Port: $($env:VLLM_PORT)
╚════════════════════════════════════════════════════════════════╝
"@
}

function Test-GPU {
    Write-Host "🔍 Checking GPU..."
    try {
        $output = & nvidia-smi --query-gpu=name,memory.total --format=csv,noheader 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Host "✅ GPU found:" -ForegroundColor Green
            Write-Host $output
        } else {
            throw "nvidia-smi failed"
        }
    } catch {
        Write-Host "❌ nvidia-smi not found. Make sure NVIDIA drivers are installed." -ForegroundColor Red
        exit 1
    }
}

function Start-DockerVLLM {
    Show-Banner
    Test-GPU
    
    Write-Host "🐳 Starting vLLM with Docker..."
    
    # Check Docker
    try {
        docker info | Out-Null
    } catch {
        Write-Host "❌ Docker not running. Start Docker Desktop first." -ForegroundColor Red
        exit 1
    }
    
    # Stop existing container if running
    docker stop character-chat-vllm 2>$null
    docker rm character-chat-vllm 2>$null
    
    # Pull image
    Write-Host "Pulling vLLM image..."
    docker pull vllm/vllm-openai:latest
    
    # Start container
    $hfToken = if ($env:HUGGING_FACE_HUB_TOKEN) { $env:HUGGING_FACE_HUB_TOKEN } else { "" }
    
    docker run -d `
        --name character-chat-vllm `
        --gpus all `
        -p "$($env:VLLM_PORT):8000" `
        -v "$env:USERPROFILE\.cache\huggingface:/root/.cache/huggingface" `
        -e "HUGGING_FACE_HUB_TOKEN=$hfToken" `
        vllm/vllm-openai:latest `
        --model $env:VLLM_MODEL `
        --max-model-len $env:VLLM_MAX_MODEL_LEN `
        --gpu-memory-utilization $env:VLLM_GPU_MEMORY `
        --trust-remote-code
    
    Write-Host "✅ vLLM started in Docker container 'character-chat-vllm'" -ForegroundColor Green
    Write-Host "📡 API available at: http://localhost:$($env:VLLM_PORT)/v1"
    Write-Host ""
    Write-Host "Test with:"
    Write-Host "  curl http://localhost:$($env:VLLM_PORT)/v1/models"
}

function Start-Ollama {
    Write-Host "🦙 Starting with Ollama (local development mode)..."
    
    # Check if Ollama is installed
    $ollamaPath = Get-Command ollama -ErrorAction SilentlyContinue
    if (-not $ollamaPath) {
        Write-Host "Ollama not found. Installing..."
        Write-Host "Please download from: https://ollama.com/download/windows"
        Start-Process "https://ollama.com/download/windows"
        exit 1
    }
    
    # Pull model
    $model = if ($env:OLLAMA_MODEL) { $env:OLLAMA_MODEL } else { "llama3.1:8b" }
    Write-Host "Pulling model: $model"
    & ollama pull $model
    
    # Start server
    Write-Host "Starting Ollama server..."
    Start-Process ollama -ArgumentList "serve" -WindowStyle Hidden
    
    Write-Host "✅ Ollama started" -ForegroundColor Green
    Write-Host "📡 API available at: http://localhost:11434"
    Write-Host ""
    Write-Host "Test with:"
    Write-Host "  ollama run $model 'Hello!'"
}

function Stop-AllServers {
    Write-Host "🛑 Stopping all LLM servers..."
    
    docker stop character-chat-vllm 2>$null
    docker rm character-chat-vllm 2>$null
    
    Get-Process -Name "ollama" -ErrorAction SilentlyContinue | Stop-Process -Force
    
    Write-Host "✅ Stopped" -ForegroundColor Green
}

function Test-Health {
    Write-Host "🏥 Checking health..."
    
    # vLLM
    try {
        $response = Invoke-RestMethod -Uri "http://localhost:$($env:VLLM_PORT)/v1/models" -TimeoutSec 5
        Write-Host "✅ vLLM is running at http://localhost:$($env:VLLM_PORT)" -ForegroundColor Green
        $response | ConvertTo-Json -Depth 3
    } catch {
        Write-Host "❌ vLLM not responding" -ForegroundColor Red
    }
    
    # Ollama
    try {
        $response = Invoke-RestMethod -Uri "http://localhost:11434/api/tags" -TimeoutSec 5
        Write-Host "✅ Ollama is running at http://localhost:11434" -ForegroundColor Green
        $response | ConvertTo-Json -Depth 3
    } catch {
        Write-Host "❌ Ollama not responding" -ForegroundColor Red
    }
}

function Show-Help {
    Write-Host @"
Usage: .\scripts\start_vllm.ps1 {docker|ollama|stop|health|help}

Commands:
  docker  - Start vLLM in Docker container (recommended)
  ollama  - Use Ollama for local development
  stop    - Stop all LLM servers
  health  - Check server health
  help    - Show this help

Environment variables:
  VLLM_MODEL         - Model to serve (default: meta-llama/Llama-3.1-8B-Instruct)
  VLLM_MAX_MODEL_LEN - Context length (default: 8192)
  VLLM_GPU_MEMORY    - GPU memory utilization (default: 0.90)
  VLLM_PORT          - Port to listen on (default: 8000)
  HUGGING_FACE_HUB_TOKEN - For gated models (Llama, Mistral)

Examples:
  .\scripts\start_vllm.ps1 docker
  `$env:VLLM_MODEL="mistralai/Mistral-7B-Instruct-v0.2"; .\scripts\start_vllm.ps1 docker
"@
}

# Main
switch ($Command) {
    "docker" { Start-DockerVLLM }
    "ollama" { Start-Ollama }
    "stop" { Stop-AllServers }
    "health" { Test-Health }
    default { Show-Help }
}

