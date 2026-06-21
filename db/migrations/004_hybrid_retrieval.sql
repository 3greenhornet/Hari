-- 004_hybrid_retrieval.sql
ALTER TABLE memories ADD COLUMN IF NOT EXISTS text_search_vector tsvector;

CREATE OR REPLACE FUNCTION memories_tsvector_trigger() RETURNS trigger AS $$
BEGIN
  NEW.text_search_vector :=
     setweight(to_tsvector('english', COALESCE(NEW.content, '')), 'A') ||
     setweight(to_tsvector('english', COALESCE(NEW.meaning_summary, '')), 'B');
  RETURN NEW;
END
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_memories_tsvector ON memories;
CREATE TRIGGER trg_memories_tsvector
BEFORE INSERT OR UPDATE OF content, meaning_summary ON memories
FOR EACH ROW EXECUTE FUNCTION memories_tsvector_trigger();

CREATE INDEX IF NOT EXISTS idx_memories_tsvector ON memories USING gin(text_search_vector);