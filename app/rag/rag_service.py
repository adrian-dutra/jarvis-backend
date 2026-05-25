from app.llm.gemma_client import GemmaClient
from app.rag.retriever import RetrievedDocument


NOT_FOUND_ANSWER = "não encontrado no contexto"


class RagService:
    def __init__(self, gemma_client: GemmaClient | None = None):
        self.gemma_client = gemma_client or GemmaClient()

    def answer(
        self,
        *,
        question: str,
        retrieved_documents: list[RetrievedDocument],
        min_score: float,
    ) -> str:
        useful_documents = [
            item for item in retrieved_documents if item.document.text.strip()
        ]

        if not useful_documents:
            return NOT_FOUND_ANSWER

        best_score = max(item.score for item in useful_documents)
        if best_score < min_score:
            return NOT_FOUND_ANSWER

        prompt = build_prompt(question=question, documents=useful_documents)
        answer = self.gemma_client.generate(prompt)
        return answer.strip() or NOT_FOUND_ANSWER


def build_prompt(question: str, documents: list[RetrievedDocument]) -> str:
    context_parts = []
    for position, item in enumerate(documents, start=1):
        context_parts.append(
            f"[Trecho {position} | material={item.document.material_name} | "
            f"chunk={item.document.chunk_index}]\n{item.document.text}"
        )

    context = "\n\n".join(context_parts)
    return (
        "Responda em português usando apenas o contexto abaixo. "
        "Se não houver informação suficiente, responda exatamente: "
        "não encontrado no contexto.\n\n"
        f"Contexto:\n{context}\n\n"
        f"Pergunta: {question}\n"
        "Resposta:"
    )
