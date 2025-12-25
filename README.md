# SGR Discount Manager

> **⚠️ Demo Project**: This is a demonstration project showcasing how to use **Structured Generation & Reasoning (SGR)** with **vLLM** and the **xgrammar** backend to enforce strict JSON output schemas.

## What This Demo Shows

This project demonstrates:

- **Schema-Enforced LLM Outputs**: Using vLLM's `guided_json` with `xgrammar` backend to guarantee 100% valid structured responses
- **Pydantic Schema Integration**: Defining strict output schemas as Pydantic models that vLLM enforces at token generation level
- **Multi-Phase Agent Workflow**: Routing → Context Retrieval → Structured Decision Making
- **Hybrid Data Architecture**: Combining SQLite (hot store) + DuckDB (cold store) for feature retrieval

## Key Feature: xgrammar-Enforced Schemas

The core SGR capability is in [`sgr/utils/llm_client.py`](sgr/utils/llm_client.py):

```python
# Use vLLM's native guided_json with xgrammar backend
completion = self.client.chat.completions.create(
    model=self.model,
    messages=enhanced_messages,
    extra_body={
        "guided_json": schema_dict,           # Pydantic schema as dict
        "guided_decoding_backend": "xgrammar", # Hardware-enforced constraints
    },
)
```

This ensures the LLM can **only** generate tokens that form valid JSON matching your schema—no post-hoc validation failures.

## Architecture

- **Hot Store (SQLite)**: Real-time session data (Cart Value, Margin)
- **Cold Store (DuckDB)**: Historical analytical data (LTV, Churn Probability)
- **Agent**: Uses vLLM with xgrammar to enforce strict output schemas ([`RouterSchema`](sgr/models/schemas.py) and [`PricingLogic`](sgr/models/schemas.py))

## Prerequisites

- Python 3.10+
- `uv` for dependency management
- A machine capable of running `vLLM` (GPU recommended)

## Installation

1. Initialize the environment and install dependencies:

   ```bash
   uv sync
   ```

## Usage

### 1. Generate Synthetic Data

Initialize the SQLite and DuckDB databases with dummy user data:

```bash
uv run python -m scripts.setup_data
```

### 2. Start vLLM Server (Native Linux/WSL with GPU)

vLLM provides the best performance when running natively on Linux or WSL2 with NVIDIA GPU support. **Important:** vLLM is **not** included in this project's dependencies because it requires CUDA and has platform-specific installation requirements.

#### Prerequisites

