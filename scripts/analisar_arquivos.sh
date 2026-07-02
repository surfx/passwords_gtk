#!/bin/bash
# Encontra o diretório onde este script está (scripts/) e entra nele
cd "$(dirname "${BASH_SOURCE[0]}")" || exit
PROJECT_ROOT="$(dirname "$PWD")"
VAULT_PATH="$PROJECT_ROOT/arquivos/.vault.gpg"

if [ ! -f "$VAULT_PATH" ]; then
    echo "Erro: Arquivo .vault.gpg não encontrado em $VAULT_PATH"
    exit 1
fi

echo "--- Analisador de Cofre (PWD Manager) ---"
read -s -p "Digite a Senha Mestre: " MASTER_PASS
echo ""

# Descriptografa e usa Python para ler o binário do Pickle
# O script Python lê do stdin, carrega o pickle e imprime formatado
gpg --batch --quiet --yes --passphrase "$MASTER_PASS" -d "$VAULT_PATH" 2>/dev/null | python3 -c "
import pickle
import sys
import pprint

try:
    data = sys.stdin.buffer.read()
    if not data:
        print('Erro: Nanhum dado recebido ou senha incorreta.')
        sys.exit(1)
    
    obj = pickle.loads(data)
    print('\nConteúdo do Cofre (Dicionário de Senhas):')
    pprint.pprint(obj)
except Exception as e:
    print(f'\nErro ao processar dados: {e}')
    sys.exit(1)
"

if [ $? -ne 0 ]; then
    echo "Falha na autenticação ou erro no processamento."
fi
