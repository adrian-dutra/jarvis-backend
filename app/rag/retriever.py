import re
from dataclasses import dataclass

import numpy as np

from app.rag.embeddings import encode_texts


@dataclass
class RetrieverDocument:
    material_id: int
    material_name: str
    chunk_id: int
    chunk_index: int
    text: str


@dataclass
class RetrievedDocument:
    document: RetrieverDocument
    score: float


def tokenize(text: str) -> list[str]:
    return re.findall(r"\w+", text.lower())


def retrieve(
    *,
    question: str,
    documents: list[RetrieverDocument],
    method: str = "hybrid",
    k: int = 5,
    alpha: float = 0.6,
) -> list[RetrievedDocument]:
    if not documents:
        return []

    if method == "bm25":
        return retrieve_bm25(question=question, documents=documents, k=k)
    if method == "dense":
        return retrieve_dense(question=question, documents=documents, k=k)
    if method == "hybrid":
        return retrieve_hybrid(question=question, documents=documents, k=k, alpha=alpha)

    raise ValueError("Método de recuperação inválido")


def retrieve_bm25(
    *,
    question: str,
    documents: list[RetrieverDocument],
    k: int,
) -> list[RetrievedDocument]:
    from rank_bm25 import BM25Okapi

    corpus = [tokenize(document.text) for document in documents]
    bm25 = BM25Okapi(corpus)
    scores = bm25.get_scores(tokenize(question))
    return _top_k(documents, scores, k)


def retrieve_dense(
    *,
    question: str,
    documents: list[RetrieverDocument],
    k: int,
) -> list[RetrievedDocument]:
    import faiss

    texts = [document.text for document in documents]
    matrix = encode_texts(texts)
    query = encode_texts([question])

    index = faiss.IndexFlatIP(matrix.shape[1])
    index.add(matrix)
    scores, indexes = index.search(query, min(k, len(documents)))

    results: list[RetrievedDocument] = []
    for position, document_index in enumerate(indexes[0]):
        if document_index < 0:
            continue
        results.append(
            RetrievedDocument(
                document=documents[int(document_index)],
                score=float(scores[0][position]),
            )
        )
    return results


def retrieve_hybrid(
    *,
    question: str,
    documents: list[RetrieverDocument],
    k: int,
    alpha: float,
) -> list[RetrievedDocument]:
    from rank_bm25 import BM25Okapi

    texts = [document.text for document in documents]
    corpus = [tokenize(text) for text in texts]

    bm25 = BM25Okapi(corpus)
    bm25_scores = np.asarray(bm25.get_scores(tokenize(question)), dtype="float32")

    matrix = encode_texts(texts)
    query = encode_texts([question])[0]
    dense_scores = np.dot(matrix, query)

    normalized_bm25 = _normalize_scores(bm25_scores)
    normalized_dense = _normalize_scores(dense_scores)
    final_scores = alpha * normalized_dense + (1.0 - alpha) * normalized_bm25

    return _top_k(documents, final_scores, k)


def _normalize_scores(scores: np.ndarray) -> np.ndarray:
    if scores.size == 0:
        return scores

    min_score = float(np.min(scores))
    max_score = float(np.max(scores))
    if max_score == min_score:
        if max_score > 0:
            return np.ones_like(scores, dtype="float32")
        return np.zeros_like(scores, dtype="float32")

    return ((scores - min_score) / (max_score - min_score)).astype("float32")


def _top_k(
    documents: list[RetrieverDocument],
    scores: np.ndarray,
    k: int,
) -> list[RetrievedDocument]:
    if len(documents) == 0:
        return []

    limit = min(k, len(documents))
    indexes = np.argsort(scores)[::-1][:limit]

    return [
        RetrievedDocument(
            document=documents[int(index)],
            score=float(scores[int(index)]),
        )
        for index in indexes
    ]
