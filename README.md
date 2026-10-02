# SGR Discount Manager

Companion demo for the article [Schema-Guided Reasoning: vLLM, XGrammar, and Pydantic](https://slavadubrov.github.io/blog/2025/12/28/schema-guided-reasoning-vllm/).

A pricing agent asks a model served by vLLM for a structured discount proposal. vLLM's structured outputs constrain the JSON shape during generation. The application still checks that the completion finished, validates the JSON with Pydantic, and approves or rejects the discount with a policy function.

## What the demo shows

- **Schema-Guided Reasoning (SGR)**: Pydantic schemas list the fields the model fills, analysis first and the proposed discount last ([`sgr/models/schemas.py`](sgr/models/schemas.py)).
- **Routing and a cascade**: `RouterSchema` picks between fetching customer data and a direct reply; `PricingLogic` records the analysis and the proposal.
- **Constrained decoding with vLLM**: the client sends the JSON Schema in `structured_outputs`; the server selects the backend, here XGrammar.
- **Checks in application code**: `completed_content` rejects incomplete, refused, or empty completions; `approve_discount` enforces the discount policy ([`sgr/agent.py`](sgr/agent.py)).
- **Hybrid feature store**: SQLite holds the live session (cart value, margin); DuckDB holds history (lifetime value, churn probability).

The request in [`sgr/utils/llm_client.py`](sgr/utils/llm_client.py):

```python
# vLLM v0.12+ structured outputs. Configure the backend on the server.
completion = self.client.chat.completions.create(
    model=self.model,
    messages=enhanced_messages,
    temperature=DEFAULT_TEMPERATURE,
    extra_body={"structured_outputs": {"json": schema_dict}},
)

return schema_class.model_validate_json(completed_content(completion))
```

The schema constrains the JSON shape. It does not make the proposed discount correct. A token limit can also stop generation in the middle of the object; `completed_content` rejects that completion.

## Discount policy

`approve_discount` is the rule. It rejects proposals outside 0–20 percent, rounds down to hundredths of a percentage point, and rejects a discount above the cart's margin percentage. The business rules in the pricing prompt ([`sgr/prompts/pricing.py`](sgr/prompts/pricing.py)) guide the model toward the same limits, but only the function decides. The agent reports the approved percentage and does not issue a coupon.

## Prerequisites

- Python 3.13+ and [`uv`](https://docs.astral.sh/uv/) for this project
- For the full agent run, a machine that can run vLLM (an NVIDIA GPU is recommended). The offline tests need no model.

## Installation

```bash
uv sync
```

## Usage

### 1. Run the offline tests

These tests check the policy function and the completion check with synthetic inputs. They need no model and no vLLM server.

```bash
uv run pytest
```

### 2. Generate synthetic data

Create the SQLite and DuckDB databases with random demo users (`user_100` to `user_109`):

```bash
uv run python -m scripts.setup_data
```

### 3. Start a vLLM server (Linux or WSL2 with an NVIDIA GPU)

vLLM is **not** a dependency of this project, because it needs CUDA and has platform-specific installation requirements. Install it in a **separate virtual environment**. The [vLLM installation guide](https://docs.vllm.ai/en/latest/getting_started/installation/gpu/) lists the supported Python and CUDA versions. For WSL2, see [NVIDIA CUDA on WSL](https://docs.nvidia.com/cuda/wsl-user-guide/).

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

Start the OpenAI-compatible server with XGrammar as the structured-output backend:

```bash
source ~/vllm-env/bin/activate

vllm serve Qwen/Qwen2.5-7B-Instruct \
    --port 8000 \
    --structured-outputs-config.backend xgrammar
```

The server downloads the model on the first run (about 15 GB for the 7B model). It then serves an OpenAI-compatible API at `http://localhost:8000`. The client reads the model name from the server.

> **Memory**: 7B models need about 16 GB of GPU memory. For GPUs with less memory, use `Qwen/Qwen2.5-3B-Instruct` or add `--max-model-len 4096` to reduce context length.

### 3 (alternative). Start a vLLM server in Docker on a CPU

For testing on Apple Silicon or systems without an NVIDIA GPU, you can build a CPU image. It is slow, and a small model follows the prompt less well.

1. **Clone the vLLM repository**:

   ```bash
   git clone https://github.com/vllm-project/vllm.git
   cd vllm
   ```

2. **Build the CPU image**:

   ```bash
   docker build -f docker/Dockerfile.cpu --tag vllm-cpu-env --build-arg max_jobs=8 .
   ```

   > **Troubleshooting:** If the build fails with "Killed" or "ResourceExhausted", it is running out of memory. `--build-arg max_jobs=8` limits parallel jobs; on an 8 GB Mac, try `max_jobs=4`.

3. **Run the server**:

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

   _(Ensure Docker Desktop is running. You may need `--platform linux/arm64` on a Mac if automatic detection fails.)_

   > **Troubleshooting out-of-memory errors:** If you see `RuntimeError: Engine core initialization failed` with exit code `-9`, the process ran out of memory. Increase Docker's memory limit (Docker Desktop → Settings → Resources), use a smaller model such as `Qwen/Qwen2.5-1.5B-Instruct`, or lower `--max-model-len`.

### 4. Run the agent

```bash
uv run python -m sgr.agent
```

Illustrative output (the values depend on the random data and the model):

```text
🤖 Processing: 'I want a discount or I'm leaving!' for user_102
📍 Routing decision: fetch_user_features
🔍 Fetching features for user_102...
   [Data] LTV: $1500.0 | Margin: 20.0%
🧠 Proposing Offer (Schema Enforced)...
   [Audit] Math: Cart $200 * 0.20 Margin = $40
   [Audit] Approved Discount: 15.00%

💬 Final Reply: Illustrative approved discount: 15.00%. No coupon has been issued.
```

If the proposal fails the policy, the reply is `No discount approved: the proposal failed the pricing policy.` If the completion is incomplete or does not match the schema, the run stops with a `ValueError` or a Pydantic `ValidationError`.

## Project structure

```text
sgr/
├── __init__.py              # Public API exports
├── agent.py                 # Agent orchestration and approve_discount
├── config/
│   └── constants.py         # Configuration values
├── models/
│   └── schemas.py           # Pydantic SGR schemas
├── prompts/
│   ├── routing.py           # Routing phase prompts
│   └── pricing.py           # Pricing phase prompts
├── store/
│   ├── hybrid_store.py      # Hot/cold data retrieval
│   └── sql/                 # SQL query files
└── utils/
    └── llm_client.py        # vLLM client and completed_content
scripts/
└── setup_data.py            # Synthetic data generation
tests/
└── test_policy.py           # Offline policy and completion tests
```
