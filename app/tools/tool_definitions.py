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
]
