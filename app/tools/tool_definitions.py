JARVIS_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "consultar_agenda",
            "description": "Consulta eventos e ocorrências da agenda acadêmica.",
            "parameters": {
                "type": "object",
                "properties": {
                    "start_date": {
                        "type": "string",
                        "format": "date",
                        "description": "Data inicial no formato YYYY-MM-DD.",
                    },
                    "end_date": {
                        "type": "string",
                        "format": "date",
                        "description": "Data final no formato YYYY-MM-DD.",
                    },
                    "event_type": {
                        "type": "string",
                        "enum": [
                            "class",
                            "exam",
                            "meeting",
                            "assignment",
                            "activity",
                            "other",
                        ],
                        "description": "Tipo de evento para filtrar a agenda.",
                    },
                    "subject": {
                        "type": "string",
                        "description": "Disciplina ou assunto para filtrar a agenda.",
                    },
                },
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "listar_tarefas",
            "description": "Lista tarefas acadêmicas cadastradas.",
            "parameters": {
                "type": "object",
                "properties": {
                    "status": {
                        "type": "string",
                        "enum": ["pending", "completed"],
                        "description": "Status opcional para filtrar tarefas.",
                    },
                    "priority": {
                        "type": "string",
                        "enum": ["low", "medium", "high"],
                        "description": "Prioridade opcional para filtrar tarefas.",
                    },
                    "subject": {
                        "type": "string",
                        "description": "Disciplina ou assunto para filtrar tarefas.",
                    },
                },
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "adicionar_tarefa",
            "description": "Cria uma nova tarefa acadêmica.",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "Título da tarefa.",
                    },
                    "description": {
                        "type": "string",
                        "description": "Descrição opcional da tarefa.",
                    },
                    "subject": {
                        "type": "string",
                        "description": "Disciplina ou assunto relacionado.",
                    },
                    "priority": {
                        "type": "string",
                        "enum": ["low", "medium", "high"],
                        "description": "Prioridade da tarefa.",
                    },
                    "due_date": {
                        "type": "string",
                        "format": "date-time",
                        "description": "Prazo opcional em formato ISO 8601.",
                    },
                },
                "required": ["title"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "concluir_tarefa",
            "description": "Marca uma tarefa existente como concluída.",
            "parameters": {
                "type": "object",
                "properties": {
                    "task_id": {
                        "type": "integer",
                        "description": "Identificador da tarefa a concluir.",
                    },
                },
                "required": ["task_id"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "buscar_material_rag",
            "description": "Busca respostas em materiais indexados usando recuperação RAG híbrida.",
            "parameters": {
                "type": "object",
                "properties": {
                    "question": {
                        "type": "string",
                        "description": "Pergunta sobre os materiais acadêmicos.",
                    },
                    "material_id": {
                        "type": "integer",
                        "description": "Material específico. Quando omitido, consulta todos os indexados.",
                    },
                    "method": {
                        "type": "string",
                        "enum": ["bm25", "dense", "hybrid"],
                        "description": "Método de recuperação.",
                    },
                    "k": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 10,
                        "description": "Quantidade máxima de chunks recuperados.",
                    },
                    "alpha": {
                        "type": "number",
                        "minimum": 0,
                        "maximum": 1,
                        "description": "Peso do score dense no método hybrid.",
                    },
                    "min_score": {
                        "type": "number",
                        "minimum": 0,
                        "maximum": 1,
                        "description": "Score mínimo para considerar contexto útil.",
                    },
                },
                "required": ["question"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "gerar_plano_estudos",
            "description": (
                "Gera um plano de estudos combinando agenda acadêmica, tarefas pendentes "
                "e materiais recuperados por RAG."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "objective": {
                        "type": "string",
                        "description": "Objetivo do plano de estudos.",
                    },
                    "target_date": {
                        "type": "string",
                        "format": "date",
                        "description": "Data alvo opcional no formato YYYY-MM-DD.",
                    },
                    "available_minutes": {
                        "type": "integer",
                        "minimum": 15,
                        "maximum": 720,
                        "description": "Tempo disponível para estudar, em minutos.",
                    },
                    "material_query": {
                        "type": "string",
                        "description": "Consulta opcional para recuperar materiais via RAG.",
                    },
                },
                "required": ["objective"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "gerar_exercicios",
            "description": "Gera exercícios a partir de materiais recuperados por RAG.",
            "parameters": {
                "type": "object",
                "properties": {
                    "topic": {
                        "type": "string",
                        "description": "Tema dos exercícios.",
                    },
                    "quantity": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 10,
                        "description": "Quantidade de exercícios.",
                    },
                    "level": {
                        "type": "string",
                        "enum": ["facil", "medio", "dificil"],
                        "description": "Nível de dificuldade.",
                    },
                },
                "required": ["topic"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "iniciar_active_recall",
            "description": "Gera uma pergunta interativa de active recall baseada em materiais RAG.",
            "parameters": {
                "type": "object",
                "properties": {
                    "topic": {
                        "type": "string",
                        "description": "Tema da pergunta.",
                    },
                    "level": {
                        "type": "string",
                        "enum": ["facil", "medio", "dificil"],
                        "description": "Nível de dificuldade.",
                    },
                },
                "required": ["topic"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "avaliar_resposta_active_recall",
            "description": "Avalia a resposta do estudante para uma pergunta de active recall.",
            "parameters": {
                "type": "object",
                "properties": {
                    "question_id": {
                        "type": "integer",
                        "description": "Identificador retornado pela ferramenta iniciar_active_recall.",
                    },
                    "user_answer": {
                        "type": "string",
                        "description": "Resposta do estudante.",
                    },
                },
                "required": ["question_id", "user_answer"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "recomendar_revisao",
            "description": "Recomenda temas para revisão com base em tentativas ruins de active recall.",
            "parameters": {
                "type": "object",
                "properties": {},
                "additionalProperties": False,
            },
        },
    },
]
