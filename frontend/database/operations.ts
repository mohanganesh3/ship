/**
 * Database Operations — CRUD for threads and messages
 *
 * Persists all chat state locally via expo-sqlite.
 */
import { openDatabaseAsync, type SQLiteDatabase } from 'expo-sqlite';
import { type Message } from '../stores/chatStore';
import { type Thread } from '../stores/threadStore';
import { CREATE_TABLES_SQL } from './schema';

const DB_NAME = 'maritime-ai.db';

let dbPromise: Promise<SQLiteDatabase> | null = null;
let initializedDbPromise: Promise<SQLiteDatabase> | null = null;

type ThreadRow = {
  id: string;
  title: string;
  preview: string;
  pinned: number;
  created_at: number;
  updated_at: number;
};

type MessageRow = {
  id: string;
  thread_id: string;
  role: Message['role'];
  content: string;
  thinking: string | null;
  think_time: number | null;
  tokens_used: number | null;
  created_at: number;
  has_safety: number;
};

async function getDb(): Promise<SQLiteDatabase> {
  if (!dbPromise) {
    dbPromise = openDatabaseAsync(DB_NAME);
  }

  const db = await dbPromise;
  if (!initializedDbPromise) {
    initializedDbPromise = initializeDb(db);
  }
  return initializedDbPromise;
}

async function initializeDb(db: SQLiteDatabase): Promise<SQLiteDatabase> {
  await db.execAsync(CREATE_TABLES_SQL);
  await ensureThreadsPreviewColumn(db);
  return db;
}

async function ensureThreadsPreviewColumn(db: SQLiteDatabase): Promise<void> {
  const columns = await db.getAllAsync<{ name: string }>('PRAGMA table_info(threads)');
  if (!columns.some((column) => column.name === 'preview')) {
    await db.execAsync(
      "ALTER TABLE threads ADD COLUMN preview TEXT NOT NULL DEFAULT '';",
    );
  }
}

function mapThread(row: ThreadRow): Thread {
  return {
    id: row.id,
    title: row.title,
    preview: row.preview ?? '',
    pinned: !!row.pinned,
    createdAt: row.created_at,
    updatedAt: row.updated_at,
  };
}

function mapMessage(row: MessageRow): Message {
  return {
    id: row.id,
    threadId: row.thread_id,
    role: row.role,
    content: row.content,
    thinking: row.thinking,
    thinkTime: row.think_time,
    tokensUsed: row.tokens_used,
    createdAt: row.created_at,
    hasSafety: !!row.has_safety,
  };
}

export function generateId(): string {
  return Date.now().toString(36) + Math.random().toString(36).slice(2, 11);
}

// ─── THREAD OPERATIONS ──────────────────────────────────────

export async function createThread(title?: string): Promise<Thread> {
  const db = await getDb();
  const now = Date.now();
  const thread: Thread = {
    id: generateId(),
    title: title || 'New Conversation',
    preview: '',
    pinned: false,
    createdAt: now,
    updatedAt: now,
  };
  await db.runAsync(
    `INSERT INTO threads (id, title, preview, pinned, created_at, updated_at)
     VALUES (?, ?, ?, ?, ?, ?)`,
    thread.id,
    thread.title,
    thread.preview,
    0,
    thread.createdAt,
    thread.updatedAt,
  );
  return thread;
}

export async function getThreads(): Promise<Thread[]> {
  const db = await getDb();
  const rows = await db.getAllAsync<ThreadRow>(
    `SELECT id, title, preview, pinned, created_at, updated_at
     FROM threads
     ORDER BY pinned DESC, updated_at DESC`,
  );
  return rows.map(mapThread);
}

export async function deleteThread(id: string): Promise<void> {
  const db = await getDb();
  await db.withTransactionAsync(async () => {
    await db.runAsync('DELETE FROM messages WHERE thread_id = ?', id);
    await db.runAsync('DELETE FROM threads WHERE id = ?', id);
  });
}

export async function pinThread(id: string, pinned: boolean): Promise<void> {
  const db = await getDb();
  await db.runAsync(
    'UPDATE threads SET pinned = ?, updated_at = ? WHERE id = ?',
    pinned ? 1 : 0,
    Date.now(),
    id,
  );
}

export async function updateThreadTitle(id: string, title: string): Promise<void> {
  const db = await getDb();
  await db.runAsync(
    'UPDATE threads SET title = ?, updated_at = ? WHERE id = ?',
    title,
    Date.now(),
    id,
  );
}

export async function updateThreadPreview(id: string, preview: string): Promise<void> {
  const db = await getDb();
  await db.runAsync(
    'UPDATE threads SET preview = ?, updated_at = ? WHERE id = ?',
    preview.substring(0, 100),
    Date.now(),
    id,
  );
}

/**
 * Auto-title: take user's first message, truncate to 60 chars
 */
export function generateThreadTitle(firstMessage: string): string {
  const cleaned = firstMessage.split('\n').join(' ').trim();
  if (cleaned.length <= 60) return cleaned;
  return cleaned.substring(0, 57) + '...';
}

export async function clearAllThreads(): Promise<void> {
  const db = await getDb();
  await db.withTransactionAsync(async () => {
    await db.runAsync('DELETE FROM messages');
    await db.runAsync('DELETE FROM threads');
  });
}

// ─── MESSAGE OPERATIONS ──────────────────────────────────────

export async function addMessage(message: Message): Promise<void> {
  const db = await getDb();
  await db.runAsync(
    `INSERT INTO messages (
      id, thread_id, role, content, thinking, think_time, tokens_used, created_at, has_safety
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)`,
    message.id,
    message.threadId,
    message.role,
    message.content,
    message.thinking,
    message.thinkTime,
    message.tokensUsed,
    message.createdAt,
    message.hasSafety ? 1 : 0,
  );
}

/**
 * Context window management: load last 20 messages per thread
 */
export async function getMessages(threadId: string, limit: number = 20): Promise<Message[]> {
  const db = await getDb();
  const rows = await db.getAllAsync<MessageRow>(
    `SELECT id, thread_id, role, content, thinking, think_time, tokens_used, created_at, has_safety
     FROM messages
     WHERE thread_id = ?
     ORDER BY created_at DESC
     LIMIT ?`,
    threadId,
    limit,
  );

  return rows.reverse().map(mapMessage);
}

export async function searchMessages(query: string): Promise<{ threadId: string; message: Message }[]> {
  const db = await getDb();
  const q = query.toLowerCase();
  const rows = await db.getAllAsync<MessageRow>(
    `SELECT id, thread_id, role, content, thinking, think_time, tokens_used, created_at, has_safety
     FROM messages
     WHERE lower(content) LIKE ?
     ORDER BY created_at DESC
     LIMIT 50`,
    `%${q}%`,
  );

  return rows.map((row) => ({
    threadId: row.thread_id,
    message: mapMessage(row),
  }));
}

// ─── SEED DATA (for demo) ───────────────────────────────────

export async function seedDemoData(): Promise<void> {
  // Production app: do not inject fake maritime conversations into user history.
}
