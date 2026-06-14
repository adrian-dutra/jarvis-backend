# Guia de Testes das Funcionalidades Implementadas

Este documento resume as funcionalidades adicionadas ao JARVIS Acadêmico e mostra testes práticos para validar tudo antes da apresentação.

## 1. O Que Foi Implementado

### Planejamento de estudos

Endpoint:

```http
POST /study-plan
```

O sistema combina:

- agenda acadêmica;
- tarefas pendentes;
- materiais recuperados via RAG;
- Gemma 12B para organizar o plano final.

Resposta esperada:

- objetivo;
- prioridades;
- agenda considerada;
- tarefas consideradas;
- materiais recuperados;
- blocos de estudo;
- justificativas;
- próxima ação recomendada;
- avisos quando alguma fonte estiver vazia.

### Memória de conversa no JARVIS

Endpoint:

```http
POST /jarvis/ask
```

Foi adicionado `conversation_id`. Chamadas com o mesmo ID reutilizam o histórico em memória.

Isso permite testar conversas como:

1. JARVIS faz uma pergunta.
2. Usuário responde.
3. JARVIS avalia a resposta considerando o histórico anterior.

Observação: essa memória é em RAM e zera quando a API reinicia.

### Melhorias de aprendizado

Endpoints:

```http
POST /learning/exercises
POST /learning/active-recall/start
POST /learning/active-recall/answer
GET /learning/review-recommendations
```

Funcionalidades:

- geração de exercícios a partir dos materiais recuperados via RAG;
- active recall interativo;
- avaliação da resposta do estudante;
- classificação como `correta`, `parcialmente_correta` ou `incorreta`;
- feedback objetivo;
- identificação de pontos fortes e pontos a melhorar;
- recomendação de revisão baseada nas tentativas salvas.

### Tool Calling

Novas ferramentas disponíveis para o agente:

```txt
gerar_plano_estudos
gerar_exercicios
iniciar_active_recall
avaliar_resposta_active_recall
recomendar_revisao
```

A decisão de chamar ferramentas continua sendo feita pela LLM, sem `if` fixo por palavra-chave na rota.

## 2. Preparação Do Ambiente

Subir a aplicação:

```bash
docker compose up --build
```

Ou localmente:

```bash
uvicorn app.main:app --reload
```

Acessar documentação interativa:

```txt
http://localhost:8000/docs
```

Health check:

```bash
curl http://localhost:8000/health
```

Resposta esperada:

```json
{
  "status": "ok"
}
```

## 3. Banco De Dados

Foi adicionada a tabela:

```txt
learning_attempts
```

Script:

```txt
database/init/005_create_learning_attempts.sql
```

Se o banco já existia antes dessa alteração, aplique o script manualmente:

```bash
docker compose exec db psql -U jarvis -d jarvis_db -f /docker-entrypoint-initdb.d/005_create_learning_attempts.sql
```

Se recriar o banco do zero, os scripts em `database/init/` serão aplicados automaticamente pelo PostgreSQL no primeiro start do container.

## 4. Fluxo Recomendado Para Testar Tudo

### 4.1 Enviar e indexar um material

No Swagger:

```http
POST /materials/upload
POST /materials/{material_id}/index
```

Depois teste o RAG:

```http
POST /materials/ask
```

Payload:

```json
{
  "question": "Explique RAG e embeddings",
  "method": "hybrid",
  "k": 5,
  "alpha": 0.6,
  "min_score": 0.15
}
```

Você deve receber uma resposta com `sources`.

### 4.2 Criar eventos de agenda

Endpoint:

```http
POST /agenda
```

Payload:

```json
{
  "title": "Prova de Inteligência Artificial",
  "description": "Avaliação sobre RAG, embeddings, FAISS e BM25.",
  "event_type": "exam",
  "subject": "Inteligência Artificial",
  "location": "Sala 12",
  "start_at": "2026-06-20T08:00:00",
  "end_at": "2026-06-20T10:00:00",
  "all_day": false,
  "recurrence_type": "none"
}
```

