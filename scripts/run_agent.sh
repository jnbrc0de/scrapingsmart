#!/bin/bash

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${YELLOW}Iniciando o Agente Inteligente de Extração de Dados...${NC}"

# Cria diretórios necessários
mkdir -p logs
mkdir -p data/strategy_history

# Verifica se o ambiente virtual existe
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}Criando ambiente virtual...${NC}"
    python -m venv venv
fi

# Ativa o ambiente virtual
source venv/bin/activate

# Instala/atualiza dependências
echo -e "${YELLOW}Instalando/atualizando dependências...${NC}"
pip install -r requirements.txt

# Instala o Playwright
echo -e "${YELLOW}Instalando browsers do Playwright...${NC}"
playwright install chromium

# Executa o agente
echo -e "${YELLOW}Executando o agente...${NC}"
python examples/smart_agent_example.py

# Verifica se a execução foi bem sucedida
if [ $? -eq 0 ]; then
    echo -e "${GREEN}Execução concluída com sucesso!${NC}"
else
    echo -e "${RED}Erro durante a execução!${NC}"
    exit 1
fi 