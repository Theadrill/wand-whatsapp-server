import customtkinter as ctk
from config_manager import CONFIG
from PIL import Image
import io
import base64
import datetime

class ToastNotification(ctk.CTkToplevel):
    def __init__(self, master, sender, message, sticker_base64=None):
        super().__init__(master)
        self.title("W.A.N.D. Notification")
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.attributes("-toolwindow", True)
        self.lift()
        
        # Janela transparente
        transparent_color = "#000001"
        self.attributes("-transparentcolor", transparent_color)
        self.configure(fg_color=transparent_color)
        self.config(bg=transparent_color)
        
        # --- CONFIGURAÇÃO DE TAMANHO E POSIÇÃO NA TELA ---
        width = CONFIG['toast_width']
        height = CONFIG['toast_height']
        
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        # Posiciona no canto inferior direito com margens de 20px e 60px
        x = screen_width - width - 20 
        y = screen_height - height - 60
        self.geometry(f"{width}x{height}+{x}+{y}")

        # CONTAINER MOLDURA (Transparente com Borda de 1px)
        self.container = ctk.CTkFrame(
            self, 
            fg_color="transparent", 
            corner_radius=15,
            border_width=1,
            border_color="#075E54"
        )
        self.container.pack(fill="both", expand=True)

        # TOPO (Verde Escuro)
        self.top_bg = ctk.CTkFrame(
            self.container,
            fg_color="#0F5429",
            corner_radius=14,
            height=50
        )
        self.top_bg.place(relx=0, rely=0, relwidth=1)

        # FILLER DO TOPO (Achata a base do título)
        self.top_filler = ctk.CTkFrame(
            self.top_bg,
            fg_color="#0F5429",
            corner_radius=14,
            height=20
        )
        self.top_filler.place(relx=0, rely=0.6, relwidth=1)

        # CORPO (Verde Médio)
        self.bottom_bg = ctk.CTkFrame(
            self.container,
            fg_color="#188741",
            corner_radius=14
        )
        self.bottom_bg.place(relx=0, y=50, relwidth=1, relheight=0.68)

        # FILLER DO CORPO (Encaixe perfeito na divisa)
        self.bottom_filler = ctk.CTkFrame(
            self.bottom_bg,
            fg_color="#188741",
            corner_radius=0,
            height=20
        )
        self.bottom_filler.place(relx=0, rely=0, relwidth=1)

        # Título
        self.lbl_sender = ctk.CTkLabel(
            self.top_bg, 
            text=sender, 
            font=ctk.CTkFont(family="Segoe UI", weight="bold", size=15), 
            text_color="#FFFFFF"
        )
        self.lbl_sender.place(relx=0.05, rely=0.25)

        # --- BOTÃO FECHAR DO TOAST ---
        self.btn_close = ctk.CTkButton(
            self.top_bg, 
            text="✕", 
            width=30, 
            height=30, 
            fg_color="transparent", 
            hover_color="#128C7E", 
            text_color="#FFFFFF",
            font=ctk.CTkFont(size=16),
            command=self.destroy
        )
        # Posição do botão fechar (relx=0.88 é a direita)
        self.btn_close.place(relx=0.88, rely=0.2)

        # Processamento da Figurinha
        if (sticker_base64):
            try:
                image_data = base64.b64decode(sticker_base64)
                img = Image.open(io.BytesIO(image_data))
                # Redimensiona para caber melhor (usando mais largura se necessário)
                img.thumbnail((200, 48))
                self.ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=(img.width, img.height))
                
                self.lbl_preview = ctk.CTkLabel(self.bottom_bg, image=self.ctk_img, text="")
                self.lbl_preview.place(relx=0.06, rely=0.10)
            except Exception as e:
                self.show_message(message, width)
        else:
            self.show_message(message, width)

        # Permite abrir o histórico ao clicar em qualquer lugar que não seja o botão fechar
        self.click_callback = None
        self.bind_click_events(self.container)
        self.bind_click_events(self.top_bg)
        self.bind_click_events(self.bottom_bg)
        self.bind_click_events(self.lbl_sender)

        self.force_on_top()

    def bind_click_events(self, widget):
        widget.bind("<Button-1>", lambda e: self.on_toast_click())

    def on_toast_click(self):
        if self.click_callback:
            self.click_callback()
        self.destroy()

    def set_click_callback(self, callback):
        self.click_callback = callback
        # Re-bind labels que podem ser criados depois
        if hasattr(self, 'lbl_message'):
            self.bind_click_events(self.lbl_message)
        if hasattr(self, 'lbl_preview'):
            self.bind_click_events(self.lbl_preview)

    def show_message(self, message, width):
        self.lbl_message = ctk.CTkLabel(
            self.bottom_bg, 
            text=message, 
            wraplength=width-40, 
            justify="left", 
            text_color="#E9EDEF",
            font=ctk.CTkFont(family="Segoe UI Variable Text", size=13)
        )
        self.lbl_message.place(relx=0.06, rely=0.10)

    def force_on_top(self):
        if self.winfo_exists():
            self.attributes("-topmost", True)
            self.lift()
            self.after(2000, self.force_on_top)


