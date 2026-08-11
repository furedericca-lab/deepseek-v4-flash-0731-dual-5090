#!/usr/bin/env bash
set -euo pipefail

repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
server="$repo_root/vendor/llama.cpp/build/bin/llama-server"
model=/data/linux-fast/models/DeepSeek-V4-Flash-0731/DeepSeek-V4-Flash-0731-reap-150b-Q2_K.gguf

if [[ ! -x "$server" ]]; then
  printf 'llama-server is not built: %s\n' "$server" >&2
  exit 1
fi

if [[ ! -f "$model" ]]; then
  printf 'runtime model is not available: %s\n' "$model" >&2
  exit 1
fi

exec "$server" \
  -m "$model" \
  -ngl all \
  -sm layer \
  -ts 1,1 \
  --no-kv-offload \
  -ctk f16 \
  -ctv f16 \
  -c 65536 \
  -np 1 \
  -b 1024 \
  -ub 256 \
  -fa on \
  --reasoning-format deepseek \
  --host 127.0.0.1 \
  --port 8000 \
  "$@"
