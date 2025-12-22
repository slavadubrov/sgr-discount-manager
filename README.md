# SGR Discount Manager

An AI-powered pricing negotiation agent using **Structured Generation & Reasoning (SGR)** and a **Hybrid Data Architecture** (SQLite + DuckDB).

## Architecture

- **Hot Store (SQLite)**: Real-time session data (Cart Value, Margin).
- **Cold Store (DuckDB)**: Historical analytical data (LTV, Churn Probability).
- **Agent**: Uses `vLLM` with `xgrammar` to enforce strict output schemas (`RouterSchema` and `PricingLogic`).

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

### 2. Start vLLM Server

In a separate terminal, start the vLLM server. This serves the local LLM that the agent communicates with.

```bash
uv run python -m vllm.entrypoints.openai.api_server \
  --model Qwen/Qwen2.5-7B-Instruct \
  --port 8000
```

> **Note:**
>
> 1. `vllm` and `xgrammar` are **not** included in the default `uv sync` due to platform-specific constraints.
> 2. **Recommended**: Run vLLM using Docker (CPU mode), as described below.
> 3. **Guided Decoding**: `xgrammar` is the default backend in newer vLLM versions. Configure it per-request via `guided_json` or `guided_decoding_backend` in the API `extra_body` parameter (see [vLLM Structured Outputs docs](https://docs.vllm.ai/en/latest/features/structured_outputs.html)).

### 2. Start vLLM Server (Docker CPU)

Since vLLM installation can be tricky on some platforms, I recommend building a CPU-enabled Docker image. This is the only way to run vLLM on Apple Silicon at the moment of writing.

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