class HistoryWindow(ctk.CTkToplevel):
    def __init__(self, master, on_send_callback=None, on_chat_selected_callback=None, on_contacts_request_callback=None):
        super().__init__(master)
        self.on_send_callback = on_send_callback
        self.on_chat_selected_callback = on_chat_selected_callback
        self.on_contacts_request_callback = on_contacts_request_callback
        self.selected_jid = None
        self.chats = []
        self.contacts = []
        self.contacts_expanded = False
        self.chat_cards = {}
        
        # Configurações da Janela
        self.title("W.A.N.D. - Histórico de Mensagens")
        # --- CONFIGURAÇÃO DE TAMANHO DA JANELA PREMIUM ---
        window_width = 800
        window_height = 500
        
        # Centralização automática
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x = (screen_width // 2) - (window_width // 2)
        y = (screen_height // 2) - (window_height // 2)
        
        self.geometry(f"{window_width}x{window_height}+{x}+{y}")
        self.overrideredirect(True)
        
        # Transparência para o radius (Estratégia validada no mockup)
        self.bg_color = "#F5F5F7"
        trans_color = "#000001"
        self.wm_attributes("-transparentcolor", trans_color)
        self.configure(fg_color=trans_color)
        self.config(bg=trans_color)
 
        # Container Principal
        self.main_container = ctk.CTkFrame(
            self, 
            fg_color=self.bg_color, 
            corner_radius=25,
            border_width=0
        )
        self.main_container.place(relx=0.5, rely=0.5, relwidth=0.96, relheight=0.94, anchor="center")
        
        # Configuração rígida do Grid do Main Container
        self.main_container.grid_rowconfigure(0, weight=0) # Título: tamanho fixo
        self.main_container.grid_rowconfigure(1, weight=1) # Conteúdo Master-Detail: expande totalmente
        self.main_container.grid_rowconfigure(2, weight=0) # Rodapé: tamanho fixo
        self.main_container.grid_columnconfigure(0, weight=1)
 
        # Barra de Título
        self.title_bar = ctk.CTkFrame(self.main_container, fg_color="transparent", height=22)
        self.title_bar.grid(row=0, column=0, sticky="ew", pady=(5, 5), padx=20)
        
        self.title_label = ctk.CTkLabel(
            self.title_bar, text="W.A.N.D. Chat & Histórico",
            font=ctk.CTkFont(family="Segoe UI Variable Display", size=14, weight="bold"),
            text_color="#1D1D1F"
        )
        self.title_label.place(relx=0.5, rely=0.5, anchor="center")
 
        # --- BOTÕES DE CONTROLE ESTILO MAC (DIREITA) ---
        self.btn_container = ctk.CTkFrame(self.title_bar, fg_color="transparent")
        self.btn_container.place(relx=1.0, rely=0.5, anchor="e")
 
        # Botão Fechar (Vermelho)
        self.btn_close = ctk.CTkButton(
            self.btn_container, text="", width=12, height=12, corner_radius=6,
            fg_color="#FF5F57", hover_color="#E0443E", command=self.withdraw
        )
        self.btn_close.pack(side="right", padx=2)
 
        # Botão Maximizar (Verde)
        self.btn_max = ctk.CTkButton(
            self.btn_container, text="", width=12, height=12, corner_radius=6,
            fg_color="#28C840", hover_color="#1AAB2F", command=self.toggle_maximize
        )
        self.btn_max.pack(side="right", padx=2)
 
        # Botão Minimizar (Amarelo)
        self.btn_min = ctk.CTkButton(
            self.btn_container, text="", width=12, height=12, corner_radius=6,
            fg_color="#FEBC2E", hover_color="#D9A322", command=self.minimize
        )
        self.btn_min.pack(side="right", padx=2)
 
        self.is_maximized = False
 
        # --- BARRA DE RODAPÉ ---
        self.bottom_bar = ctk.CTkFrame(self.main_container, fg_color="transparent", height=22)
        self.bottom_bar.grid(row=2, column=0, sticky="ew", pady=(3, 7), padx=20)
 
        self.lbl_footer = ctk.CTkLabel(
            self.bottom_bar,
            text="W.A.N.D. - WhatsApp Notification Devices",
            font=ctk.CTkFont(family="Segoe UI Variable Text", size=10, weight="bold"),
            text_color="#8E8E93"
        )
        self.lbl_footer.place(relx=0.5, rely=0.5, anchor="center")
 
        # --- ÁREA DE CONTEÚDO MASTER-DETAIL ---
        self.content_area = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.content_area.grid(row=1, column=0, sticky="nsew", padx=15, pady=0)
        self.content_area.grid_rowconfigure(0, weight=1)
        self.content_area.grid_columnconfigure(0, weight=0) # Sidebar: largura fixa
        self.content_area.grid_columnconfigure(1, weight=1) # Chat: expande
        
        # 1. Sidebar (Master)
        self.sidebar_frame = ctk.CTkFrame(self.content_area, fg_color="#EFEFF4", width=230, corner_radius=12)
        self.sidebar_frame.grid(row=0, column=0, sticky="ns", padx=(0, 5), pady=0)
        self.sidebar_frame.grid_propagate(False)
        
        self.lbl_sidebar_title = ctk.CTkLabel(
            self.sidebar_frame, text="Conversas Ativas",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color="#8E8E93"
        )
        self.lbl_sidebar_title.pack(anchor="w", padx=15, pady=(12, 6))
        
        # Botão Dashboard Premium
        self.btn_dashboard = ctk.CTkButton(
            self.sidebar_frame, text="📊 Dashboard",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            fg_color="#007AFF", hover_color="#0059C1", text_color="#FFFFFF",
            height=28, corner_radius=8, cursor="hand2",
            command=self.reset_to_dashboard
        )
        self.btn_dashboard.pack(fill="x", padx=15, pady=(2, 8))
        
        self.sidebar_scroll = ctk.CTkScrollableFrame(self.sidebar_frame, fg_color="transparent", corner_radius=0)
        self.sidebar_scroll.pack(fill="both", expand=True, padx=2, pady=(0, 5))
        
        # 2. Área de Chat (Detail)
        self.chat_frame = ctk.CTkFrame(self.content_area, fg_color="#FFFFFF", corner_radius=12, border_width=1, border_color="#E5E5EA")
        self.chat_frame.grid(row=0, column=1, sticky="nsew", padx=(5, 0), pady=0)
        self.chat_frame.grid_rowconfigure(0, weight=0) # Cabeçalho
        self.chat_frame.grid_rowconfigure(1, weight=1) # Balões de mensagens
        self.chat_frame.grid_rowconfigure(2, weight=0) # Input de digitação
        self.chat_frame.grid_columnconfigure(0, weight=1)
        
        # Cabeçalho do Chat
        self.chat_header = ctk.CTkFrame(self.chat_frame, fg_color="transparent", height=45)
        self.chat_header.grid(row=0, column=0, sticky="ew", padx=15, pady=(10, 5))
        
        self.lbl_active_chat = ctk.CTkLabel(
            self.chat_header, text="Selecione uma conversa",
            font=ctk.CTkFont(family="Segoe UI Variable Display", size=15, weight="bold"),
            text_color="#1D1D1F"
        )
        self.lbl_active_chat.pack(side="left", pady=5)
        
        # Scroll de Mensagens
        self.messages_scroll = ctk.CTkScrollableFrame(self.chat_frame, fg_color="#F5F5F7", corner_radius=10)
        self.messages_scroll.grid(row=1, column=0, sticky="nsew", padx=15, pady=5)
        
        self.messages_container = ctk.CTkFrame(self.messages_scroll, fg_color="transparent")
        self.messages_container.pack(fill="x", side="top")
        
        # Mensagem Inicial
        self.lbl_empty_chat = ctk.CTkLabel(
            self.messages_container, text="Selecione um contato na barra lateral\npara começar a conversar.",
            font=ctk.CTkFont(family="Segoe UI Variable Text", size=13),
            text_color="#8E8E93",
            justify="center"
        )
        self.lbl_empty_chat.pack(expand=True, pady=120)
        
        # Barra de Entrada de Resposta
        self.input_container = ctk.CTkFrame(self.chat_frame, fg_color="transparent")
        # Escondida inicialmente, só é exibida quando um chat for ativado
        self.input_container.grid_forget()
        
        self.entry_message = ctk.CTkEntry(
            self.input_container, placeholder_text="Digite uma mensagem...",
            height=36, corner_radius=18, border_width=1,
            fg_color="#FFFFFF", text_color="#000000", placeholder_text_color="#8E8E93"
        )
        self.entry_message.pack(side="left", fill="x", expand=True, padx=(0, 10))
        
        self.btn_send_chat = ctk.CTkButton(
            self.input_container, text="Enviar", width=70, height=36, corner_radius=18,
            fg_color="#007AFF", hover_color="#0056B3",
            command=self.handle_send_message
        )
        self.btn_send_chat.pack(side="right")
        
        self.entry_message.bind("<Return>", lambda e: self.handle_send_message())
  
        # Movimentação arrastando a barra de título
        self.title_bar.bind("<ButtonPress-1>", self.start_move)
        self.title_bar.bind("<B1-Motion>", self.do_move)
        self.title_label.bind("<ButtonPress-1>", self.start_move)
        self.title_label.bind("<B1-Motion>", self.do_move)
  
        # Maximizar com duplo clique na barra de título
        self.title_bar.bind("<Double-Button-1>", lambda event: self.toggle_maximize())
        self.title_label.bind("<Double-Button-1>", lambda event: self.toggle_maximize())

        # Exibe tela de carregamento na sidebar até o primeiro get_chats responder
        self.show_sidebar_loading()

    def show_sidebar_loading(self):
        """Mostra carregamento na barra lateral."""
        for widget in self.sidebar_scroll.winfo_children():
            widget.destroy()
        lbl_load = ctk.CTkLabel(
            self.sidebar_scroll, text="Carregando contatos...",
            font=ctk.CTkFont(size=11), text_color="#8E8E93"
        )
        lbl_load.pack(pady=20)

    def show_loading_screen(self):
        """Exibe tela de carregamento na area de mensagens."""
        for widget in self.messages_container.winfo_children():
            widget.destroy()
        lbl_loading = ctk.CTkLabel(
            self.messages_container, text="Carregando mensagens...",
            font=ctk.CTkFont(family="Segoe UI Variable Text", size=13, weight="bold"),
            text_color="#007AFF"
        )
        lbl_loading.pack(pady=120)

    def bind_click_to_widget(self, widget, jid):
        """Associa clique esquerdo para selecionar um chat."""
        widget.bind("<Button-1>", lambda e: self.select_chat(jid))

    def ensure_containers_exist(self):
        """Garante que os containers persistentes da barra lateral existam e estejam limpos de carregadores."""
        if not hasattr(self, 'chats_container') or not self.chats_container.winfo_exists():
            # Limpa qualquer carregador temporário
            for widget in self.sidebar_scroll.winfo_children():
                widget.destroy()
                
            self.chats_container = ctk.CTkFrame(self.sidebar_scroll, fg_color="transparent")
            self.chats_container.pack(fill="x")
            
            self.sidebar_separator = ctk.CTkFrame(self.sidebar_scroll, height=1, fg_color="#E5E5EA")
            self.sidebar_separator.pack(fill="x", pady=(15, 10), padx=10)
            
            self.contacts_header_frame = ctk.CTkFrame(self.sidebar_scroll, fg_color="transparent", height=28, cursor="hand2")
            self.contacts_header_frame.pack(fill="x", padx=5)
            
            arrow = "▲" if self.contacts_expanded else "▼"
            self.lbl_contacts_header = ctk.CTkLabel(
                self.contacts_header_frame, text=f"{arrow} Contatos Sincronizados",
                font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
                text_color="#8E8E93"
            )
            self.lbl_contacts_header.pack(side="left", padx=10)
            
            self.contacts_header_frame.bind("<Button-1>", lambda e: self.toggle_contacts())
            self.lbl_contacts_header.bind("<Button-1>", lambda e: self.toggle_contacts())
            
            self.contacts_container = ctk.CTkFrame(self.sidebar_scroll, fg_color="transparent")
            if self.contacts_expanded:
                self.contacts_container.pack(fill="x")

    def update_chats_list(self, chats_list):
        """Atualiza apenas o container de conversas ativas na sidebar."""
        import time
        t0 = time.perf_counter()
        
        self.chats = chats_list
        self.ensure_containers_exist()
        
        # Limpa apenas os widgets dentro do container de chats
        for widget in self.chats_container.winfo_children():
            widget.destroy()
            
        # Limpa do self.chat_cards apenas os JIDs que pertencem às conversas ativas
        active_jids = {chat.get("jid") for chat in chats_list}
        self.chat_cards = {jid: card for jid, card in self.chat_cards.items() if jid not in active_jids}
        
        if not chats_list:
            lbl_empty = ctk.CTkLabel(
                self.chats_container, text="Nenhuma conversa ativa",
                font=ctk.CTkFont(size=11), text_color="#8E8E93"
            )
            lbl_empty.pack(pady=20)
            print(f"[UI DEBUG] Chats vazios renderizados em {(time.perf_counter() - t0)*1000:.2f}ms")
            return
            
        for chat in chats_list:
            jid = chat.get("jid")
            name = chat.get("name", "Desconhecido")
            last_msg = chat.get("lastMessage", {})
            last_text = last_msg.get("text", "")
            last_ts = last_msg.get("timestamp", 0)
            
            if len(last_text) > 22:
                last_text = last_text[:22] + "..."
                
            time_str = ""
            if last_ts:
                time_str = datetime.datetime.fromtimestamp(last_ts/1000).strftime("%H:%M")
                
            is_selected = (self.selected_jid == jid)
            bg_color = "#D1D1D6" if is_selected else "#FFFFFF"
            border_color = "#007AFF" if is_selected else "#E5E5EA"
            
            card = ctk.CTkFrame(
                self.chats_container, fg_color=bg_color,
                corner_radius=8, border_width=1, border_color=border_color,
                height=60, cursor="hand2"
            )
            card.pack(fill="x", pady=4, padx=5)
            card.pack_propagate(False)
            
            self.bind_click_to_widget(card, jid)
            
            lbl_name = ctk.CTkLabel(
                card, text=name,
                font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
                text_color="#000000"
            )
            lbl_name.place(x=10, y=8)
            self.bind_click_to_widget(lbl_name, jid)
            
            lbl_msg = ctk.CTkLabel(
                card, text=last_text,
                font=ctk.CTkFont(family="Segoe UI Variable Text", size=11),
                text_color="#3A3A3C"
            )
            lbl_msg.place(x=10, y=28)
            self.bind_click_to_widget(lbl_msg, jid)
            
            lbl_time = ctk.CTkLabel(
                card, text=time_str,
                font=ctk.CTkFont(size=9), text_color="#8E8E93"
            )
            lbl_time.place(relx=1.0, y=8, x=-10, anchor="ne")
            self.bind_click_to_widget(lbl_time, jid)
            
            self.chat_cards[jid] = card
            
        print(f"[UI DEBUG] Chats atualizados com sucesso em {(time.perf_counter() - t0)*1000:.2f}ms")

    def update_contacts_list(self, contacts_list):
        """Atualiza o container de contatos sincronizados na sidebar (limite de 50 para performance)."""
        import time
        t0 = time.perf_counter()
        
        self.contacts = contacts_list
        self.ensure_containers_exist()
        
        # Limpa apenas os widgets do container de contatos
        for widget in self.contacts_container.winfo_children():
            widget.destroy()
            
        # Limpa do self.chat_cards apenas os JIDs que pertencem aos contatos sincronizados
        contact_jids = {c.get("jid") for c in contacts_list}
        self.chat_cards = {jid: card for jid, card in self.chat_cards.items() if jid not in contact_jids}
        
        if not contacts_list:
            lbl_no_contacts = ctk.CTkLabel(
                self.contacts_container, text="Nenhum contato encontrado",
                font=ctk.CTkFont(size=11), text_color="#8E8E93"
            )
            lbl_no_contacts.pack(pady=10)
            print(f"[UI DEBUG] Contatos vazios renderizados em {(time.perf_counter() - t0)*1000:.2f}ms")
            return

        # Limita a exibição a 50 contatos para manter performance 60 FPS fluida
        max_display = 50
        displayed_contacts = contacts_list[:max_display]
        
        for contact in displayed_contacts:
            jid = contact.get("jid")
            name = contact.get("name", "Contato")
            
            is_selected = (self.selected_jid == jid)
            bg_color = "#D1D1D6" if is_selected else "#FFFFFF"
            border_color = "#007AFF" if is_selected else "#E5E5EA"
            
            card = ctk.CTkFrame(
                self.contacts_container, fg_color=bg_color,
                corner_radius=8, border_width=1, border_color=border_color,
                height=40, cursor="hand2"
            )
            card.pack(fill="x", pady=3, padx=5)
            card.pack_propagate(False)
            
            self.bind_click_to_widget(card, jid)
            
            # Avatar circular com inicial
            avatar_frame = ctk.CTkFrame(card, fg_color="#EFEFF4", width=24, height=24, corner_radius=12)
            avatar_frame.place(x=8, y=8)
            avatar_frame.pack_propagate(False)
            
            lbl_avatar = ctk.CTkLabel(
                avatar_frame, text=name[0].upper() if name else "?",
                font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"),
                text_color="#8E8E93"
            )
            lbl_avatar.pack(expand=True)
            
            self.bind_click_to_widget(avatar_frame, jid)
            self.bind_click_to_widget(lbl_avatar, jid)
            
            # Nome do contato
            lbl_name = ctk.CTkLabel(
                card, text=name,
                font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
                text_color="#000000"
            )
            lbl_name.place(x=40, y=8)
            self.bind_click_to_widget(lbl_name, jid)
            
            self.chat_cards[jid] = card

        # Se houver mais contatos, adiciona um aviso premium e amigável no final da lista
        if len(contacts_list) > max_display:
            lbl_more = ctk.CTkLabel(
                self.contacts_container, 
                text=f"Mostrando 50 de {len(contacts_list)} contatos.\nUse a busca para filtrar.",
                font=ctk.CTkFont(family="Segoe UI Variable Text", size=10, weight="bold"), 
                text_color="#8E8E93",
                justify="center"
            )
            lbl_more.pack(pady=10)
            
        print(f"[UI DEBUG] Contatos atualizados em {(time.perf_counter() - t0)*1000:.2f}ms")

    def toggle_contacts(self):
        """Expande ou recolhe a seção de contatos instantaneamente (0ms) usando pack_forget/pack."""
        import time
        t0 = time.perf_counter()
        
        self.contacts_expanded = not self.contacts_expanded
        self.ensure_containers_exist()
        
        arrow = "▲" if self.contacts_expanded else "▼"
        self.lbl_contacts_header.configure(text=f"{arrow} Contatos Sincronizados")
        
        if self.contacts_expanded:
            self.contacts_container.pack(fill="x")
            if not self.contacts:
                # Mostra estado de carregamento inicial
                lbl_no_contacts = ctk.CTkLabel(
                    self.contacts_container, text="Carregando contatos...",
                    font=ctk.CTkFont(size=11), text_color="#8E8E93"
                )
                lbl_no_contacts.pack(pady=10)
                
                if self.on_contacts_request_callback:
                    self.on_contacts_request_callback()
        else:
            self.contacts_container.pack_forget()
            
        print(f"[UI DEBUG] Contatos toggled em {(time.perf_counter() - t0)*1000:.2f}ms")

    def select_chat(self, jid):
        """Seleciona um contato da sidebar, mudando o destaque visual e invocando a callback."""
        if self.selected_jid == jid:
            return
            
        self.selected_jid = jid
        self.show_loading_screen()
        
        # Atualiza título do cabeçalho
        chat_name = "Conversa"
        found = False
        for chat in self.chats:
            if chat.get("jid") == jid:
                chat_name = chat.get("name", "Conversa")
                found = True
                break
        if not found:
            for contact in self.contacts:
                if contact.get("jid") == jid:
                    chat_name = contact.get("name", "Conversa")
                    break
        self.lbl_active_chat.configure(text=chat_name)
        
        # Exibe a barra de entrada
        self.input_container.grid(row=2, column=0, sticky="ew", padx=15, pady=(5, 10))
        self.entry_message.delete(0, "end")
        self.entry_message.focus_set()
        
        # Atualiza destaque dos cards na barra lateral
        for card_jid, card in self.chat_cards.items():
            if card_jid == jid:
                card.configure(fg_color="#D1D1D6", border_color="#007AFF")
            else:
                card.configure(fg_color="#FFFFFF", border_color="#E5E5EA")
                
        # Aciona callback
        if self.on_chat_selected_callback:
            self.on_chat_selected_callback(jid)

    def reset_to_dashboard(self):
        """Reseta a visualização para a tela de mensagens recentes (Dashboard)."""
        self.selected_jid = None
        self.show_loading_screen()
        
        # Limpa o destaque de todos os cards
        for card_jid, card in self.chat_cards.items():
            card.configure(fg_color="#FFFFFF", border_color="#E5E5EA")
            
        # Aciona callback com None para carregar o histórico recente
        if self.on_chat_selected_callback:
            self.on_chat_selected_callback(None)

    def update_chat_messages(self, jid, messages):
        """Renderiza a lista de mensagens no corpo do chat."""
        if self.selected_jid != jid:
            return
            
        # Reseta a barra de rolagem para o topo antes de limpar os widgets,
        # evitando coordenadas de scroll fantasmas e telas cinzas vazias
        self.messages_scroll._parent_canvas.yview_moveto(0.0)
            
        for widget in self.messages_container.winfo_children():
            widget.destroy()
            
        if not messages:
            lbl_empty = ctk.CTkLabel(
                self.messages_container, text="Nenhuma mensagem nesta conversa.",
                font=ctk.CTkFont(size=12), text_color="#8E8E93"
            )
            lbl_empty.pack(pady=120)
            return
            
        for msg in messages:
            self.create_message_balloon(msg)
            
        self.update_idletasks()
        
        # Agendamento assíncrono de 50ms para dar tempo ao CustomTkinter de recalcular
        # a scrollregion real baseada na nova altura e rolar com precisão para a base
        self.after(50, lambda: self.messages_scroll._parent_canvas.yview_moveto(1.0))

    def create_message_balloon(self, msg):
        """Desenha balões de chat realistas à esquerda (recebidas) ou direita (enviadas)."""
        from_me = msg.get("fromMe", False)
        text = msg.get("text", "")
        ts = msg.get("timestamp", 0)
        
        time_str = datetime.datetime.fromtimestamp(ts/1000).strftime("%H:%M") if ts else ""
        
        row_frame = ctk.CTkFrame(self.messages_container, fg_color="transparent")
        row_frame.pack(fill="x", padx=10, pady=4)
        
        bg_color = "#DCF8C6" if from_me else "#FFFFFF"
        text_color = "#000000"
        
        balloon = ctk.CTkFrame(
            row_frame, fg_color=bg_color,
            corner_radius=10, border_width=1, border_color="#E5E5EA"
        )
        balloon.pack(side="right" if from_me else "left")
        
        # Se for mensagem curta de uma unica linha, adiciona padding de caracteres para evitar sobreposicao com o horario
        display_text = text
        if "\n" not in text and len(text) < 20:
            display_text = text + "          "
            
        # Se for chat de grupo (@g.us) e mensagem recebida, exibe o nome do remetente no topo do balão em azul
        is_group = self.selected_jid and self.selected_jid.endswith("@g.us")
        sender_name = msg.get("senderName", "")
        
        if is_group and not from_me and sender_name:
            lbl_sender = ctk.CTkLabel(
                balloon, text=sender_name,
                font=ctk.CTkFont(family="Segoe UI Variable Text", size=11, weight="bold"),
                text_color="#007AFF", # Azul clássico do iOS
                justify="left"
            )
            lbl_sender.pack(anchor="w", padx=(12, 12), pady=(6, 0))
            
            lbl_text = ctk.CTkLabel(
                balloon, text=display_text,
                font=ctk.CTkFont(family="Segoe UI Variable Text", size=13),
                text_color=text_color, justify="left",
                wraplength=350
            )
            lbl_text.pack(anchor="w", padx=(12, 12), pady=(3, 18))
        else:
            lbl_text = ctk.CTkLabel(
                balloon, text=display_text,
                font=ctk.CTkFont(family="Segoe UI Variable Text", size=13),
                text_color=text_color, justify="left",
                wraplength=350
            )
            lbl_text.pack(anchor="w", padx=(12, 12), pady=(8, 18))
            
        lbl_time = ctk.CTkLabel(
            balloon, text=time_str,
            font=ctk.CTkFont(size=9), text_color="#8E8E93", height=9
        )
        lbl_time.place(relx=1.0, rely=1.0, x=-8, y=-5, anchor="se")

    def handle_send_message(self):
        """Envia a mensagem digitada e adiciona o balão local instantâneo na UI."""
        text = self.entry_message.get().strip()
        if not text or not self.selected_jid:
            return
            
        if self.on_send_callback:
            self.on_send_callback(self.selected_jid, text)
            
        local_msg = {
            "fromMe": True,
            "text": text,
            "timestamp": int(datetime.datetime.now().timestamp() * 1000)
        }
        
        children = self.messages_container.winfo_children()
        if len(children) == 1 and isinstance(children[0], ctk.CTkLabel) and "Nenhuma mensagem" in children[0].cget("text"):
            children[0].destroy()
            
        self.create_message_balloon(local_msg)
        self.entry_message.delete(0, "end")
        self.update_idletasks()
        self.messages_scroll._parent_canvas.yview_moveto(1.0)

    def handle_incoming_message(self, data):
        """Trata o recebimento de mensagens em tempo real na janela ativa."""
        remote_jid = data.get("remoteJid", "")
        alternate_jid = data.get("alternateJid", "")
        
        if self.selected_jid == remote_jid or (alternate_jid and self.selected_jid == alternate_jid):
            from_me = data.get("fromMe", False) or data.get("from") == "Você"
            
            # Se a mensagem for nossa, verifica se já foi desenhada pelo feedback instantâneo local
            if from_me:
                children = self.messages_container.winfo_children()
                if children:
                    last_widget = children[-1]
                    balloon_frame = None
                    for child in last_widget.winfo_children():
                        if isinstance(child, ctk.CTkFrame):
                            balloon_frame = child
                            break
                    if balloon_frame:
                        lbl_text = None
                        for b_child in balloon_frame.winfo_children():
                            # Procura pelo widget do texto da mensagem (que tem wraplength=350)
                            if isinstance(b_child, ctk.CTkLabel) and b_child.cget("wraplength") == 350:
                                lbl_text = b_child
                                break
                        if lbl_text:
                            # Compara o texto na tela (removendo preenchimentos extras de linha única) com o novo
                            last_text = lbl_text.cget("text").rstrip()
                            new_text = data.get("text", "")
                            if last_text == new_text:
                                return # Ignora a duplicação!
            
            children = self.messages_container.winfo_children()
            if len(children) == 1 and isinstance(children[0], ctk.CTkLabel) and "Nenhuma mensagem" in children[0].cget("text"):
                children[0].destroy()
                
            self.create_message_balloon({
                "fromMe": from_me,
                "text": data.get("text", ""),
                "timestamp": data.get("timestamp", 0),
                "senderName": data.get("from", "")
            })
            self.update_idletasks()
            self.messages_scroll._parent_canvas.yview_moveto(1.0)

    def update_history(self, data):
        """Preenche a tela da direita com o feed de mensagens recentes se nenhum chat estiver selecionado."""
        if self.selected_jid is not None:
            return
            
        for widget in self.messages_container.winfo_children():
            widget.destroy()
            
        self.lbl_active_chat.configure(text="Mensagens Recentes")
        self.input_container.grid_forget()
        
        if not data:
            lbl_empty = ctk.CTkLabel(
                self.messages_container, text="Nenhuma mensagem recente encontrada.",
                font=ctk.CTkFont(size=12), text_color="#8E8E93"
            )
            lbl_empty.pack(pady=120)
            return
            
        # Renderiza a lista de mensagens recentes como cards clicáveis
        for msg in data:
            self.create_feed_card(msg)
            
        self.update_idletasks()
        self.messages_scroll._parent_canvas.yview_moveto(0)

    def create_feed_card(self, msg):
        """Cria um card premium de feed na área central, que ao ser clicado abre o chat específico do contato."""
        jid = msg.get("remoteJid")
        sender_name = msg.get("senderName", "Desconhecido")
        receiver_name = msg.get("receiverName", "")
        text = msg.get("text", "")
        ts = msg.get("timestamp", 0)
        from_me = msg.get("fromMe", 0) == 1 or msg.get("fromMe", False)
        
        time_str = datetime.datetime.fromtimestamp(ts/1000).strftime("%H:%M") if ts else ""
        
        # Nome formatado
        display_name = f"{sender_name} ➔ Você" if not from_me else f"Você ➔ {receiver_name or 'Contato'}"
        
        # Card do Feed (clicável)
        card = ctk.CTkFrame(
            self.messages_container, fg_color="#FFFFFF",
            corner_radius=12, border_width=1, border_color="#E5E5EA",
            cursor="hand2"
        )
        card.pack(fill="x", padx=15, pady=6)
        
        # Bind do clique no card inteiro para abrir a conversa
        card.bind("<Button-1>", lambda e: self.select_chat(jid))
        
        # Título / Remetente
        lbl_title = ctk.CTkLabel(
            card, text=display_name,
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            text_color="#007AFF" if not from_me else "#8E8E93"
        )
        lbl_title.pack(anchor="w", padx=15, pady=(10, 0))
        lbl_title.bind("<Button-1>", lambda e: self.select_chat(jid))
        
        # Texto da Mensagem
        lbl_text = ctk.CTkLabel(
            card, text=text,
            font=ctk.CTkFont(family="Segoe UI Variable Text", size=13),
            text_color="#1D1D1F", justify="left",
            wraplength=480
        )
        lbl_text.pack(anchor="w", padx=15, pady=(5, 12))
        lbl_text.bind("<Button-1>", lambda e: self.select_chat(jid))
        
        # Hora no canto inferior direito
        lbl_time = ctk.CTkLabel(
            card, text=time_str,
            font=ctk.CTkFont(size=9), text_color="#8E8E93"
        )
        lbl_time.place(relx=1.0, rely=1.0, x=-12, y=-6, anchor="se")

    def start_move(self, event):
        self.x = event.x
        self.y = event.y

    def do_move(self, event):
        if self.is_maximized: return
        deltax = event.x - self.x
        deltay = event.y - self.y
        x = self.winfo_x() + deltax
        y = self.winfo_y() + deltay
        self.geometry(f"+{x}+{y}")

    def toggle_maximize(self):
        self.show_loading_screen()
        self.update_idletasks()

        if not self.is_maximized:
            self.old_geometry = self.geometry()
            sw = self.winfo_screenwidth()
            sh = self.winfo_screenheight()
            
            self.configure(fg_color=self.bg_color)
            self.config(bg=self.bg_color)
            self.update_idletasks()
            
            self.geometry(f"{sw}x{sh-40}+0+0")
            self.main_container.configure(corner_radius=0)
            self.main_container.place(relwidth=1.0, relheight=1.0)
            
            self.update_idletasks()
            self.is_maximized = True
            
            if self.selected_jid and self.on_chat_selected_callback:
                self.on_chat_selected_callback(self.selected_jid)
        else:
            self.geometry(self.old_geometry)
            self.main_container.configure(corner_radius=25)
            self.main_container.place(relwidth=0.96, relheight=0.94)
            
            self.update_idletasks()
            
            self.configure(fg_color="#000001")
            self.config(bg="#000001")
            self.update_idletasks()
            
            self.is_maximized = False
            
            if self.selected_jid and self.on_chat_selected_callback:
                self.on_chat_selected_callback(self.selected_jid)

    def minimize(self):
        self.overrideredirect(False)
        self.iconify()
        self.bind("<FocusIn>", self.on_restore)

    def on_restore(self, event):
        if self.state() == "normal":
            self.overrideredirect(True)
            self.unbind("<FocusIn>")