### 4.3 Criar tarefas pendentes

Endpoint:

```http
POST /tasks
```

Payload:

```json
{
  "title": "Estudar RAG híbrido",
  "description": "Revisar embeddings, FAISS, BM25 e recuperação híbrida.",
  "subject": "Inteligência Artificial",
  "priority": "high",
  "due_date": "2026-06-19T20:00:00"
}
```

## 5. Testar Planejamento De Estudos

Endpoint:

```http
POST /study-plan
```

Payload:

```json
{
  "objective": "Montar um plano de estudos para a prova de IA",
  "target_date": "2026-06-20",
  "available_minutes": 120,
  "material_query": "RAG, embeddings, FAISS, BM25"
}
```

Verifique se a resposta contém:

- `priorities`;
- `agenda_considered`;
- `tasks_considered`;
- `materials_considered`;
- `study_blocks`;
- `next_action`;
- `warnings`.

Mesmo que alguma fonte esteja vazia, o endpoint deve retornar `200 OK` com aviso em `warnings`.

## 6. Testar Memória No JARVIS

Endpoint:

```http
POST /jarvis/ask
```

Primeira chamada:

```json
{
  "conversation_id": "teste-rag",
  "message": "Quero estudar RAG. Me faça uma pergunta."
}
```

Segunda chamada, usando o mesmo `conversation_id`:

```json
{
  "conversation_id": "teste-rag",
  "message": "RAG é uma técnica que recupera informações externas antes de gerar uma resposta."
}
```

Resultado esperado:

- o JARVIS deve considerar a pergunta anterior;
- deve avaliar sua resposta;
- deve continuar a conversa de forma coerente.

Logs esperados:

```txt
jarvis conversa pergunta conversation_id=teste-rag history_messages=...
jarvis conversa historico conversation_id=teste-rag ...
jarvis conversa resposta conversation_id=teste-rag answer=...
```

## 7. Testar Geração De Exercícios

Endpoint:

```http
POST /learning/exercises
```

Payload:

```json
{
  "topic": "RAG e embeddings",
  "quantity": 5,
  "level": "medio"
}
```

Verifique se a resposta contém:

- `topic`;
- `level`;
- `exercises`;
- `question`;
- `exercise_type`;
- `expected_answer`;
- `sources`.

Se não houver material recuperado, o endpoint deve retornar:

```txt
404 Nenhum material relevante foi encontrado para o tema informado.
```

## 8. Testar Active Recall

### 8.1 Iniciar pergunta

Endpoint:

```http
POST /learning/active-recall/start
```

Payload:

```json
{
  "topic": "RAG e embeddings",
  "level": "medio"
}
```

Verifique se a resposta contém:

- `question_id`;
- `topic`;
- `level`;
- `question`;
- `sources`.

Guarde o `question_id`.

### 8.2 Responder pergunta

Endpoint:

```http
POST /learning/active-recall/answer
```

Payload:

```json
{
  "question_id": 1,
  "user_answer": "RAG recupera documentos externos relevantes e usa esses documentos como contexto para a LLM gerar uma resposta mais precisa."
}
```

Verifique se a resposta contém:

- `classification`;
- `score`;
- `feedback`;
- `expected_answer_summary`;
- `strengths`;
- `improvements`;
- `review_recommendation`.

Classificações possíveis:

```txt
correta
parcialmente_correta
incorreta
```

## 9. Testar Recomendações De Revisão

Para gerar recomendações, faça algumas tentativas de active recall com respostas incompletas ou erradas.

Depois chame:

```http
GET /learning/review-recommendations
```

Resposta esperada:

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

Prioridades:

- `alta`: média baixa ou erros recorrentes;
- `media`: respostas parcialmente corretas ou média intermediária;
- `baixa`: dificuldade leve.

## 10. Testar As Ferramentas Pelo Agente

Endpoint:

```http
POST /jarvis/ask
```

### Gerar plano de estudos

