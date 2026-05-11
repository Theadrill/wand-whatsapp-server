# 📋 Documento de Especificação: W.A.N.D. (WhatsApp Notification Devices)
**Repositório:** `wand-whatsapp-server`
**Licença:** GPL-3.0

---

## ⚠️ DIRETRIZES CRÍTICAS PARA A IA (LEIA ANTES DE CODAR)
1. **Explicação de Código:** Sempre que gerar um novo código ou arquivo, você **DEVE** mostrar e explicar o que cada parte do código está fazendo. Não entregue apenas o código cru.
2. **Vanilla Node.js:** O servidor deve ser feito em Node.js o mais vanilla possível (sem frameworks pesados no frontend da web).
3. **Ambiente Dinâmico:** O sistema será acessado via Hostname (Tailscale), pois o IP do servidor é dinâmico. O cliente Python deve lidar com tentativas de reconexão automática (*reconnect heartbeat*).
4. **Passo a Passo:** Siga estritamente as fases de desenvolvimento abaixo. **Não tente implementar a Fase 2 antes que a Fase 1 esteja 100% funcional, testada e aprovada pelo usuário.**
5. **Arquitetura Modular:** Respeite a separação de responsabilidades (Separation of Concerns) no lado do servidor.
6. **Identificação da Sessão:** Ao conectar via QR Code, a sessão deve ser identificada no WhatsApp como **"WAND Server"**.

---

## 📖 README / VISÃO GERAL
O **W.A.N.D.** é uma solução de arquitetura leve (Server/Client) para monitorar o WhatsApp sem interrupções de fluxo de trabalho. 
Rodando um servidor Node.js silencioso em background, ele captura mensagens via `@whiskeysockets/baileys` e faz o *broadcast* via WebSockets para qualquer dispositivo conectado. 

**Arquitetura Global:**
*   **Servidor:** Node.js puro + `@whiskeysockets/baileys`.
*   **Comunicação:** WebSockets (`ws`).
*   **Armazenamento (Fase 2):** SQLite local no servidor.
*   **Cliente Windows:** Python + `CustomTkinter` (UI) + `websockets`.

---

## 🚀 FASE 1: MVP (Produto Mínimo Viável)
**Objetivo:** Estabelecer a comunicação base e receber notificações passivas no Windows.

### Estrutura de Arquivos Esperada (Fase 1)

wand-whatsapp-server/
├── server/
│   ├── package.json
│   ├── src/
│   │   ├── index.js          # Ponto de entrada
│   │   ├── whatsapp.js       # Core do Baileys
│   │   ├── websocket.js      # Servidor WS
│   │   └── http.js           # Servidor Web vanilla
│   └── public/
│       └── index.html        # Frontend vanilla (QR Code)
└── client/
    ├── requirements.txt
    └── main.py


### Detalhamento dos Arquivos (Fase 1)

#### Lado do Servidor (`/server`)
1. **`package.json`**:
   - Deve conter as dependências essenciais: `@whiskeysockets/baileys`, `ws`, `qrcode` (para renderizar o QR code na web) e `node-notifier` (para o tray do servidor).
2. **`src/index.js`**:
   - **O que deve fazer:** É o orquestrador. Importa e inicializa o módulo HTTP, o módulo WebSocket e o módulo do WhatsApp, conectando-os.
3. **`src/http.js`**:
   - **O que deve fazer:** Sobe um servidor HTTP vanilla (ex: porta 3000) para servir os arquivos estáticos da pasta `public`.
4. **`src/websocket.js`**:
   - **O que deve fazer:** Sobe um servidor WebSocket (`ws`) anexado ao servidor HTTP. Exporta uma função de `broadcast(data)` para que outros módulos possam enviar JSON para os clientes conectados.
5. **`src/whatsapp.js`**:
   - **O que deve fazer:** Inicializa e gerencia a conexão com o Baileys. Escuta os eventos de `connection.update` (para repassar o QR Code via WebSocket) e `messages.upsert`. Ao receber uma mensagem, extrai `nome`, `texto` e `avatar` e chama a função `broadcast()` do `websocket.js`.
6. **`public/index.html`**:
   - **O que deve fazer:** Página HTML/JS vanilla rudimentar que conecta no WebSocket do servidor para receber o base64 do QR Code e renderizá-lo na tela. Se o status mudar para "conectado", exibe apenas "Servidor Online".

#### Lado do Cliente (`/client`)
1. **`requirements.txt`**:
   - Deve conter: `websockets`, `customtkinter`, e `asyncio` (nativo).
2. **`main.py`**:
   - **O que deve fazer:**
     - Iniciar um loop `asyncio` que tenta conectar no `ws://<HOSTNAME>:3000` (variável configurável no topo do arquivo).
     - **Reconnect Heartbeat:** Se a conexão cair ou o hostname mudar de IP, o script deve tentar reconectar em loop infinito silenciosamente.
     - Ao receber um JSON do servidor WebSocket, invocar uma função do `CustomTkinter` para desenhar o "Toast" (Banner) retangular no canto inferior direito da tela.
     - **Regras do Toast na Fase 1:** Fundo escuro, mostra o Nome e o Texto da mensagem. Fica persistente na tela até o usuário clicar no "X" para fechar. Nenhuma outra interação por enquanto.

---

## 🌟 FASE 2: A APLICAÇÃO COMPLETA (Implementar apenas após aprovação da Fase 1)
**Objetivo:** Adicionar persistência, UI completa, motor de privacidade e filtros.

*   **2.1. Banco de Dados e Histórico (`src/database.js` e SQLite):** Salvar as mensagens recebidas localmente no Node e criar rotas WS para o cliente pedir histórico.
*   **2.2. UI Master-Detail (`main.py`):** Mudar de apenas um Toast para uma Janela Principal em CustomTkinter contendo a Sidebar (contatos) à esquerda e o Dashboard/Chat à direita.
*   **2.3. Auto-Privacy (Toast do Cliente):** Atualizar o Toast para borrar o texto após X segundos e empilhar badges vermelhos de contagem. Clicar no Toast abre o Chat correspondente.
*   **2.4. Web UI e Configurações (`src/config.js`):** Criar os botões na UI do Python ou na interface Web do servidor para gerenciar Whitelist/Blacklist, Modo Não Perturbe e Tempo de Censura. O Node deve aplicar os filtros (descartando mensagens da blacklist na raiz).
*   **2.5. Pipeline de Mídia (Baileys + Python):** Implementar os 3 estágios de economia de dados: (1) Preview Thumbnail -> (2) Download em RAM sob demanda -> (3) Gravar em Disco.

---
**Fim das Especificações.** 
**Ação para a IA:** Responda confirmando o entendimento deste documento pergunte se pode iniciar a codificação da **FASE 1** (somente), gerando os arquivos do servidor e do cliente e explicando detalhadamente o que cada bloco faz.