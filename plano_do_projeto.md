# 📋 Documento de Especificação: W.A.N.D. (WhatsApp Notification Devices)
**Repositório:** `wand-whatsapp-server`
**Licença:** GPL-3.0

---

## ⚠️ DIRETRIZES CRÍTICAS PARA A IA (LEIA ANTES DE CODAR)
1. **Explicação de Código:** Sempre que gerar um novo código ou arquivo, você **DEVE** mostrar e explicar o que cada parte do código está fazendo. Não entregue apenas o código cru.
2. **Vanilla Node.js:** O servidor deve ser feito em Node.js o mais vanilla possível (sem frameworks pesados no frontend da web).
3. **Ambiente Dinâmico:** O sistema será acessado via Hostname (Tailscale), pois o IP do servidor é dinâmico. O cliente Python deve lidar com tentativas de reconexão automática (*reconnect heartbeat*).
4. **Passo a Passo:** Siga estritamente as fases de desenvolvimento abaixo. **Não tente implementar a próxima fase antes que a anterior esteja 100% funcional, testada e aprovada pelo usuário.**
5. **Arquitetura Modular:** Respeite a separação de responsabilidades (Separation of Concerns) no lado do servidor.
6. **Identificação da Sessão:** Ao conectar via QR Code, a sessão deve ser identificada no WhatsApp como **"WAND Server"**.
7. **Código Limpo:** Nunca utilize CSS ou Scripts inline nos arquivos HTML. Estilos e lógicas devem sempre residir em arquivos separados (`.css` e `.js`) para garantir a modularidade e facilidade de manutenção.

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
   - **O que deve fazer:** Sobe um servidor HTTP vanilla (ex: porta 4750) para servir os arquivos estáticos da pasta `public`.
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
     - Iniciar um loop `asyncio` que tenta conectar no `ws://<HOSTNAME>:4750` (variável configurável no topo do arquivo).
     - **Reconnect Heartbeat:** Se a conexão cair ou o hostname mudar de IP, o script deve tentar reconectar em loop infinito silenciosamente.
     - Ao receber um JSON do servidor WebSocket, invocar uma função do `CustomTkinter` para desenhar o "Toast" (Banner) retangular no canto inferior direito da tela.
     - **Regras do Toast na Fase 1:** Fundo escuro, mostra o Nome e o Texto da mensagem. Fica persistente na tela até o usuário clicar no "X" para fechar. Nenhuma outra interação por enquanto.

---

## 💾 FASE 2: HISTÓRICO E PERSISTÊNCIA
**Objetivo:** Adicionar armazenamento local e uma janela minimalista para visualização de mensagens anteriores.

*   **[X] 2.1. Banco de Dados e Histórico (`src/database.js` e SQLite):** Salvar as mensagens recebidas localmente no Node e criar rotas WS para o cliente pedir histórico.
*   **[X] 2.2. Janela Mínima de Histórico (`main.py`):** Desenvolver uma janela mínima no cliente Python que exibe o histórico de mensagens recentes com persistência que será acessada ao clicar no icone da bandeija ou em qualquer lugar do toast que não seja o botão X. A janela mínima vai mostrar as mensagens ordenadas por data e hora, com o nome do remetente, o texto da mensagem e o horário em que foi recebida, em uma lista.
*   **[X] 2.3. Resposta via Histórico:** Habilidade de responder a uma mensagem ao clicar diretamente em uma das mensagens listadas na janela de histórico.

---

## 👤 FASE 3: PADRONIZAÇÃO E RESOLUÇÃO DE CONTATOS (Nova Fase)
**Objetivo:** Implementar padronização de contatos, resolução automática de nomes amigáveis usando metadados e persistência de contatos para evitar JIDs numéricos e IDs mascarados (`@lid`).

*   **[X] 3.1. Esteira de Resolução de Nomes (Fallback Chain):** Criar lógica no servidor Node.js que resolva o nome do remetente com a seguinte prioridade antes de enviar a mensagem ao cliente Python:
    1. **Mensagem própria (`fromMe: true`):** Sempre identificar como **"Você"**.
    2. **Agenda Local (`store.contacts`):** Buscar o nome cadastrado na lista de contatos do usuário sincronizada pelo Baileys.
    3. **Nome de Perfil (`pushName`):** Utilizar o nome configurado pelo próprio remetente no WhatsApp.
    4. **Máscara Telefônica:** Formatar o número do telefone de forma elegante (ex: `+55 (11) 99999-9999`) caso nenhum nome seja encontrado.
*   **[X] 3.2. Resolução de IDs Mascarados (`@lid`):** Identificar e tratar JIDs do tipo `@lid` (IDs internos do WhatsApp que mascaram a identidade real dos usuários). Usar a inteligência do Baileys para buscar correspondências de nomes ou contatos amigáveis e evitar a exibição de números desconhecidos como `126010179747935`.
*   **[X] 3.3. Sincronização de Contatos no SQLite:** Criar tabela de `contacts` no banco SQLite do servidor e capturar eventos do Baileys (`contacts.upsert`, `contacts.update`) para atualizar continuamente o catálogo local com o mapeamento `jid -> display_name`.
*   **[X] 3.4. Enriquecimento da Mensagem no Servidor:** Ajustar a mensagem entregue via WebSocket do servidor para o cliente Python, de modo que já contenha os campos formatados `senderName` e `senderNumber`, simplificando a renderização na UI Python.

