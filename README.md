# JARVIS Acadêmico API

JARVIS Acadêmico é uma API backend desenvolvida em Python/FastAPI para apoiar estudantes na organização acadêmica e na consulta inteligente a materiais de estudo. O projeto combina RAG (Retrieval-Augmented Generation), Tool Calling, agenda acadêmica e gerenciamento de tarefas, mantendo uma arquitetura modular, assíncrona e simples de explicar em contexto acadêmico.

O objetivo do projeto é demonstrar a aplicação prática de técnicas modernas de Inteligência Artificial em um assistente acadêmico capaz de organizar informações, recuperar conhecimento e auxiliar estudantes em atividades do dia a dia.

---

# Funcionalidades

- Materiais de estudo com RAG
  - Upload de arquivos PDF/TXT
  - Extração de texto
  - Chunking com janela deslizante
  - Busca BM25, vetorial e híbrida
  - Respostas contextualizadas usando Gemma 12B

- Agenda acadêmica
  - Cadastro de aulas, provas, reuniões e eventos
  - Consultas por período
  - Consultas de hoje e semana atual
  - Recorrência semanal simples

- Tarefas acadêmicas
  - Criação de tarefas
  - Listagem com filtros
  - Conclusão de tarefas
  - Remoção de tarefas

- Tool Calling
  - A LLM decide dinamicamente quais ferramentas utilizar
  - Integração com agenda, tarefas e RAG
  - Logs completos de execução

- Testes automatizados
  - Testes unitários
  - Testes de integração
  - Mocks de banco e IA

---

# Stack Tecnológica

- Python 3.11+
- FastAPI
- PostgreSQL 16
- SQLAlchemy 2.0 Assíncrono
- AsyncPG
- Pydantic V2
- Loguru
- OpenAI SDK
- Gemma 12B
- Sentence Transformers
- FAISS
- rank-bm25
- PyMuPDF / pypdf
- Docker e Docker Compose
- pytest
- pytest-asyncio
- pytest-mock
- httpx

---

# Arquitetura

O projeto segue uma arquitetura modular em camadas:

```txt
Routes -> Services -> Repositories -> Banco de Dados
```

## Camadas

### Routes
Recebem as requisições HTTP e delegam o processamento para os services.

### Services
Concentram regras de negócio, validações, logs, conversões de timezone, chamadas de IA e fluxo RAG.

### Repositories
Responsáveis pelo acesso ao banco utilizando SQLAlchemy assíncrono.

### Models
Representam as tabelas do banco de dados.

### Schemas
Definem os contratos de entrada e saída da API utilizando Pydantic V2.

---

# Arquitetura de IA

O núcleo inteligente do sistema utiliza:

- Retrieval-Augmented Generation (RAG)
- Tool Calling
- Busca híbrida (BM25 + Vetorial)
- Embeddings semânticos
- Modelo Gemma 12B

## Pipeline RAG

1. Upload do documento
2. Extração textual
3. Chunking com overlap
4. Geração de embeddings
5. Indexação vetorial FAISS
6. Recuperação híbrida
7. Resposta contextualizada pela LLM

---

# Dataset

O dataset utilizado pelo sistema foi construído utilizando:

- Artigos científicos públicos
- Documentações técnicas
- Materiais acadêmicos
- Resumos produzidos pelo grupo

Os documentos foram selecionados por relevância aos temas:

- Inteligência Artificial
- RAG
- Embeddings
- Busca vetorial
- Engenharia de Software
- Arquitetura Backend
- Machine Learning
- Recuperação de Informação

## Estrutura do Dataset

```txt
data/
├── papers/
├── docs/
├── summaries/
└── README.md
```

## Estratégia de Chunking

O sistema utiliza Janela Deslizante (Sliding Window):

- `chunk_size`: 800 caracteres
- `overlap`: 150 caracteres

## Impacto no RAG

O overlap reduz perda de contexto entre chunks consecutivos e melhora o recall da busca híbrida.

