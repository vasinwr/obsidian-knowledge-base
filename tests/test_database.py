"""Tests for the SQLite database store."""

from kb.database import Database
from kb.models import Document, ReadStatus, SourceType


class TestDatabase:
    def test_upsert_and_get(self, db: Database, sample_document: Document):
        db.upsert_document(sample_document)
        retrieved = db.get_document(sample_document.id)
        assert retrieved is not None
        assert retrieved.title == sample_document.title
        assert retrieved.source_url == sample_document.source_url
        assert retrieved.content == sample_document.content
        assert retrieved.summary == sample_document.summary
        assert set(retrieved.keywords) == set(sample_document.keywords)

    def test_get_nonexistent(self, db: Database):
        assert db.get_document("nonexistent") is None

    def test_document_exists(self, db: Database, sample_document: Document):
        assert not db.document_exists(sample_document.id)
        db.upsert_document(sample_document)
        assert db.document_exists(sample_document.id)

    def test_get_by_prefix(self, db: Database, sample_document: Document):
        db.upsert_document(sample_document)
        retrieved = db.get_document("abc123")
        assert retrieved is not None
        assert retrieved.id == sample_document.id

    def test_get_by_title(self, db: Database, sample_document: Document):
        db.upsert_document(sample_document)
        retrieved = db.get_document_by_title("Test Document")
        assert retrieved is not None
        assert retrieved.id == sample_document.id

    def test_find_document(self, db: Database, sample_document: Document):
        db.upsert_document(sample_document)
        # By ID prefix
        assert db.find_document("abc123") is not None
        # By title
        assert db.find_document("Test Document") is not None
        # Not found
        assert db.find_document("zzz") is None

    def test_list_documents(self, db: Database, sample_document: Document):
        db.upsert_document(sample_document)
        docs = db.list_documents()
        assert len(docs) == 1
        assert docs[0].title == sample_document.title

    def test_list_unread(self, db: Database, sample_document: Document):
        db.upsert_document(sample_document)
        assert len(db.list_documents(unread_only=True)) == 1
        db.set_read_status(sample_document.id, ReadStatus.READ)
        assert len(db.list_documents(unread_only=True)) == 0

    def test_list_by_type(self, db: Database, sample_document: Document):
        db.upsert_document(sample_document)
        assert len(db.list_documents(source_type="web")) == 1
        assert len(db.list_documents(source_type="pdf")) == 0

    def test_delete_document(self, db: Database, sample_document: Document):
        db.upsert_document(sample_document)
        assert db.delete_document(sample_document.id)
        assert db.get_document(sample_document.id) is None

    def test_delete_nonexistent(self, db: Database):
        assert not db.delete_document("nonexistent")

    def test_set_read_status(self, db: Database, sample_document: Document):
        db.upsert_document(sample_document)
        assert db.set_read_status(sample_document.id, ReadStatus.READ)
        doc = db.get_document(sample_document.id)
        assert doc.read_status == ReadStatus.READ

    def test_wikilinks(self, db: Database, sample_document: Document):
        # Create two documents
        doc2 = Document(
            id="other_doc_id",
            title="Other Document",
            source_url="https://example.com/other",
            source_type=SourceType.WEB,
            content="Other content",
        )
        db.upsert_document(sample_document)
        db.upsert_document(doc2)

        db.set_wikilinks(sample_document.id, [doc2.id])
        targets = db.get_wikilink_targets(sample_document.id)
        assert targets == [doc2.id]

    def test_keywords(self, db: Database, sample_document: Document):
        db.upsert_document(sample_document)
        doc_ids = db.get_documents_by_keyword("testing")
        assert sample_document.id in doc_ids

    def test_all_keywords(self, db: Database, sample_document: Document):
        db.upsert_document(sample_document)
        keywords = db.get_all_keywords()
        assert "testing" in keywords
        assert "example" in keywords

    def test_stats(self, db: Database, sample_document: Document):
        db.upsert_document(sample_document)
        s = db.stats()
        assert s["total_documents"] == 1
        assert s["unread"] == 1
        assert s["read"] == 0
        assert s["by_type"]["web"] == 1

    def test_upsert_idempotent(self, db: Database, sample_document: Document):
        db.upsert_document(sample_document)
        sample_document.summary = "Updated summary"
        db.upsert_document(sample_document)
        docs = db.list_documents()
        assert len(docs) == 1
        assert docs[0].summary == "Updated summary"
