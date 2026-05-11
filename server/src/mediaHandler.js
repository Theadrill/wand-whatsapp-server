import { downloadMediaMessage } from '@whiskeysockets/baileys';

/**
 * Baixa a figurinha e retorna o buffer original em Base64
 */
export async function processSticker(msg, logger) {
  const sticker = msg.message?.stickerMessage || 
                  msg.message?.viewOnceMessage?.message?.stickerMessage ||
                  msg.message?.viewOnceMessageV2?.message?.stickerMessage;
                  
  if (!sticker) return null;

  try {
    const buffer = await downloadMediaMessage(msg, 'buffer', {}, { logger });

    if (buffer) {
      return buffer.toString('base64');
    }
    
    return null;
  } catch (err) {
    console.error('[MediaHandler] Erro no download:', err.message);
    return null;
  }
}
