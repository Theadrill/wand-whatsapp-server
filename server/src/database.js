import sqlite3 from 'sqlite3';
import { open } from 'sqlite';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

let db;

/**
 * Helper interno para remover sufixos de dispositivo (:0, :1, etc.) de qualquer JID.
 */
function sanitizeJid(jid) {
  if (!jid || typeof jid !== 'string') return jid;
  if (jid.includes(':')) {
    const parts = jid.split('@');
    if (parts.length === 2) {
      const user = parts[0].split(':')[0];
      const domain = parts[1];
      return `${user}@${domain}`;
    }
  }
  return jid;
}

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

  // Migração legada: limpa JIDs contendo ":" das tabelas de forma proativa
  try {
    await db.run(`
      UPDATE messages 
      SET remoteJid = SUBSTR(remoteJid, 1, INSTR(remoteJid, ':') - 1) || '@' || SUBSTR(remoteJid, INSTR(remoteJid, '@') + 1) 
      WHERE remoteJid LIKE '%:%@%'
    `);
    await db.run(`
      UPDATE contacts 
      SET jid = SUBSTR(jid, 1, INSTR(jid, ':') - 1) || '@' || SUBSTR(jid, INSTR(jid, '@') + 1) 
      WHERE jid LIKE '%:%@%'
    `);
    await db.run(`
      UPDATE muted_chats 
      SET remoteJid = SUBSTR(remoteJid, 1, INSTR(remoteJid, ':') - 1) || '@' || SUBSTR(remoteJid, INSTR(remoteJid, '@') + 1) 
      WHERE remoteJid LIKE '%:%@%'
    `);
    console.log('[DB] Migração de sanitização de JIDs legados concluída com sucesso.');
  } catch (migError) {
    console.error('[DB] Erro na migração de sanitização:', migError.message);
  }

  console.log('[DB] Banco de dados inicializado em:', dbPath);
  return db;
}

/**
 * Salva uma nova mensagem no banco de dados.
 * @param {Object} msg - Objeto da mensagem contendo remoteJid, senderName, text, timestamp e fromMe.
 */
export async function saveMessage({ remoteJid, senderName, text, timestamp, fromMe }) {
  if (!db) await initDatabase();
  
  const cleanJid = sanitizeJid(remoteJid);
  try {
    await db.run(
      'INSERT INTO messages (remoteJid, senderName, text, timestamp, fromMe) VALUES (?, ?, ?, ?, ?)',
      [cleanJid, senderName, text, timestamp, fromMe ? 1 : 0]
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
  const cleanJid = sanitizeJid(remoteJid);
  try {
    if (isMuted) {
      await db.run('INSERT OR REPLACE INTO muted_chats (remoteJid) VALUES (?)', [cleanJid]);
    } else {
      await db.run('DELETE FROM muted_chats WHERE remoteJid = ?', [cleanJid]);
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
  const cleanJid = sanitizeJid(remoteJid);
  try {
    const row = await db.get('SELECT 1 FROM muted_chats WHERE remoteJid = ?', [cleanJid]);
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
  const cleanJid = sanitizeJid(jid);
  try {
    await db.run(
      'INSERT OR REPLACE INTO contacts (jid, name, verifiedName, displayName) VALUES (?, ?, ?, ?)',
      [cleanJid, name, verifiedName, displayName]
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
  const cleanJid = sanitizeJid(jid);
  try {
    return await db.get('SELECT * FROM contacts WHERE jid = ?', [cleanJid]);
  } catch (error) {
    console.error('[DB] Erro ao recuperar contato do banco:', error);
    return null;
  }
}

/**
 * Recupera todos os contatos do banco de dados SQLite ordenados alfabeticamente.
 */
export async function getAllContacts() {
  if (!db) await initDatabase();
  try {
    return await db.all(`
      SELECT * FROM contacts 
      WHERE (name IS NOT NULL AND name != '')
         OR (verifiedName IS NOT NULL AND verifiedName != '')
         OR (displayName IS NOT NULL AND displayName != '')
      ORDER BY COALESCE(name, verifiedName, displayName) ASC
    `);
  } catch (error) {
    console.error('[DB] Erro ao recuperar todos os contatos do banco:', error);
    return [];
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
        (
          SELECT senderName 
          FROM messages 
          WHERE remoteJid = m.remoteJid AND fromMe = 0 
          ORDER BY timestamp DESC 
          LIMIT 1
        ) as lastIncomingSenderName,
        c.name as contactName,
        c.verifiedName as contactVerifiedName,
        c.displayName as contactDisplayName
      FROM messages m
      INNER JOIN (
        SELECT remoteJid, MAX(timestamp) as max_ts
        FROM messages
        GROUP BY remoteJid
      ) latest ON m.remoteJid = latest.remoteJid AND m.timestamp = latest.max_ts
      LEFT JOIN contacts c ON (
        m.remoteJid = c.jid 
        OR (
          INSTR(m.remoteJid, '@') > 0 
          AND INSTR(c.jid, '@') > 0 
          AND SUBSTR(m.remoteJid, 1, INSTR(m.remoteJid, '@') - 1) = SUBSTR(c.jid, 1, INSTR(c.jid, '@') - 1)
        )
      )
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

/**
 * Recupera o histórico de mensagens de um chat específico unificando dois JIDs (ex: LID e PN).
 */
export async function getChatHistoryUnified(jid1, jid2, limit = 50) {
  if (!db) await initDatabase();
  try {
    return await db.all(
      'SELECT * FROM messages WHERE remoteJid = ? OR remoteJid = ? ORDER BY timestamp DESC LIMIT ?',
      [jid1, jid2, limit]
    );
  } catch (error) {
    console.error('[DB] Erro ao buscar histórico unificado do chat:', error);
    return [];
  }
}