---

## 🌟 FASE 4: A APLICAÇÃO COMPLETA (Implementar apenas após aprovação da Fase 3)
**Objetivo:** UI completa, motor de privacidade e filtros avançados.

*   **[X] 4.1. UI Master-Detail (`main.py` e `ui_components.py`):** Adicionar um Sidebar (contatos) à esquerda e tela de histórico geral na direita como estado inicial (Feed geral macOS). Incluído o botão **Dashboard** premium na barra lateral que permite retornar a esta visualização agregada inicial a qualquer momento limpando o estado de seleção.
*   **4.2. Auto-Privacy (Toast do Cliente):** Atualizar o Toast para borrar o texto após X segundos e empilhar badges vermelhos de contagem. Clicar no Toast abre o Chat correspondente.
*   **4.3. Web UI e Configurações (`src/config.js`):** Criar os botões na UI do Python ou na interface Web do servidor para gerenciar Whitelist/Blacklist (Contatos, Grupos e Canais), Modo Não Perturbe e Tempo de Censura. O Node deve aplicar os filtros (descartando mensagens da blacklist na raiz).
*   **4.4. Pipeline de Mídia (Baileys + Python):** Implementar os 3 estágios de economia de dados: (1) Preview Thumbnail -> (2) Download em RAM sob demanda -> (3) Gravar em Disco.

---

## 🔧 REFATORAÇÃO TÉCNICA: Correções de Concorrência e I/O (Maio/2026)

**Objetivo:** Corrigir três falhas estruturais de concorrência e I/O identificadas na auditoria técnica do projeto, aplicando os padrões das skills `python-pro` e `async-python-patterns`.

### Fix 1 — Cliente Python: Fila Thread-Safe (`client/network_client.py` + `client/main.py`)

**Problema:** O canal de comunicação entre a thread `asyncio` (WebSocket) e a thread principal do Tkinter era uma lista Python simples (`msg_queue = []`). O CPython não garante atomicidade em operações concorrentes de `append()` + `pop(0)`, o que poderia causar corrupção de dados ou condições de corrida sob carga alta de mensagens.

**Correção aplicada:**
- `self.msg_queue` substituído por `queue.Queue()` (da stdlib, inerentemente thread-safe).
- Escrita: `self.msg_queue.put_nowait(data)` na thread asyncio.
- Leitura: `self.msg_queue.get_nowait()` com `except queue.Empty` na thread Tkinter.
- Type hints completos adicionados em `NetworkClient`.
- `open_timeout=10` adicionado ao `websockets.connect()` para evitar travamento em hosts sem resposta.
- `CancelledError` tratado explicitamente em `listen()` para suportar shutdown gracioso.

### Fix 2 — Cliente Python: Shutdown Gracioso (`client/main.py`)

**Problema:** `quit_app()` e `restart_app()` usavam `os._exit(0)`, que termina o processo abruptamente sem fechar sockets WebSocket, deixando conexões TCP em estado `TIME_WAIT` no sistema operacional.

**Correção aplicada:**
- Criado método `_shutdown_async_loop()` que usa `asyncio.all_tasks()` para cancelar todas as corrotinas pendentes no loop antes de parar o loop via `loop.call_soon_threadsafe(loop.stop)`.
- `os._exit(0)` removido de ambos os métodos.
- `root.destroy()` agendado com `root.after(200, ...)` para dar 200ms ao loop asyncio para processar os cancelamentos antes do Tkinter fechar.
- Thread do WebSocket armazenada em `self._ws_thread` para referência futura.

### Fix 3 — Servidor Node.js: I/O Não-Bloqueante (`server/src/whatsapp.js`)

**Problema:** O `setInterval` de 10 segundos usava `fs.writeFileSync()` para persistir os stores de chats e contatos em disco. Operação síncrona que bloqueia o Event Loop do Node.js durante a serialização JSON e a escrita — podendo causar latência nas mensagens WebSocket e perda de eventos do Baileys conforme os arquivos crescem.

**Correção aplicada:**
- `setInterval` refatorado para chamar uma função `async` (`persistStores`).
- `fs.writeFileSync()` substituído por `await fs.promises.writeFile()` (não-bloqueante).
- O Event Loop agora permanece livre para processar mensagens e conexões WS durante a persistência.

### Fix 4 — Servidor Node.js: Concorrência e Locks no SQLite (`server/src/database.js`)

**Problema:** O SQLite (de arquivo único) sofria locks de concorrência com o Baileys escrevendo novas mensagens em segundo plano. Consultas rápidas e sequenciais (`get_chat_history`) geravam erros `SQLITE_BUSY: database is locked`, capturados no catch silenciosamente, fazendo com que a UI Python exibisse conversas vazias até o destravamento do arquivo.

**Correção aplicada:**
- Habilitado o modo **WAL (Write-Ahead Logging)** (`PRAGMA journal_mode = WAL`), que permite a leitores paralelos realizarem buscas de histórico simultaneamente a gravações sem bloqueios.
- Definido um **`busy_timeout` de 10 segundos** (`PRAGMA busy_timeout = 10000`), para que o SQLite gerencie a fila de concorrência de forma suave e aguarde liberação em vez de dar erro instantâneo de lock.

---
**Fim das Especificações.**