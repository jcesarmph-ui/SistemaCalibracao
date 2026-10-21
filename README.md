# Sistema de Gestão de Calibração

<p align="center">
  <img src="https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python"/>
  <img src="https://img.shields.io/badge/Streamlit-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white" alt="Streamlit"/>
  <img src="https://img.shields.io/badge/SQLite-003B57?style=for-the-badge&logo=sqlite&logoColor=white" alt="SQLite"/>
  <img src="https://img.shields.io/badge/Pandas-150458?style=for-the-badge&logo=pandas&logoColor=white" alt="Pandas"/>
  <img src="https://img.shields.io/badge/Git-F05032?style=for-the-badge&logo=git&logoColor=white" alt="Git"/>
  <img src="https://img.shields.io/badge/GitHub-181717?style=for-the-badge&logo=github&logoColor=white" alt="GitHub"/>
</p>

<p align="center">
  Aplicação para digitalização e gerenciamento de processos de calibração, com organização de equipamentos, planos, pontos de medição e registros históricos.
</p>

---

## Visão Geral

O Sistema de Gestão de Calibração é uma aplicação desenvolvida para estruturar e simplificar o gerenciamento de calibrações de equipamentos, substituindo um fluxo de trabalho baseado em planilhas extensas por uma solução com interface interativa e armazenamento estruturado.

A aplicação centraliza informações técnicas e registros operacionais, facilitando a consulta dos equipamentos, a organização dos planos de calibração e o acompanhamento do histórico.

O projeto aplica conceitos de desenvolvimento de software, modelagem de dados, automação de processos administrativos e melhoria contínua em um cenário relacionado à gestão da qualidade.

## Objetivos

- Digitalizar o gerenciamento de calibrações.
- Organizar os cadastros de equipamentos e seus respectivos tipos.
- Estruturar planos e pontos de calibração.
- Centralizar os registros e o histórico das calibrações.
- Facilitar a consulta e a manutenção das informações.
- Reduzir a dependência de planilhas extensas e de operações manuais.
- Melhorar a organização e a rastreabilidade das informações técnicas.

## Funcionalidades

### Gestão de Equipamentos

- Cadastro e gerenciamento de equipamentos.
- Organização por tipos de equipamento.
- Associação entre equipamentos e planos de calibração.
- Consulta das informações cadastradas.

### Planos e Pontos de Calibração

- Cadastro e organização de planos de calibração.
- Definição de pontos de calibração.
- Suporte a diferentes categorias de pontos:
  - Numéricos.
  - Qualitativos.
  - Funcionais.
  - De valor mínimo.

### Registros e Histórico

- Registro das calibrações realizadas.
- Consulta dos registros armazenados.
- Organização dos dados para acompanhamento do histórico.
- Armazenamento persistente em banco de dados local.

## Arquitetura da Aplicação

A aplicação segue uma arquitetura organizada em camadas, separando a interface, a lógica de processamento e a persistência dos dados.

```text
┌──────────────────────────────────────┐
│                Usuário               │
└──────────────────┬───────────────────┘
                   │
                   ▼
┌──────────────────────────────────────┐
│        Interface Streamlit           │
│       Navegação e formulários        │
└──────────────────┬───────────────────┘
                   │
                   ▼
┌──────────────────────────────────────┐
│          Lógica em Python            │
│   Regras e processamento dos dados   │
└──────────────────┬───────────────────┘
                   │
                   ▼
┌──────────────────────────────────────┐
│             Banco SQLite             │
│       Persistência dos registros     │
└──────────────────┬───────────────────┘
                   │
                   ▼
┌──────────────────────────────────────┐
│ Equipamentos, planos, pontos e       │
│ registros de calibração              │
└──────────────────────────────────────┘
```

## Tecnologias e Ferramentas

| Tecnologia | Aplicação no projeto |
|---|---|
| Python | Implementação da lógica e das regras da aplicação. |
| Streamlit | Construção da interface interativa. |
| SQLite | Armazenamento estruturado dos dados. |
| Pandas | Manipulação e organização de dados tabulares. |
| Git | Controle de versão do código-fonte. |
| GitHub | Hospedagem e documentação do repositório. |

## Estrutura do Repositório

```text
SistemaCalibracao/
├── app/
├── assets/
├── data/
├── scripts/
├── .vscode/
├── Abrir_CALIB.bat
├── main.py
├── requirements.txt
└── README.md
```

- `app/`: componentes e módulos da aplicação.
- `assets/`: recursos utilizados pela interface.
- `data/`: arquivos relacionados ao armazenamento dos dados.
- `scripts/`: scripts auxiliares.
- `main.py`: ponto de entrada da aplicação.
- `requirements.txt`: dependências do projeto.
- `Abrir_CALIB.bat`: arquivo auxiliar para iniciar a aplicação no Windows.

## Aplicações e Competências Demonstradas

- Desenvolvimento de aplicações em Python.
- Construção de interfaces com Streamlit.
- Modelagem e persistência de dados relacionais.
- Digitalização de processos de qualidade.
- Organização e rastreabilidade de informações técnicas.
- Estruturação de software para resolução de problemas operacionais.

---

**Projeto de desenvolvimento de software aplicado à gestão da qualidade, com foco na organização de dados, digitalização de processos e melhoria da eficiência operacional.**


## Atualização: lixeira e resultados visuais

Exclusão lógica, restauração segura, exclusão permanente protegida, resultados coloridos e melhorias no cronograma. A migração cria backup automático antes de adicionar os campos da lixeira.

Consulte [as regras, os arquivos modificados e a validação](docs/ATUALIZACAO_LIXEIRA.md). Para executar os testes: `python -m unittest discover -s tests -v`. O executável precisa ser gerado novamente para incorporar a atualização.
