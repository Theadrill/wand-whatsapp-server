import { createServer } from './http.js';
import { setupWebSocket } from './websocket.js';
import { connectToWhatsApp } from './whatsapp.js';
import { setupTray } from './tray.js';

/**
 * Ponto de entrada principal do W.A.N.D. Server
 * Orquestra a inicialização dos módulos HTTP, WS e WhatsApp
 */
async function bootstrap() {
  console.log('--- W.A.N.D. Server ---');
  
  try {
    // 1. Inicializa o Servidor HTTP
    const { server, start } = createServer();
    
    // 2. Inicializa o WebSocket (anexado ao HTTP)
    setupWebSocket(server);

    // 3. Inicializa a System Tray (Bandeja)
    await setupTray();

    // 4. Inicializa a conexão com o WhatsApp
    connectToWhatsApp();
    
    // Inicia a escuta na porta configurada
    start();
    
    console.log('[System] Servidor HTTP e WS prontos.');
  } catch (error) {
    console.error('[Fatal] Falha ao iniciar o servidor:', error);
    process.exit(1);
  }
}

bootstrap();
