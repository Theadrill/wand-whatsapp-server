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
    def __init__(self, master, history_data=None, on_send_callback=None):
        super().__init__(master)
        self.on_send_callback = on_send_callback
        
        # Configurações da Janela
        self.title("W.A.N.D. - Histórico")
        # --- CONFIGURAÇÃO DE TAMANHO DA JANELA ---
        window_width = 450
        window_height = 450
        
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
        self.main_container.place(relx=0.5, rely=0.5, relwidth=0.90, relheight=0.90, anchor="center")
        
        # Configuração rígida do Grid
        self.main_container.grid_rowconfigure(0, weight=0) # Título: tamanho fixo
        self.main_container.grid_rowconfigure(1, weight=1) # Conteúdo: expande totalmente
        self.main_container.grid_rowconfigure(2, weight=0) # Rodapé: tamanho fixo
        self.main_container.grid_columnconfigure(0, weight=1)
 
        # Barra de Título
        self.title_bar = ctk.CTkFrame(self.main_container, fg_color="transparent", height=22)
        self.title_bar.grid(row=0, column=0, sticky="ew", pady=(5, 5), padx=20)
        
        self.title_label = ctk.CTkLabel(
            self.title_bar, text="Histórico de Notificações",
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
 
        # --- BARRA DE RODAPÉ (Estilo Barra de Título) ---
        self.bottom_bar = ctk.CTkFrame(self.main_container, fg_color="transparent", height=22)
        self.bottom_bar.grid(row=2, column=0, sticky="ew", pady=(3, 7), padx=20)
 
        self.lbl_footer = ctk.CTkLabel(
            self.bottom_bar,
            text="W.A.N.D. - WhatsApp Notification Devices",
            font=ctk.CTkFont(family="Segoe UI Variable Text", size=10, weight="bold"),
            text_color="#8E8E93"
        )
        self.lbl_footer.place(relx=0.5, rely=0.5, anchor="center")
 
        # Área de Scroll (Inicialmente NÃO gridada/oculta por padrão)
        self.scrollable_frame = ctk.CTkScrollableFrame(
            self.main_container, fg_color="transparent", corner_radius=0
        )
 
        # Container interno para as mensagens (fixado no topo)
        self.messages_container = ctk.CTkFrame(self.scrollable_frame, fg_color="transparent")
        self.messages_container.pack(fill="x", side="top")
 
        self.update_history(history_data)
 
        # Movimentação
        self.title_bar.bind("<ButtonPress-1>", self.start_move)
        self.title_bar.bind("<B1-Motion>", self.do_move)
        self.title_label.bind("<ButtonPress-1>", self.start_move)
        self.title_label.bind("<B1-Motion>", self.do_move)
 
        # Maximizar com duplo clique na barra de título
        self.title_bar.bind("<Double-Button-1>", lambda event: self.toggle_maximize())
        self.title_label.bind("<Double-Button-1>", lambda event: self.toggle_maximize())

 
    def show_loading_screen(self):
        """Exibe a tela de carregamento centralizada diretamente na janela principal, com o scroll oculto"""
        if hasattr(self, "loading_frame") and self.loading_frame:
            try:
                self.loading_frame.destroy()
            except:
                pass
                
        # Oculta o frame de scroll se ele estiver visível
        self.scrollable_frame.grid_remove()
        
        # Cria um container centralizado e transparente para a animação do texto
        self.loading_frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.loading_frame.place(relx=0.5, rely=0.53, anchor="center")
        
        lbl_loading = ctk.CTkLabel(
            self.loading_frame, text="Carregando mensagens...",
            font=ctk.CTkFont(family="Segoe UI Variable Text", size=14, weight="bold"),
            text_color="#007AFF"
        )
        lbl_loading.pack(pady=(0, 5))
        
        lbl_loading_sub = ctk.CTkLabel(
            self.loading_frame, text="Sincronizando com o servidor W.A.N.D.",
            font=ctk.CTkFont(family="Segoe UI Variable Text", size=11),
            text_color="#8E8E93"
        )
        lbl_loading_sub.pack(pady=0)

    def update_history(self, data):
        self.current_data = data # Guarda os dados atuais para redimensionamento
            
        if data is None:
            self.show_loading_screen()
            return
            
        if not data:
            # Destrói a tela de carregamento se existir
            if hasattr(self, "loading_frame") and self.loading_frame:
                try:
                    self.loading_frame.destroy()
                except:
                    pass
                self.loading_frame = None
                
            # Limpa e exibe a mensagem de lista vazia dentro do scroll
            for widget in self.messages_container.winfo_children():
                widget.destroy()
            lbl_empty = ctk.CTkLabel(
                self.messages_container, text="Nenhuma mensagem recente.",
                font=ctk.CTkFont(size=13), text_color="#8E8E93"
            )
            lbl_empty.pack(pady=20)
            
            # Exibe o scrollable frame com a mensagem vazia
            self.scrollable_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=0)
            return

        # --- REVELAÇÃO NATIVA (FADE-IN DIGITAL) ---
        # 1. Limpa o container de mensagens (enquanto o scroll está ocultado/sem grid)
        for widget in self.messages_container.winfo_children():
            widget.destroy()
        
        # 2. Constrói todos os cards de forma oculta na memória
        for msg in data:
            self.create_message_card(msg, parent=self.messages_container)
            
        # 3. Destrói o frame de carregamento
        if hasattr(self, "loading_frame") and self.loading_frame:
            try:
                self.loading_frame.destroy()
            except:
                pass
            self.loading_frame = None
            
        # 4. Envia o scrollable frame para a tela (grid ativa o motor geométrico do Tkinter)
        self.scrollable_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=0)
        
        # 5. Força o redesenho síncrono dos cards prontos em frações de milissegundo
        self.update_idletasks()
            
        # Garante que o scroll suba ao topo ao carregar a lista
        self.scrollable_frame._parent_canvas.yview_moveto(0)

    def _adjust_scrollbar_visibility(self):
        """Esconde ou mostra a barra de scroll dependendo do tamanho do conteúdo"""
        try:
            # Bbox "all" retorna (x1, y1, x2, y2) de todo o conteúdo do canvas interno
            bbox = self.scrollable_frame._parent_canvas.bbox("all")
            if not bbox: return
            
            content_height = bbox[3]
            frame_height = self.scrollable_frame._parent_canvas.winfo_height()

            if content_height <= frame_height:
                # Esconde a barra de scroll interna do CTkScrollableFrame
                self.scrollable_frame._scrollbar.grid_forget()
            else:
                # self.scrollable_frame._scrollbar.grid(row=0, column=1, sticky="ns")
                pass
        except:
            pass

    def add_message_to_top(self, msg):
        """Adiciona uma nova mensagem no topo do histórico de forma dinâmica e sem redesenhar toda a tela"""
        if self.current_data is None:
            self.current_data = []
            
        # Evita duplicidade (caso a mensagem já tenha sido adicionada localmente ou venha do websocket)
        for existing in self.current_data[:3]:
            if (existing.get("text") == msg.get("text") and 
                existing.get("remoteJid") == msg.get("remoteJid") and 
                abs(existing.get("timestamp", 0) - msg.get("timestamp", 0)) < 5000):
                return
                
        self.current_data.insert(0, msg)
        
        # Se havia a mensagem de "Nenhuma mensagem recente", remove ela
        children = self.messages_container.winfo_children()
        if len(children) == 1 and isinstance(children[0], ctk.CTkLabel) and children[0].cget("text") == "Nenhuma mensagem recente.":
            children[0].destroy()
            
        # Cria o card e insere no topo
        self.create_message_card(msg, parent=self.messages_container, prepend=True)
        
        # Garante que o scroll suba ao topo para ver a nova mensagem
        self.scrollable_frame._parent_canvas.yview_moveto(0)
        self._adjust_scrollbar_visibility()

    def create_message_card(self, msg, parent=None, is_reply_mode=False, prepend=False):
        # Se não houver pai definido, usa o container de mensagens padrão
        target = parent if parent else self.messages_container
        
        card = ctk.CTkFrame(
            target, fg_color="#FFFFFF",
            corner_radius=12, border_width=1, border_color="#E5E5EA"
        )
        
        if prepend:
            slaves = target.pack_slaves()
            first_packed_child = None
            for slave in slaves:
                if slave != card:
                    first_packed_child = slave
                    break
            if first_packed_child:
                card.pack(fill="x", pady=5, padx=5, before=first_packed_child)
            else:
                card.pack(fill="x", pady=5, padx=5)
        else:
            card.pack(fill="x", pady=5, padx=5)

        # Se não estiver no modo resposta, permite clicar para responder
        if not is_reply_mode:
            card.configure(cursor="hand2")
            card.bind("<Button-1>", lambda e: self.show_reply_view(msg))

        sender_name = msg.get("senderName", "Desconhecido")
        receiver_name = msg.get("receiverName", "")
        display_name = f"{sender_name} ---> {receiver_name}" if receiver_name else sender_name

        lbl_from = ctk.CTkLabel(
            card, text=display_name,
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            text_color="#000000"
        )
        lbl_from.pack(anchor="w", padx=15, pady=(10, 0))
        if not is_reply_mode: lbl_from.bind("<Button-1>", lambda e: self.show_reply_view(msg))

        lbl_text = ctk.CTkLabel(
            card, text=msg.get("text", ""),
            font=ctk.CTkFont(family="Segoe UI Variable Text", size=13),
            text_color="#3A3A3C", 
            justify="left"
        )
        # Quebra de linha dinâmica segura baseada na largura da janela
        width = self.winfo_width()
        if width < 100:
            width = 450  # Largura padrão caso a janela não esteja mapeada
        lbl_text.configure(wraplength=width - 80)
        lbl_text.pack(anchor="w", padx=15, pady=(5, 10))
        if not is_reply_mode: lbl_text.bind("<Button-1>", lambda e: self.show_reply_view(msg))

        # Formatação simples da data (se disponível)
        ts = msg.get("timestamp", 0)
        time_str = datetime.datetime.fromtimestamp(ts/1000).strftime("%H:%M") if ts else "--:--"
        
        lbl_time = ctk.CTkLabel(
            card, text=time_str, font=ctk.CTkFont(size=10), text_color="#8E8E93"
        )
        lbl_time.place(relx=1.0, rely=1.0, x=-10, y=-5, anchor="se")

    def show_reply_view(self, msg):
        """Muda a interface para o modo de resposta de uma mensagem específica"""
        # Esconde a lista original (remove do grid temporariamente)
        self.scrollable_frame.grid_remove()
        
        # Container centralizado verticalmente na janela principal
        self.reply_view = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.reply_view.place(relx=0.5, rely=0.45, relwidth=0.9, anchor="center")
        
        # Card da mensagem em destaque
        self.create_message_card(msg, parent=self.reply_view, is_reply_mode=True)
        
        # Campo de Input estilo Mac/iOS
        self.reply_input = ctk.CTkEntry(
            self.reply_view, 
            placeholder_text="Escreva uma resposta...",
            height=40,
            corner_radius=20,
            border_width=1,
            fg_color="#FFFFFF",
            text_color="#000000",
            placeholder_text_color="#8E8E93"
        )
        self.reply_input.pack(fill="x", padx=15, pady=20)
        self.reply_input.focus_set()
        
        # Botão de Enviar
        self.btn_send = ctk.CTkButton(
            self.reply_view, text="Enviar Resposta",
            height=35, corner_radius=18, fg_color="#007AFF", hover_color="#0056B3",
            command=lambda: self.handle_send(msg)
        )
        self.btn_send.pack(pady=(0, 10), padx=15, fill="x")

        # Atalho: Enter para enviar
        self.reply_input.bind("<Return>", lambda e: self.handle_send(msg))

        # Botão Voltar
        self.btn_back = ctk.CTkButton(
            self.reply_view, text="← Voltar",
            fg_color="transparent", text_color="#8E8E93", hover_color="#E5E5EA",
            width=100, height=25,
            command=self.back_to_list
        )
        self.btn_back.pack(pady=5)
        
        self._adjust_scrollbar_visibility()

    def back_to_list(self):
        """Volta para a visualização de lista"""
        if hasattr(self, 'reply_view'):
            self.reply_view.destroy()
        # Restaura o scroll exibindo a lista original intacta que estava apenas oculta
        self.scrollable_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=0)

    def handle_send(self, msg):
        """Coleta o texto, dispara o callback de envio e adiciona a resposta no topo do histórico sem redesenhar"""
        text = self.reply_input.get().strip()
        if text and self.on_send_callback:
            remoteJid = msg.get("remoteJid")
            if remoteJid:
                # Chama o callback (main.py cuidará do WebSocket)
                self.on_send_callback(remoteJid, text)
                
                # Pega o nome do contato a partir da mensagem original
                contact_name = msg.get("senderName") if msg.get("fromMe") == 0 else msg.get("receiverName", "Desconhecido")
                
                # Prepara o objeto da mensagem enviada
                reply_msg = {
                    "remoteJid": remoteJid,
                    "senderName": "Você",
                    "receiverName": contact_name,
                    "text": text,
                    "timestamp": int(datetime.datetime.now().timestamp() * 1000),
                    "fromMe": 1
                }
                
                # Adiciona no topo do histórico dinamicamente
                self.add_message_to_top(reply_msg)
                
                # Volta para a lista após enviar
                self.back_to_list()

    def start_move(self, event):
        self.x = event.x
        self.y = event.y

    def do_move(self, event):
        if self.is_maximized: return # Impede mover se estiver maximizado
        deltax = event.x - self.x
        deltay = event.y - self.y
        x = self.winfo_x() + deltax
        y = self.winfo_y() + deltay
        self.geometry(f"+{x}+{y}")

    def toggle_maximize(self):
        # Exibe a cortina de carregamento de imediato para ocultar o processo geométrico
        self.show_loading_screen()
        self.update_idletasks()  # Força o desenho síncrono da cortina na tela

        if not self.is_maximized:
            # Salva posição original para restaurar depois
            self.old_geometry = self.geometry()
            # Pega tamanho da tela
            sw = self.winfo_screenwidth()
            sh = self.winfo_screenheight()
            
            # 1. Altera a cor de fundo do Toplevel para a cor sólida ANTES de expandir a janela (evita flash preto)
            self.configure(fg_color=self.bg_color)
            self.config(bg=self.bg_color)
            self.update_idletasks()
            
            # 2. Altera a geometria e o posicionamento do container (já preenchido com a cor de fundo perfeita)
            self.geometry(f"{sw}x{sh-40}+0+0")
            self.main_container.configure(corner_radius=0)
            self.main_container.place(relwidth=1.0, relheight=1.0)
            
            # 3. FORÇA O REDESENHO SÍNCRONO DA JANELA MAXIMIZADA E SEUS COMPONENTES IMEDIATAMENTE
            self.update_idletasks()
            self.is_maximized = True
            
            # 4. Reconstrói os cards por trás da cortina já nas novas proporções
            self.after(50, lambda: self.update_history(self.current_data))
            self.after(100, self._adjust_scrollbar_visibility)
        else:
            # 1. Restaura primeiro a geometria e arredondamento mantendo a cor sólida ativa
            self.geometry(self.old_geometry)
            self.main_container.configure(corner_radius=25)
            self.main_container.place(relwidth=0.90, relheight=0.90)
            
            # 2. Sincroniza o redimensionamento físico síncrono para o tamanho menor
            self.update_idletasks()
            
            # 3. Reativa a transparência do Toplevel aplicando a máscara (#000001) com a janela já reduzida
            self.configure(fg_color="#000001")
            self.config(bg="#000001")
            self.update_idletasks()
            
            self.is_maximized = False
            
            # 4. Reconstrói os cards por trás da cortina já nas novas proporções
            self.after(50, lambda: self.update_history(self.current_data))
            self.after(100, self._adjust_scrollbar_visibility)

    def minimize(self):
        """Minimiza a janela contornando a limitação do overrideredirect"""
        self.overrideredirect(False)
        self.iconify()
        # Monitora o estado para reativar o overrideredirect ao voltar
        self.bind("<FocusIn>", self.on_restore)

    def on_restore(self, event):
        """Reativa o visual sem bordas ao restaurar a janela"""
        if self.state() == "normal":
            self.overrideredirect(True)
            self.unbind("<FocusIn>")
