#!/usr/bin/env bash
# Simple script to run the FastAPI app for development
set -euo pipefail

PYMODULE="auto_red_teaming_prompt.api.server:app"
HOST="127.0.0.1"
PORT="8001"

exec uvicorn --host ${HOST} --port ${PORT} ${PYMODULE} --reload
