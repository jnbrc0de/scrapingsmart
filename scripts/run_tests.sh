#!/bin/bash

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${YELLOW}Iniciando testes...${NC}"

# Cria diretórios necessários
mkdir -p logs
mkdir -p data/strategy_history

# Executa testes com cobertura
pytest tests/ \
    --cov=src \
    --cov-report=term-missing \
    --cov-report=html \
    --cov-fail-under=80 \
    -v

# Verifica se os testes passaram
if [ $? -eq 0 ]; then
    echo -e "${GREEN}Todos os testes passaram!${NC}"
    
    # Abre o relatório de cobertura no navegador
    if command -v xdg-open > /dev/null; then
        xdg-open htmlcov/index.html
    elif command -v open > /dev/null; then
        open htmlcov/index.html
    fi
else
    echo -e "${RED}Alguns testes falharam!${NC}"
    exit 1
fi 