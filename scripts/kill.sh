#!/bin/bash
# Encontra o diretório onde este script está (scripts/) e entra nele
cd "$(dirname "${BASH_SOURCE[0]}")" || exit
PROJECT_ROOT="$(dirname "$PWD")"

# Mata o processo do Python que está rodando o main.py
pkill -f "python3 $PROJECT_ROOT/main.py" || pkill -f "python3 main.py"
echo "Aplicação encerrada (se estava rodando)."
