import sqlite3 from 'sqlite3';
import { open } from 'sqlite';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

let db;

/**
 * Inicializa o banco de dados SQLite.
 * Cria a tabela de mensagens se ela não existir.
 */
export async function initDatabase() {
  const dbPath = path.join(__dirname, '..', 'user_messages.db');
  
  db = await open({
    filename: dbPath,
    driver: sqlite3.Database
  });

  await db.exec(`
    CREATE TABLE IF NOT EXISTS messages (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      remoteJid TEXT,
      senderName TEXT,
      text TEXT,
      timestamp INTEGER,
      fromMe INTEGER
    )
  `);

  await db.exec(`
    CREATE TABLE IF NOT EXISTS muted_chats (
      remoteJid TEXT PRIMARY KEY
    )
  `);

  console.log('[DB] Banco de dados inicializado em:', dbPath);
  return db;
}

/**
 * Salva uma nova mensagem no banco de dados.
 * @param {Object} msg - Objeto da mensagem contendo remoteJid, senderName, text, timestamp e fromMe.
 */
export async function saveMessage({ remoteJid, senderName, text, timestamp, fromMe }) {
  if (!db) await initDatabase();
  
  try {
    await db.run(
      'INSERT INTO messages (remoteJid, senderName, text, timestamp, fromMe) VALUES (?, ?, ?, ?, ?)',
      [remoteJid, senderName, text, timestamp, fromMe ? 1 : 0]
    );
  } catch (error) {
    console.error('[DB] Erro ao salvar mensagem:', error);
  }
}

/**
 * Recupera o histórico de mensagens.
 * @param {number} limit - Número máximo de mensagens a serem recuperadas.
 * @returns {Promise<Array>} - Lista de mensagens.
 */
export async function getHistory(limit = 50) {
  if (!db) await initDatabase();
  
  try {
    return await db.all(
      'SELECT * FROM messages ORDER BY timestamp DESC LIMIT ?',
      [limit]
    );
  } catch (error) {
    console.error('[DB] Erro ao buscar histórico:', error);
    return [];
  }
}

/**
 * Define se um chat está silenciado no banco de dados.
 */
export async function setChatMutedStatus(remoteJid, isMuted) {
  if (!db) await initDatabase();
  try {
    if (isMuted) {
      await db.run('INSERT OR REPLACE INTO muted_chats (remoteJid) VALUES (?)', [remoteJid]);
    } else {
      await db.run('DELETE FROM muted_chats WHERE remoteJid = ?', [remoteJid]);
    }
  } catch (error) {
    console.error('[DB] Erro ao atualizar status de silêncio do chat:', error);
  }
}

/**
 * Verifica se um chat está marcado como silenciado no banco de dados.
 */
export async function isChatMutedInDB(remoteJid) {
  if (!db) await initDatabase();
  try {
    const row = await db.get('SELECT 1 FROM muted_chats WHERE remoteJid = ?', [remoteJid]);
    return !!row;
  } catch (error) {
    console.error('[DB] Erro ao verificar silêncio do chat no banco:', error);
    return false;
  }
}