```json
{
  "conversation_id": "teste-tools",
  "message": "Monte um plano de estudos para minha prova de IA sobre RAG e embeddings."
}
```

### Gerar exercícios

```json
{
  "conversation_id": "teste-tools",
  "message": "Gere 3 exercícios de nível médio sobre RAG e embeddings."
}
```

### Iniciar active recall

```json
{
  "conversation_id": "teste-tools",
  "message": "Inicie uma pergunta de active recall sobre RAG."
}
```

### Avaliar active recall

Use o `question_id` retornado pela ferramenta anterior:

```json
{
  "conversation_id": "teste-tools",
  "message": "Avalie minha resposta da pergunta 1: RAG recupera documentos externos e usa como contexto."
}
```

### Recomendar revisão

```json
{
  "conversation_id": "teste-tools",
  "message": "Com base nas minhas dificuldades, recomende o que eu devo revisar."
}
```

Na resposta do `/jarvis/ask`, observe o campo:

```json
"tools_used": []
```

Quando a LLM chamar uma ferramenta, esse campo deve listar o nome da tool executada e os argumentos usados.

## 11. Rodar Testes Automatizados

Rodar todos os testes:

```bash
python -m pytest
```

Rodar apenas unitários:

```bash
python -m pytest tests/unit
```

Rodar apenas testes do módulo de aprendizado:

```bash
python -m pytest tests/unit/test_learning_service.py tests/unit/test_review_service.py tests/unit/test_learning_routes.py
```

Rodar testes do agente:

```bash
python -m pytest tests/unit/test_jarvis_agent.py
```

Compilar o pacote para checar erros de sintaxe/import:

```bash
python -m compileall -q app
```

Resultado atual esperado:

```txt
43 passed, 6 skipped
```

Os testes skipped são integrações que dependem de `TEST_DATABASE_URL`.

## 12. Testes De Integração Com Banco

Para rodar integração, configure um banco de teste separado:

```bash
export TEST_DATABASE_URL="postgresql+asyncpg://usuario:senha@localhost:5432/jarvis_test"
python -m pytest tests/integration
```

Importante: o nome do banco precisa conter `test`, pois o `conftest.py` bloqueia execução contra banco real.

## 13. Checklist De Aceite

Use esta lista antes da entrega:

- `/health` retorna `ok`.
- Material é enviado e indexado.
- `/materials/ask` retorna fontes.
- Agenda tem pelo menos uma prova/evento futuro.
- Tarefas pendentes existem.
- `/study-plan` retorna plano com agenda, tarefas e materiais.
- `/jarvis/ask` mantém histórico com `conversation_id`.
- `/learning/exercises` gera exercícios com fontes.
- `/learning/active-recall/start` gera uma pergunta.
- `/learning/active-recall/answer` avalia a resposta.
- `/learning/review-recommendations` recomenda revisão após tentativas ruins.
- Tool Calling mostra `tools_used` quando a LLM decide chamar uma ferramenta.
- `python -m pytest` passa.

## 14. Como Explicar Na Apresentação

Resumo simples:

```txt
O JARVIS Acadêmico usa RAG para recuperar materiais relevantes, Gemma 12B para gerar respostas e uma arquitetura modular em camadas. 
As funcionalidades de aprendizado incluem geração de exercícios, active recall interativo e recomendações de revisão. 
No active recall, o sistema salva a tentativa, avalia a resposta do estudante e usa erros ou respostas parciais para recomendar temas de revisão.
```

Arquitetura:

```txt
Routes -> Services -> Repositories -> Database
```

Fluxo do active recall:

```txt
1. Usuário escolhe um tema.
2. LearningService busca contexto nos materiais via RAG.
3. Gemma gera uma pergunta e resposta esperada.
4. A pergunta é salva em learning_attempts.
5. Usuário responde.
6. Gemma avalia a resposta.
7. A tentativa é atualizada com classificação, nota e feedback.
8. ReviewService usa tentativas ruins para recomendar revisão.
```
