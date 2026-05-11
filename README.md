# 🪄 W.A.N.D. (WhatsApp Notification Devices)
**Repositório:** `wand-whatsapp-server`

> **Status do Projeto:** 🚧 **Em Desenvolvimento (Iniciando Fase 1)**
> *Este projeto está sendo construído em etapas. Verifique o Roadmap abaixo para saber quais funcionalidades já estão ativas.*

O **W.A.N.D.** é uma solução de arquitetura leve (Server/Client) desenvolvida para quem precisa monitorar o WhatsApp sem interrupções de fluxo de trabalho ou poluição visual. 

Rodando um servidor Node.js silencioso em background, ele captura mensagens via `@whiskeysockets/baileys` e faz o *broadcast* via WebSockets para qualquer dispositivo conectado (Windows, Android, etc). Desenvolvido para lidar com IPs dinâmicos de forma transparente via resolução de Hostname (ex: Tailscale / MagicDNS).

**Principais Diferenciais:**
- 📡 **Multi-Dispositivos:** Conecte via Hostname e receba notificações simultâneas onde estiver.
- 🛡️ **Auto-Privacy:** Notificações em banner com censura automática por tempo (blur) para ambientes expostos.
- 📉 **Economia de Dados Extrema:** Motor de Blacklist/Whitelist nativo e download de mídia em 3 estágios (apenas preview borrado por padrão).
- 🗄️ **Local-First:** Histórico mantido exclusivamente no servidor via banco SQLite leve, mantendo os clients totalmente independentes.

---

## 🗺️ Roadmap e Fases de Implementação

O projeto adota uma abordagem de MVP (Produto Mínimo Viável) para garantir que a comunicação base seja sólida antes da implementação de interfaces ricas.

### 📍 Fase 1: MVP (Core & Comunicação) — `[Em Andamento ⏳]`
*Objetivo: Estabelecer a comunicação base e receber notificações no Windows de forma passiva.*
- [ ] Servidor Node.js puro conectado à API do WhatsApp via Baileys.
- [ ] Rota HTTP provisória servindo HTML simples para pareamento (QR Code).
- [ ] Servidor WebSocket embutido para *broadcast* de eventos.
- [ ] Script Cliente Windows (Python) com *reconnect heartbeat*.
- [ ] Notificações em Toast persitentes exibindo Avatar, Nome e Texto.

### 🚀 Fase 2: UI Avançada e Gerenciamento — `[Planejado 📝]`
*Objetivo: Implementar banco de dados, layout Master-Detail, filtros e mídia inteligente.*
- [ ] **Histórico Centralizado:** Integração do SQLite no servidor Node.js.
- [ ] **Interface Gráfica (Python/CustomTkinter):** Layout Master-Detail (Dashboard Global + Chats Específicos).
- [ ] **Web UI de Configurações:** Painel acessível via navegador para gerenciar o comportamento do Node.js.
- [ ] **Motor de Filtros:** Whitelist/Blacklist aplicada direto na raiz do servidor para barrar mensagens indesejadas e economizar banda.
- [ ] **Auto-Privacy (Client):** Temporizador para ocultar (blur) o texto do Toast após 10 segundos de exibição na tela.
- [ ] **Pipeline de Mídia:** Estágio 1 (Thumbnail borrada) -> Estágio 2 (Download em RAM) -> Estágio 3 (Gravação em Disco via Windows Explorer).

---
