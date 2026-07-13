from pydantic import BaseModel


class Finding(BaseModel):
    """A single condensed, cited research finding retrieved from the corpus.
    `abstract_text` is retained so any number in `finding_text` is checkable
    against its source (§6.2)."""

    pubmed_id: str
    title: str
    finding_text: str
    citation: str
    source_url: str
    topic_tags: list[str]
