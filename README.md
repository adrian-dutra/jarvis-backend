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

- Planejamento de estudos
  - Combina agenda acadêmica, tarefas pendentes e materiais recuperados por RAG
  - Gera prioridades justificadas
  - Organiza o estudo em blocos com tempo sugerido
  - Indica a próxima ação recomendada

- Aprendizado
  - Geração de exercícios a partir dos materiais
  - Active recall interativo com pergunta e avaliação da resposta
  - Recomendação de revisão baseada em dificuldades identificadas

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

# Funcionalidade 3.4: Planejamento de Estudos

O planejamento de estudos usa a rota `POST /study-plan` para gerar um plano objetivo a partir de três fontes do sistema:

1. Agenda acadêmica: eventos entre a data atual e a data alvo informada.
2. Tarefas pendentes: atividades ainda não concluídas.
3. Materiais RAG: trechos recuperados por busca híbrida usando `material_query` ou o próprio objetivo.

Quando alguma fonte não possui dados, o endpoint continua retornando `200 OK` e inclui avisos no campo `warnings`.

## Endpoint

```http
POST /study-plan
```

Request:

```json
{
  "objective": "Montar um plano de estudos para a prova de IA",
  "target_date": "2026-06-20",
  "available_minutes": 120,
  "material_query": "RAG, embeddings, FAISS, BM25"
}
```

Response resumida:

```json
{
  "objective": "Montar um plano de estudos para a prova de IA",
  "priorities": [
    {
      "title": "Revisar RAG híbrido",
      "level": "high",
      "justification": "Tema recorrente nos materiais recuperados e relacionado à prova.",
      "related_sources": ["material:ia.pdf#chunk-1"]
    }
  ],
  "agenda_considered": [
    {
      "source_type": "agenda",
      "reference": "agenda:1",
      "title": "Prova de IA",
      "summary": "exam disciplina=IA em 2026-06-20 08:00:00."
    }
  ],
  "tasks_considered": [],
  "materials_considered": [
    {
      "source_type": "material",
      "reference": "material:ia.pdf#chunk-1",
      "title": "ia.pdf",
      "summary": "Trecho recuperado sobre RAG, embeddings e FAISS."
    }
  ],
  "study_blocks": [
    {
      "order": 1,
      "duration_minutes": 60,
      "focus": "RAG e embeddings",
      "activity": "Revisar conceitos e produzir um resumo curto.",
      "related_sources": ["material:ia.pdf#chunk-1"],
      "justification": "Ataca o tema mais relevante para o objetivo."
    }
  ],
  "next_action": "Comece pelo primeiro bloco e anote dúvidas.",
  "warnings": ["Nenhuma tarefa pendente encontrada."],
  "llm_summary": "Plano gerado com base na agenda e nos materiais recuperados."
}
```

O agente JARVIS também possui a ferramenta `gerar_plano_estudos`. A decisão de usá-la continua sendo feita pela LLM no endpoint `/jarvis/ask`, sem regras fixas por palavra-chave.

---

# Melhorias de Aprendizado

O módulo de aprendizado implementa as funcionalidades acadêmicas obrigatórias voltadas ao estudo ativo. A funcionalidade interativa é o active recall: o sistema pergunta algo ao estudante, recebe a resposta e avalia como `correta`, `parcialmente_correta` ou `incorreta`.

As dificuldades são identificadas a partir das tentativas salvas em `learning_attempts`. Respostas incorretas ou parcialmente corretas são agrupadas por tema e usadas para recomendar revisão.

## Gerar exercícios

```http
POST /learning/exercises
```

Request:

```json
{
  "topic": "RAG e embeddings",
  "quantity": 5,
  "level": "medio"
}
```

Response resumida:

