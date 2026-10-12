# Sistema de Gestão de Calibração

Sistema desenvolvido para digitalizar e otimizar o gerenciamento de calibrações de equipamentos, substituindo uma planilha Excel complexa por uma aplicação estruturada.

## Objetivo

Simplificar o controle de equipamentos, o planejamento de calibrações e o registro de resultados, melhorando a organização, a rastreabilidade e a eficiência operacional.

## Tecnologias utilizadas

- **Python:** linguagem principal da aplicação.
- **Streamlit:** interface web interativa.
- **SQLite:** banco de dados relacional local.
- **Pandas:** manipulação e organização de dados.
- **Git e GitHub:** versionamento e gerenciamento do código-fonte.

## Funcionalidades

- Cadastro e gerenciamento de equipamentos.
- Organização de equipamentos por tipos.
- Associação de equipamentos a planos de calibração.
- Cadastro e consulta de pontos de calibração.
- Suporte a pontos numéricos, qualitativos, funcionais e de valor mínimo.
- Registro e consulta de calibrações.
- Armazenamento estruturado das informações em banco de dados.
- Interface para facilitar as operações do usuário.

## Arquitetura

```text
Usuário
   |
   v
Interface Streamlit
   |
   v
Lógica da aplicação Python
   |
   v
Banco de dados SQLite
   |
   v
Equipamentos, planos, pontos e registros
```

## Como executar

### Pré-requisitos

- Python instalado.
- Dependências do projeto instaladas.

### Criar e ativar o ambiente virtual

No Windows, execute na pasta do projeto:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### Instalar as dependências

Se o projeto possuir um arquivo `requirements.txt`:

```powershell
pip install -r requirements.txt
```

### Executar a aplicação

Na pasta que contém o arquivo `main.py`:

```powershell
streamlit run main.py
```

A aplicação normalmente ficará disponível em:

`http://localhost:8501`

## Banco de dados

O SQLite armazena os dados em um arquivo local. Esse arquivo deve ser preservado para evitar a perda dos registros.

Para uso compartilhado, é necessário definir uma estratégia adequada de armazenamento, backup, permissões e acesso simultâneo.

## Segurança e implantação

Para utilização empresarial, devem ser considerados:

- Controle de acesso e permissões.
- Backup periódico do banco de dados.
- Proteção das informações da empresa.
- Testes de integridade e recuperação dos dados.
- Definição do ambiente de execução e das atualizações do sistema.

## Status

Projeto em desenvolvimento, voltado à digitalização do processo de gestão de calibração de equipamentos e à melhoria da eficiência operacional.
