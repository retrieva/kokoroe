# Run GPT-OSS Model with VLLM

- openai/gpt-oss-20b
  - The smaller model
  - Only requires about 16GB of VRAM
- openai/gpt-oss-120b
  - Our larger full-sized model
  - Best with ≥60GB VRAM
  - Can fit on a single H100 or multi-GPU setups

## Install

```bash
uv venv --python 3.12 --seed
source .venv/bin/activate
uv pip install --pre vllm==0.10.1+gptoss \
    --extra-index-url https://wheels.vllm.ai/gpt-oss/ \
    --extra-index-url https://download.pytorch.org/whl/nightly/cu128 \
    --index-strategy unsafe-best-match
```

## Run

```
# For 20B
vllm serve openai/gpt-oss-20b

# For 120B
vllm serve openai/gpt-oss-120b
```
