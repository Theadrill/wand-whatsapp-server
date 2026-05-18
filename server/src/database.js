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
  const dbPath = path.join(__dirname, '..', 'user.db');
  
  db = await open({
    filename: dbPath,
    driver: sqlite3.Database
  });

  // Habilita o modo WAL (Write-Ahead Logging) e define busy_timeout de 10s para concorrência fluida
  try {
    await db.run('PRAGMA journal_mode = WAL');
    await db.run('PRAGMA busy_timeout = 10000');
    console.log('[DB] PRAGMAs WAL e busy_timeout configurados com sucesso.');
  } catch (pragmaError) {
    console.error('[DB] Erro ao aplicar PRAGMAs:', pragmaError.message);
  }

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

  await db.exec(`
    CREATE TABLE IF NOT EXISTS contacts (
      jid TEXT PRIMARY KEY,
      name TEXT,
      verifiedName TEXT,
      displayName TEXT
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
      `SELECT m.*, 
              c.name as contactName, 
              c.verifiedName as contactVerifiedName, 
              c.displayName as contactDisplayName 
       FROM messages m 
       LEFT JOIN contacts c ON m.remoteJid = c.jid 
       ORDER BY m.timestamp DESC LIMIT ?`,
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

/**
 * Salva ou atualiza um contato no banco de dados SQLite.
 */
export async function saveContact({ jid, name, verifiedName, displayName }) {
  if (!db) await initDatabase();
  try {
    await db.run(
      'INSERT OR REPLACE INTO contacts (jid, name, verifiedName, displayName) VALUES (?, ?, ?, ?)',
      [jid, name, verifiedName, displayName]
    );
  } catch (error) {
    console.error('[DB] Erro ao salvar contato no banco:', error);
  }
}

/**
 * Recupera um contato do banco de dados SQLite.
 */
export async function getContact(jid) {
  if (!db) await initDatabase();
  try {
    return await db.get('SELECT * FROM contacts WHERE jid = ?', [jid]);
  } catch (error) {
    console.error('[DB] Erro ao recuperar contato do banco:', error);
    return null;
  }
}

/**
 * Recupera todos os chats ativos ordenados pela última mensagem.
 */
export async function getChats() {
  if (!db) await initDatabase();
  try {
    // Busca a última mensagem de cada remoteJid e traz o contato associado se existir
    const rows = await db.all(`
      SELECT 
        m.remoteJid,
        m.text as lastText,
        m.timestamp as lastTimestamp,
        m.fromMe as lastFromMe,
        m.senderName as lastSenderName,
        c.name as contactName,
        c.verifiedName as contactVerifiedName,
        c.displayName as contactDisplayName
      FROM messages m
      INNER JOIN (
        SELECT remoteJid, MAX(timestamp) as max_ts
        FROM messages
        GROUP BY remoteJid
      ) latest ON m.remoteJid = latest.remoteJid AND m.timestamp = latest.max_ts
      LEFT JOIN contacts c ON m.remoteJid = c.jid
      GROUP BY m.remoteJid
      ORDER BY m.timestamp DESC
    `);
    return rows;
  } catch (error) {
    console.error('[DB] Erro ao buscar lista de chats:', error);
    return [];
  }
}

/**
 * Recupera o histórico de mensagens de um chat específico.
 */
export async function getChatHistory(remoteJid, limit = 50) {
  if (!db) await initDatabase();
  try {
    return await db.all(
      'SELECT * FROM messages WHERE remoteJid = ? ORDER BY timestamp DESC LIMIT ?',
      [remoteJid, limit]
    );
  } catch (error) {
    console.error('[DB] Erro ao buscar histórico do chat:', error);
    return [];
  }
}

