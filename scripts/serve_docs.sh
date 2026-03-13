#!/bin/bash
set -euo pipefail

cd "$(dirname "$0")/.."
echo "Abrindo observatorio em http://localhost:8000"
python3 -m http.server 8000 -d docs
