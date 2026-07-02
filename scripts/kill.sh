#!/bin/bash
# Encontra o diretório onde este script está (scripts/)
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Mata o processo do Python que está rodando o main.py (usando o caminho absoluto do projeto)
pkill -f "python3 $PROJECT_ROOT/main.py" || pkill -f "python3 main.py"
echo "Aplicação encerrada (se estava rodando)."
