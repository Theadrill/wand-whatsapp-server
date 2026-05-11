import SysTray from 'systray2';
import path from 'path';
import os from 'os';
import { fileURLToPath } from 'url';
import { exec } from 'child_process';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Importação resiliente para ESM
const SysTrayClass = SysTray.default || SysTray;

let systray;

/**
 * Gera a configuração do menu da Tray
 */
function getMenuConfig(connected = false) {
  // Garantindo caminho absoluto relativo ao arquivo src/tray.js
  const iconPath = path.resolve(__dirname, '../public/icon.ico');
  
  return {
    menu: {
      icon: iconPath,
      title: 'W.A.N.D. Server',
      tooltip: connected ? 'WhatsApp Conectado' : 'Aguardando WhatsApp',
      items: [
        {
          title: '🌐 Abrir Interface',
          enabled: true
        },
        {
          title: '---',
          enabled: false
        },
        {
          title: '❌ Sair e Encerrar',
          enabled: true
        }
      ]
    },
    debug: false,
    copyDir: true
  };
}

/**
 * Inicializa a System Tray
 */
export async function setupTray() {
  try {
    console.log('[Tray] Iniciando processo da bandeja...');
    systray = new SysTrayClass(getMenuConfig());

    // Na versão atual, ready() retorna uma Promise
    await systray.ready();
    
    console.log('[Tray] Ícone da bandeja carregado e pronto.');

    systray.onClick((action) => {
      const title = action.item.title;

      if (title.includes('Abrir Interface')) {
        const url = 'http://localhost:3000';
        const command = os.platform() === 'win32' ? `start ${url}` : `open ${url}`;
        exec(command);
      } 
      else if (title.includes('Sair e Encerrar')) {
        console.log('[System] Encerrando via Tray...');
        systray.kill();
        process.exit(0);
      }
    });

  } catch (error) {
    console.error('[Tray] Erro crítico ao iniciar bandeja:', error);
  }
}

/**
 * Atualiza o status visual da Tray
 * @param {boolean} connected 
 */
export function updateTrayStatus(connected) {
  if (systray) {
    systray.sendAction({
      type: 'update-menu',
      menu: getMenuConfig(connected).menu
    });
  }
}