```json
{
  "topic": "RAG e embeddings",
  "level": "medio",
  "exercises": [
    {
      "question": "Explique como embeddings ajudam na recuperação semântica.",
      "exercise_type": "discursiva",
      "expected_answer": "Embeddings representam textos como vetores para comparar similaridade semântica."
    }
  ],
  "sources": [
    {
      "material_id": 1,
      "material_name": "rag.pdf",
      "chunk_id": 10,
      "chunk_index": 2,
      "score": 0.91,
      "text": "Trecho recuperado sobre RAG e embeddings."
    }
  ]
}
```

## Active recall

Iniciar pergunta:

```http
POST /learning/active-recall/start
```

```json
{
  "topic": "RAG e embeddings",
  "level": "medio"
}
```

Resposta:

```json
{
  "question_id": 1,
  "topic": "RAG e embeddings",
  "level": "medio",
  "question": "Como o RAG usa informações externas para melhorar uma resposta?",
  "sources": []
}
```

Avaliar resposta:

```http
POST /learning/active-recall/answer
```

```json
{
  "question_id": 1,
  "user_answer": "O RAG recupera documentos externos e usa esse contexto antes de gerar a resposta."
}
```

Response resumida:

```json
{
  "question_id": 1,
  "classification": "correta",
  "score": 0.95,
  "feedback": "Boa resposta, você explicou a recuperação e o uso do contexto.",
  "expected_answer_summary": "RAG recupera informações externas relevantes e usa esse contexto na geração.",
  "strengths": ["Mencionou recuperação externa", "Relacionou contexto e geração"],
  "improvements": ["Citar exemplos de fontes externas"],
  "review_recommendation": "Revise exemplos práticos de pipelines RAG."
}
```

## Recomendações de revisão

```http
GET /learning/review-recommendations
```

Response resumida:

```json
{
  "recommendations": [
    {
      "topic": "RAG e embeddings",
      "priority": "alta",
      "reason": "O tema teve 2 tentativa(s) com dificuldade, média 0.35, 2 incorreta(s) e 0 parcialmente correta(s).",
      "attempts_count": 2,
      "average_score": 0.35
    }
  ],
  "generated_at": "2026-06-14T12:00:00"
}
```

O agente JARVIS também pode chamar as ferramentas `gerar_exercicios`, `iniciar_active_recall`, `avaliar_resposta_active_recall` e `recomendar_revisao` por Tool Calling.

---

# Conversas no JARVIS

O endpoint `POST /jarvis/ask` mantém um histórico simples em memória usando `conversation_id`. Isso permite testar conversas em sequência no Swagger ou Postman sem precisar reenviar todo o histórico manualmente.

Exemplo:

```json
{
  "conversation_id": "teste-rag",
  "message": "Crie uma pergunta sobre RAG."
}
```

Na próxima chamada, use o mesmo `conversation_id`:

```json
{
  "conversation_id": "teste-rag",
  "message": "A resposta é recuperação de documentos."
}
```

A API registra nos logs a pergunta atual, as mensagens anteriores carregadas e a resposta final do assistente. O histórico é mantido apenas em memória, então é perdido ao reiniciar a aplicação.

---

# Pré-requisitos

- Docker
- Docker Compose
- Python 3.11+
- Arquivo `.env`

Exemplo:

```env
APP_NAME=JARVIS Acadêmico API
APP_ENV=development
DEBUG=true

POSTGRES_DB=jarvis_db
POSTGRES_USER=jarvis
POSTGRES_PASSWORD=jarvis123
POSTGRES_HOST=db
POSTGRES_PORT=5432

DATABASE_URL=postgresql://jarvis:jarvis123@db:5432/jarvis_db

GEMMA_BASE_URL=https://seu-endpoint-gemma/v1
GEMMA_MODEL=google/gemma-3-12b-it
GEMMA_API_KEY=sua_chave

UPLOAD_DIR=uploads
TIMEZONE=America/Campo_Grande
USE_LOCAL_DATASET=false
LOCAL_DATASET_PATH=data
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
