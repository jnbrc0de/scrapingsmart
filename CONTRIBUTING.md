# Guia de Contribuição - SmartScraping

## Como Contribuir

### 1. Preparação do Ambiente

1. **Fork do Projeto**
   ```bash
   # Clone seu fork
   git clone https://github.com/seu-usuario/smartscraping.git
   cd smartscraping
   
   # Adicione o repositório original
   git remote add upstream https://github.com/original/smartscraping.git
   ```

2. **Configuração do Ambiente**
   ```bash
   # Crie um ambiente virtual
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   venv\Scripts\activate     # Windows
   
   # Instale dependências
   pip install -r requirements.txt
   pip install -r requirements-dev.txt
   ```

3. **Configuração do Pre-commit**
   ```bash
   # Instale o pre-commit
   pip install pre-commit
   
   # Configure os hooks
   pre-commit install
   ```

### 2. Fluxo de Trabalho

1. **Crie uma Branch**
   ```bash
   # Atualize sua branch main
   git checkout main
   git pull upstream main
   
   # Crie uma nova branch
   git checkout -b feature/nova-feature
   ```

2. **Desenvolvimento**
   - Siga as convenções de código
   - Escreva testes
   - Atualize a documentação
   - Mantenha commits atômicos

3. **Testes**
   ```bash
   # Execute os testes
   pytest
   
   # Verifique a cobertura
   pytest --cov=src tests/
   ```

4. **Linting e Formatação**
   ```bash
   # Verifique o código
   flake8
   black .
   isort .
   mypy .
   ```

5. **Commit**
   ```bash
   # Adicione as mudanças
   git add .
   
   # Faça o commit
   git commit -m "feat: adiciona nova feature"
   ```

6. **Push**
   ```bash
   # Envie para seu fork
   git push origin feature/nova-feature
   ```

7. **Pull Request**
   - Crie um PR no GitHub
   - Descreva as mudanças
   - Referencie issues
   - Aguarde revisão

### 3. Convenções de Código

#### 3.1 Python
- Siga PEP 8
- Use type hints
- Documente funções
- Escreva docstrings

#### 3.2 Commits
- Use Conventional Commits
- Seja descritivo
- Mantenha mensagens curtas

#### 3.3 Branches
- `feature/*` para novas features
- `fix/*` para correções
- `docs/*` para documentação
- `test/*` para testes

### 4. Testes

#### 4.1 Unitários
```python
def test_example():
    # Arrange
    input = "test"
    
    # Act
    result = function(input)
    
    # Assert
    assert result == expected
```

#### 4.2 Integração
```python
async def test_integration():
    # Setup
    browser = BrowserManager()
    
    # Test
    result = await agent.extract()
    
    # Verify
    assert result.success
```

### 5. Documentação

#### 5.1 Código
```python
def function(param: str) -> bool:
    """
    Descrição da função.
    
    Args:
        param: Descrição do parâmetro
        
    Returns:
        Descrição do retorno
    """
    pass
```

#### 5.2 README
- Atualize o README
- Documente mudanças
- Adicione exemplos
- Mantenha atualizado

### 6. Revisão de Código

#### 6.1 Checklist
- [ ] Código segue convenções
- [ ] Testes passam
- [ ] Documentação atualizada
- [ ] Sem warnings
- [ ] Cobertura adequada

#### 6.2 Feedback
- Seja construtivo
- Explique sugestões
- Mantenha foco
- Respeite outros

### 7. Manutenção

#### 7.1 Dependências
- Mantenha atualizadas
- Verifique segurança
- Teste atualizações
- Documente mudanças

#### 7.2 Issues
- Use templates
- Seja específico
- Forneça contexto
- Siga up

### 8. Comunicação

#### 8.1 Issues
- Use labels
- Atribua responsáveis
- Defina milestones
- Mantenha atualizado

#### 8.2 Discussões
- Seja respeitoso
- Mantenha foco
- Contribua construtivamente
- Ajude outros

### 9. Recursos

#### 9.1 Links Úteis
- [Documentação](docs/)
- [Issues](https://github.com/original/smartscraping/issues)
- [Discussions](https://github.com/original/smartscraping/discussions)
- [Wiki](https://github.com/original/smartscraping/wiki)

#### 9.2 Ferramentas
- VS Code
- PyCharm
- Git
- GitHub

### 10. Suporte

#### 10.1 Canais
- Issues
- Discussions
- Email
- Slack

#### 10.2 Responsáveis
- Mantenedores
- Colaboradores
- Comunidade
- Suporte 