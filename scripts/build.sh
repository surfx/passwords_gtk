#!/bin/bash
# Encontra o diretório onde este script está (scripts/) e entra nele
cd "$(dirname "${BASH_SOURCE[0]}")" || exit
PROJECT_ROOT="$(dirname "$PWD")"

# Garante que o processo anterior seja morto chamando o kill.sh localmente
./kill.sh

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