O tamanho de chunk escolhido mantém conceitos completos dentro de um único vetor sem gerar excesso de contexto irrelevante.

---

# Pré-requisitos

- Docker
- Docker Compose
- Python 3.11+
- Arquivo `.env`

Exemplo:

```env
APP_NAME=
APP_ENV=
DEBUG=
POSTGRES_DB=
POSTGRES_USER=
POSTGRES_PASSWORD=
POSTGRES_HOST=
POSTGRES_PORT=
DATABASE_URL=
GEMMA_BASE_URL=
GEMMA_MODEL=
GEMMA_API_KEY=
UPLOAD_DIR=
TIMEZONE=
USE_LOCAL_DATASET=
LOCAL_DATASET_PATH=
```

---

# Executando com Docker

Suba os containers:

```bash
docker compose up --build
```

A aplicação ficará disponível em:

- Swagger UI: http://localhost:8000/docs
- Health Check: http://localhost:8000/health
- Nginx: http://localhost:8080

---

# Banco de Dados

Os scripts SQL ficam em:

```txt
database/init/
```

Scripts:

- `001_create_materials.sql`
- `002_create_agenda.sql`
- `003_create_tasks.sql`
- `004_update_timestamps_timezone.sql`

---

# Execução Local

Instalar dependências:

```bash
pip install -r requirements.txt
```

Executar:

```bash
uvicorn app.main:app --reload
```

---

# Testes

Executar todos os testes:

```bash
pytest
```

Executar apenas unitários:

```bash
pytest tests/unit
```

Executar integração:

```bash
pytest tests/integration
```

---

# Endpoints Principais

## Materiais

- `POST /materials/upload`
- `GET /materials`
- `POST /materials/{material_id}/index`
- `POST /materials/ask`

## Agenda

- `POST /agenda`
- `GET /agenda`
- `GET /agenda/today`
- `GET /agenda/week`
- `POST /agenda/ask`

## Tarefas

- `POST /tasks`
- `GET /tasks`
- `PATCH /tasks/{task_id}/complete`

## Assistente IA

- `POST /jarvis/ask`

---

# Dataset Local Para Demonstrações

O RAG pode operar sobre documentos locais fixos, sem upload via API. Para isso, coloque arquivos `.pdf`, `.txt` ou `.md` em:

```txt
data/
├── papers/
├── docs/
└── summaries/
```

Ative no `.env`:

```env
USE_LOCAL_DATASET=true
LOCAL_DATASET_PATH=data
```

Com essa configuração, `POST /materials/ask` usa exclusivamente os documentos locais. Para voltar ao fluxo normal de upload e banco:

```env
USE_LOCAL_DATASET=false
```

---

# Observações Técnicas

- Todos os timestamps são armazenados em UTC.
- Datas sem timezone são assumidas como `America/Campo_Grande`.
- Operações pesadas de CPU utilizam `asyncio.to_thread`.
- O backend utiliza SQLAlchemy assíncrono com `AsyncSession`.
- O sistema possui logs estruturados via Loguru.

---

# Inteligências Artificiais Utilizadas

Durante o desenvolvimento do projeto, foram utilizadas ferramentas de IA generativa como apoio para:

- Revisão de código
- Sugestões de arquitetura
- Identificação de bugs
- Geração de documentação
- Refatoração e melhorias

Ferramentas utilizadas:

- ChatGPT
- Codex
- Gemini
- Claude

Todas as implementações foram revisadas, adaptadas e compreendidas pelo grupo.

---

# Objetivo Acadêmico

O projeto foi desenvolvido para a disciplina de Inteligência Artificial do curso de Engenharia de Software da UFMS.

Além da implementação funcional, o foco do trabalho é demonstrar:

- compreensão sobre RAG
- integração com LLMs
- Tool Calling
- recuperação de informação
- arquitetura backend moderna
- boas práticas de engenharia de software

---

# Licença

Projeto acadêmico desenvolvido para fins educacionais.
