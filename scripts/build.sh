#!/bin/bash
# Encontra o diretório onde este script está (scripts/)
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Garante que o processo anterior seja morto chamando o kill.sh na mesma pasta
"$SCRIPT_DIR/kill.sh"

# Volta para a raiz para gerenciar venv e dependências
cd "$PROJECT_ROOT"

if [ ! -d "venv" ]; then
    echo "Criando ambiente virtual em $PROJECT_ROOT/venv..."
    python3 -m venv venv
fi

echo "Verificando dependências..."
source venv/bin/activate
python3 -m pip install PyQt6 --quiet

echo "Build concluído com sucesso."
