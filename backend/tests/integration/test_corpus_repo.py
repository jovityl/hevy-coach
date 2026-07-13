import asyncio
import uuid

from sqlalchemy import delete

from app.core.db import async_session_factory
from app.domain.rag import Finding
from app.repositories.corpus_repo import CorpusRepository
from app.repositories.models import EMBEDDING_DIM, ScienceCorpusRow


def _unit_vector(index: int) -> list[float]:
    """A vector that's all zeros except a single 1.0 — so two different unit
    vectors are orthogonal (cosine distance 1) and identical ones match
    exactly (cosine distance 0)."""
    vector = [0.0] * EMBEDDING_DIM
    vector[index] = 1.0
    return vector


def _finding(pubmed_id: str) -> Finding:
    return Finding(
        pubmed_id=pubmed_id,
        title=f"title {pubmed_id}",
        finding_text=f"finding {pubmed_id}",
        citation="Author (2024)",
        source_url="https://pubmed.example/x",
        topic_tags=["hypertrophy"],
    )


async def _search_scenario() -> list[str]:
    tag = uuid.uuid4().hex  # isolates this run's rows in the global corpus table
    async with async_session_factory() as session:
        repo = CorpusRepository(session)
        await repo.add(_finding(f"{tag}-A"), "abstract A", _unit_vector(0))
        await repo.add(_finding(f"{tag}-B"), "abstract B", _unit_vector(1))
        await repo.add(_finding(f"{tag}-C"), "abstract C", _unit_vector(2))
        await repo.commit()

        # Query with B's exact vector -> B should rank first.
        results = await repo.search(_unit_vector(1), k=3)

        await session.execute(
            delete(ScienceCorpusRow).where(ScienceCorpusRow.pubmed_id.like(f"{tag}-%"))
        )
        await session.commit()
    return [f.pubmed_id.rsplit("-", 1)[1] for f in results]


def test_cosine_search_ranks_nearest_first() -> None:
    order = asyncio.run(_search_scenario())

    assert order[0] == "B"  # exact match to the query vector
    assert set(order) == {"A", "B", "C"}
