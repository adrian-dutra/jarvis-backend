from app.rag.rag_service import NOT_FOUND_ANSWER, RagService, build_prompt
from app.rag.retriever import RetrievedDocument, RetrieverDocument


def test_build_prompt_inclui_instrucao_contexto_e_pergunta():
    document = RetrieverDocument(
        material_id=1,
        material_name="aula.txt",
        chunk_id=10,
        chunk_index=3,
        text="Regressão logística é usada para classificação.",
    )
    retrieved = RetrievedDocument(document=document, score=0.9)

    prompt = build_prompt("Explique regressão logística", [retrieved])

    assert "Responda em português usando apenas o contexto abaixo." in prompt
    assert "não encontrado no contexto" in prompt
    assert "material=aula.txt" in prompt
    assert "chunk=3" in prompt
    assert "Pergunta: Explique regressão logística" in prompt


def test_answer_retorna_not_found_sem_contexto_util(mock_gemma_client):
    service = RagService()

    answer = service.answer(
        question="Explique regressão logística",
        retrieved_documents=[],
        min_score=0.15,
    )

    assert answer == NOT_FOUND_ANSWER
    mock_gemma_client.assert_not_called()


def test_answer_retorna_not_found_quando_score_for_baixo(mock_gemma_client):
    document = RetrieverDocument(
        material_id=1,
        material_name="aula.txt",
        chunk_id=10,
        chunk_index=3,
        text="Texto recuperado.",
    )
    service = RagService()

    answer = service.answer(
        question="Pergunta",
        retrieved_documents=[RetrievedDocument(document=document, score=0.1)],
        min_score=0.15,
    )

    assert answer == NOT_FOUND_ANSWER
    mock_gemma_client.assert_not_called()
