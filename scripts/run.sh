#!/bin/bash
# Encontra o diretório onde este script está (scripts/) e entra nele
cd "$(dirname "${BASH_SOURCE[0]}")" || exit
PROJECT_ROOT="$(dirname "$PWD")"

# Mata qualquer instância rodando chamando o kill.sh localmente
./kill.sh

# Vai para a raiz para rodar o programa corretamente
cd "$PROJECT_ROOT"

clear
echo "Iniciando aplicação..."
source venv/bin/activate
python3 main.py &
