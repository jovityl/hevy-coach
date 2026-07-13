from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.rag import Finding
from app.interfaces.vector_repo import VectorRepository
from app.repositories.models import ScienceCorpusRow


class CorpusRepository(VectorRepository):
    """pgvector-backed VectorRepository — the default binding. Cosine search at
    300-600 rows is an exact scan (no ANN index needed at this scale, §5)."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, finding: Finding, abstract_text: str, embedding: list[float]) -> None:
        self._session.add(
            ScienceCorpusRow(
                pubmed_id=finding.pubmed_id,
                title=finding.title,
                finding_text=finding.finding_text,
                abstract_text=abstract_text,
                topic_tags=finding.topic_tags,
                citation=finding.citation,
                source_url=finding.source_url,
                embedding=embedding,
            )
        )

    async def commit(self) -> None:
        await self._session.commit()

    async def search(self, embedding: list[float], k: int) -> list[Finding]:
        stmt = (
            select(ScienceCorpusRow)
            .order_by(ScienceCorpusRow.embedding.cosine_distance(embedding))
            .limit(k)
        )
        result = await self._session.execute(stmt)
        return [self._to_finding(row) for row in result.scalars().all()]

    @staticmethod
    def _to_finding(row: ScienceCorpusRow) -> Finding:
        return Finding(
            pubmed_id=row.pubmed_id,
            title=row.title,
            finding_text=row.finding_text,
            citation=row.citation,
            source_url=row.source_url,
            topic_tags=row.topic_tags,
        )
