# Dataset Local do JARVIS Acadêmico

Este diretório contém o dataset acadêmico local utilizado pelo módulo RAG do projeto JARVIS Acadêmico API. O objetivo do dataset é permitir demonstrações, avaliações e testes rápidos sem depender do fluxo de upload de materiais pela API.

Quando o modo local está ativado, o endpoint `/materials/ask` consulta os documentos presentes nesta pasta e utiliza o mesmo pipeline do RAG: leitura de documentos, extração de texto, chunking, recuperação BM25/dense/híbrida e geração de resposta com base no contexto recuperado.

## Origem dos Dados

Os documentos foram produzidos pelo grupo como textos acadêmicos autorais, com apoio de ferramentas de IA generativa para revisão, organização e padronização da escrita.

O conteúdo foi baseado em conceitos estudados na disciplina de Inteligência Artificial e em fundamentos gerais de Engenharia de Software, Recuperação de Informação, Machine Learning e Arquitetura Backend.

Não foram adicionadas citações formais nem referências bibliográficas inventadas. Os textos têm finalidade didática e servem como base controlada para demonstração do RAG.

## Tipo de Conteúdo

O dataset contém documentos em Markdown sobre:

- Retrieval-Augmented Generation;
- embeddings e representação semântica;
- busca vetorial com FAISS;
- BM25 e busca léxica;
- Tool Calling em modelos de linguagem;
- arquitetura backend modular;
- FastAPI e programação assíncrona;
- PostgreSQL com SQLAlchemy assíncrono;
- classificação em Machine Learning;
- avaliação de sistemas RAG e análise de erros.

Os textos foram escritos com linguagem acadêmica clara, priorizando explicações conceituais, relação com o projeto JARVIS Acadêmico, exemplos de aplicação e limitações técnicas.

## Estrutura das Pastas

```txt
data/
├── README.md
├── papers/
├── docs/
└── summaries/
```

- `papers/`: reservado para artigos e PDFs acadêmicos usados em demonstrações futuras.
- `docs/`: contém os documentos Markdown principais do dataset atual.
- `summaries/`: reservado para resumos, sínteses e anotações futuras.

## Documentos do Dataset

Os 10 documentos principais ficam em `data/docs/`:

1. `01_rag_fundamentos.md`
2. `02_embeddings_representacao_semantica.md`
3. `03_busca_vetorial_faiss.md`
4. `04_bm25_busca_lexica.md`
5. `05_tool_calling_llms.md`
6. `06_arquitetura_backend_modular.md`
7. `07_fastapi_programacao_assincrona.md`
8. `08_postgresql_sqlalchemy_async.md`
9. `09_classificacao_machine_learning.md`
10. `10_avaliacao_rag_analise_erros.md`

## Estratégia de Chunking

O loader local reutiliza a estratégia de chunking do módulo RAG:

```txt
chunk_size = 800 caracteres
overlap = 150 caracteres
```

O `chunk_size` define o tamanho aproximado de cada trecho enviado para recuperação. O `overlap` cria uma pequena sobreposição entre chunks consecutivos, reduzindo o risco de separar uma ideia importante exatamente na fronteira entre dois trechos.

## Impacto do Chunking no RAG

O chunking influencia diretamente a qualidade da recuperação. Chunks muito grandes podem misturar assuntos diferentes e dificultar a seleção precisa do contexto. Chunks muito pequenos podem perder explicações completas e obrigar o modelo a responder com contexto fragmentado.

No JARVIS Acadêmico, o tamanho de 800 caracteres busca equilibrar contexto suficiente e precisão. A sobreposição de 150 caracteres ajuda a preservar continuidade sem duplicar conteúdo em excesso. Essa estratégia é adequada para textos didáticos médios, como os documentos deste dataset.

## Limitações

- O dataset é pequeno e foi criado para demonstração acadêmica, não para representar uma base de conhecimento completa.
- Os textos são autorais e sintéticos, portanto não substituem livros, artigos científicos ou documentação oficial.
- Alguns conceitos são explicados em nível introdutório a intermediário.
- A qualidade da resposta do RAG ainda depende da pergunta, do método de recuperação, do chunking, do modelo de embeddings e da LLM utilizada.
- O dataset local não é persistido no PostgreSQL; ele é carregado a partir dos arquivos locais.

## Como Ativar o Dataset Local

No arquivo `.env`, configure:

```env
USE_LOCAL_DATASET=true
LOCAL_DATASET_PATH=data
```

Com essa configuração, o endpoint `/materials/ask` usa exclusivamente os arquivos locais do dataset. Para voltar ao fluxo normal de upload e banco:

```env
USE_LOCAL_DATASET=false
```

## Exemplos de Perguntas Para Avaliação

- O que é RAG e como ele reduz alucinações?
- Qual a diferença entre busca vetorial e BM25?
- Como o FAISS ajuda em um sistema RAG?
- O que são embeddings?
- O que é Tool Calling?
- Por que separar backend em routes, services e repositories?
- Como o PostgreSQL é usado no projeto?
- O que é classificação em Machine Learning?
- Como avaliar se uma resposta do RAG está correta?
- Quais erros podem ocorrer em um sistema RAG?

## Uso Esperado na Apresentação

Durante a apresentação, recomenda-se ativar `USE_LOCAL_DATASET=true`, iniciar a API e realizar perguntas pelo endpoint `/materials/ask` ou pelo orquestrador `/jarvis/ask`. O dataset foi estruturado para permitir perguntas conceituais sobre IA, RAG, backend e arquitetura do próprio projeto.