- **NVIDIA GPU** with CUDA support (compute capability 7.0+)
- **CUDA Toolkit 12.x** installed ([installation guide](https://developer.nvidia.com/cuda-downloads))
- **Python 3.10-3.12** (vLLM does not yet support Python 3.13)
- For **WSL2**: Follow [NVIDIA CUDA on WSL](https://docs.nvidia.com/cuda/wsl-user-guide/) to enable GPU passthrough

#### Installation

Create a **separate virtual environment** for vLLM (do not install in this project's environment):

```bash
# Create a dedicated vLLM environment
cd ~
uv venv vllm-env --python 3.12
source vllm-env/bin/activate

# Install vLLM (this will install PyTorch with CUDA support)
uv pip install vllm

# Verify installation
python -c "import vllm; print(vllm.__version__)"
```

#### Running the Server

With the vLLM environment activated, start the OpenAI-compatible API server:

```bash
# Activate the environment (if not already active)
source ~/vllm-env/bin/activate

# Start the server
python -m vllm.entrypoints.openai.api_server \
  --model Qwen/Qwen2.5-7B-Instruct \
  --port 8000
```

The server will download the model on first run (~14GB for 7B model). Once ready, it exposes an OpenAI-compatible API at `http://localhost:8000`.

> **Note:**
>
> - **Guided Decoding**: `xgrammar` is the default backend in newer vLLM versions. Configure it per-request via `guided_json` or `guided_decoding_backend` in the API `extra_body` parameter (see [vLLM Structured Outputs docs](https://docs.vllm.ai/en/latest/features/structured_outputs.html)).
> - **Memory**: 7B models require ~16GB VRAM. For GPUs with less memory, use `Qwen/Qwen2.5-3B-Instruct` (~6GB) or add `--max-model-len 4096` to reduce context length.

### 2. Start vLLM Server (Docker CPU - Limited xgrammar Support)

> **⚠️ Note**: CPU mode may not include full xgrammar support. For guaranteed schema enforcement with xgrammar, use a GPU setup (Option 1 above).

For testing on Apple Silicon or systems without NVIDIA GPUs, you can build a CPU-enabled Docker image:

1. **Clone vLLM Repository**:

   ```bash
   git clone https://github.com/vllm-project/vllm.git
   cd vllm
   ```

2. **Build the CPU Image**:

   ```bash
   docker build -f docker/Dockerfile.cpu --tag vllm-cpu-env --build-arg max_jobs=8 .
   ```

   > **Troubleshooting:**
   > If the build fails with "Killed" or "ResourceExhausted", it's likely running out of memory. The default build uses 32 parallel jobs. We limit this with `--build-arg max_jobs=8`. If you still have issues (e.g. on an 8GB Mac), try lowering it further to `max_jobs=4`.

3. **Run the Server**:

   > **Note:** We use `Qwen2.5-3B-Instruct` with a reduced context length (`--max-model-len 4096`) to avoid OOM (Out of Memory) errors on CPU. See troubleshooting below if you want to use larger models.

   ```bash
   docker run --rm -it \
       --privileged=true \
       --shm-size=4g \
       -p 8000:8000 \
       -e VLLM_CPU_KVCACHE_SPACE=2 \
       -e VLLM_CPU_OMP_THREADS_BIND=all \
       vllm-cpu-env \
       --model Qwen/Qwen2.5-3B-Instruct \
       --dtype=bfloat16 \
       --max-model-len 8192
   ```

   _(Ensure Docker Desktop is running. You may need to adjust `--platform linux/arm64` on Mac if automatic detection fails, though building from source usually handles it.)_

   > **Troubleshooting OOM (Out of Memory) Errors:**
   >
   > If you see `RuntimeError: Engine core initialization failed` with exit code `-9`, the process was killed due to insufficient memory.
   >
   > **Memory Requirements for Qwen2.5-7B-Instruct:**
   >
   > - ~14GB for model weights (7B params × 2 bytes for bfloat16)
   > - - KV cache (controlled by `VLLM_CPU_KVCACHE_SPACE`)
   > - - runtime overhead
   > - **Total: ~20-24GB minimum**
   >
   > **Solutions:**
   >
   > 1. **Increase Docker memory**: In Docker Desktop → Settings → Resources, set memory to at least 24GB.
   >
   > 2. **Use a smaller model**:
   >
   >    ```bash
   >    --model Qwen/Qwen2.5-3B-Instruct   # ~6GB weights
   >    --model Qwen/Qwen2.5-1.5B-Instruct # ~3GB weights
   >    ```
   >
   > 3. **Reduce context length** (limits KV cache size):
   >    ```bash
   >    --max-model-len 8192  # Default is 32768
   >    ```
   >
   > **Troubleshooting Guided Decoding (Schema Validation Errors):**
   >
   > If you see validation errors like `Field required [type=missing, input_value={'response': ...}]`, the model is returning JSON with the wrong structure.
   >
   > **Cause:** The Docker CPU build doesn't include `xgrammar` or `outlines` guided decoding backends. Without hardware-enforced schema constraints, the model relies purely on instruction-following.
   >
   > **How the agent handles this:**
   >
   > - The schema is injected directly into the system prompt
   > - Works well for simple queries, but smaller models (1.5B) may occasionally produce malformed JSON
   >
   > **For 100% reliability:**
   >
   > - Use the 7B model on a GPU with guided decoding enabled
   > - Or use a larger model (3B+) on CPU which follows instructions more reliably

### 3. Run the Agent

Execute the agent script to see the negotiation in action:

```bash
uv run python -m sgr.agent
```

## Project Structure

```text
sgr/
├── __init__.py              # Public API exports
├── agent.py                 # Main agent orchestration
├── config/
│   └── constants.py         # Centralized configuration
├── models/
│   └── schemas.py           # Pydantic SGR schemas
├── prompts/
│   ├── routing.py           # Routing phase prompts
│   └── pricing.py           # Pricing phase prompts
├── store/
│   ├── hybrid_store.py      # Hot/Cold data retrieval
│   └── sql/                 # SQL query files
└── utils/
    ├── json_utils.py        # JSON parsing utilities
    └── llm_client.py        # LLM client wrapper
```

- `scripts/setup_data.py`: Script to generate synthetic data for testing.

## Maintenance

### Update Pre-commit Hooks

To update the pre-commit hooks to their latest versions:

```bash
uv run pre-commit autoupdate
```

### Update Python Dependencies

To update the `uv` lockfile and upgrade all packages:

```bash
uv lock --upgrade
uv sync
```
