/**
 * SQLite Database Schema for Maritime AI
 * 
 * Tables: threads, messages, messages_fts (FTS5 virtual table)
 * All data persists locally — no cloud, no API.
 */

export const CREATE_TABLES_SQL = `
  CREATE TABLE IF NOT EXISTS threads (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL DEFAULT 'New Conversation',
    preview TEXT NOT NULL DEFAULT '',
    pinned INTEGER NOT NULL DEFAULT 0,
    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL
  );

  CREATE TABLE IF NOT EXISTS messages (
    id TEXT PRIMARY KEY,
    thread_id TEXT NOT NULL,
    role TEXT NOT NULL CHECK(role IN ('user', 'assistant', 'system')),
    content TEXT NOT NULL,
    thinking TEXT,
    think_time REAL,
    tokens_used INTEGER,
    created_at INTEGER NOT NULL,
    has_safety INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (thread_id) REFERENCES threads(id) ON DELETE CASCADE
  );

  CREATE INDEX IF NOT EXISTS idx_messages_thread ON messages(thread_id, created_at);
`;

// FTS5 for full-text search — created separately as it may not be available on all platforms
export const CREATE_FTS_SQL = `
  CREATE VIRTUAL TABLE IF NOT EXISTS messages_fts USING fts5(
    content,
    thread_id UNINDEXED,
    content='messages',
    content_rowid='rowid'
  );
`;

export const FTS_TRIGGERS_SQL = `
  CREATE TRIGGER IF NOT EXISTS messages_ai AFTER INSERT ON messages BEGIN
    INSERT INTO messages_fts(rowid, content, thread_id) VALUES (new.rowid, new.content, new.thread_id);
  END;
  
  CREATE TRIGGER IF NOT EXISTS messages_ad AFTER DELETE ON messages BEGIN
    INSERT INTO messages_fts(messages_fts, rowid, content, thread_id) VALUES('delete', old.rowid, old.content, old.thread_id);
  END;
`;
