#!/bin/bash
# Encontra o diretório onde este script está (scripts/)
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Mata qualquer instância rodando chamando o kill.sh na mesma pasta
"$SCRIPT_DIR/kill.sh"

# Vai para a raiz para rodar o programa corretamente
cd "$PROJECT_ROOT"

clear
echo "Iniciando aplicação..."
source venv/bin/activate
python3 main.py &
