import customtkinter as ctk

class HistoryMockup(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Configurações da Janela
        self.title("W.A.N.D. - Histórico (Mockup)")
        
        # Largura um pouco maior que o toast (375) -> 450
        # Altura para 3+ mensagens (150*3) -> 600
        window_width = 450
        window_height = 450
        
        # Centralizar na tela
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x = (screen_width // 2) - (window_width // 2)
        y = (screen_height // 2) - (window_height // 2)
        
        self.geometry(f"{window_width}x{window_height}+{x}+{y}")
        
        # Estilo Mac: Sem bordas padrão do Windows para total controle
        self.overrideredirect(True)
        
        # Cor de fundo "não tão branco" (Off-white/Mac Silver)
        self.bg_color = "#F5F5F7"
        self.configure(fg_color=self.bg_color)
        
        # Abordagem de transparência absoluta
        trans_color = "#000001"
        self.wm_attributes("-transparentcolor", trans_color)
        self.configure(fg_color=trans_color)
        self.config(bg=trans_color)

        # Container Principal com Bordas Arredondadas (sem borda externa para evitar serrilhado)
        self.main_container = ctk.CTkFrame(
            self, 
            fg_color=self.bg_color, 
            corner_radius=25,
            border_width=0
        )
        # Usando place centralizado com mais margem para garantir que o radius não "vaze" nas quinas do Windows
        self.main_container.place(relx=0.5, rely=0.5, relwidth=0.90, relheight=0.90, anchor="center")

        # BARRA DE TÍTULO (Estilo Mac)
        self.title_bar = ctk.CTkFrame(
            self.main_container,
            fg_color="transparent",
            height=40,
        )
        self.title_bar.pack(fill="x", side="top", pady=(10, 0), padx=20)
        
        # Título Centralizado
        self.title_label = ctk.CTkLabel(
            self.title_bar,
            text="Histórico de Notificações",
            font=ctk.CTkFont(family="SF Pro Display", size=14, weight="bold"),
            text_color="#1D1D1F"
        )
        self.title_label.place(relx=0.5, rely=0.5, anchor="center")

        # Botões na Direita Superior (como solicitado)
        self.btn_container = ctk.CTkFrame(self.title_bar, fg_color="transparent")
        self.btn_container.pack(side="right", padx=5)

        # Botão Fechar (Vermelho Mac)
        self.btn_close = ctk.CTkButton(
            self.btn_container, text="", width=12, height=12, corner_radius=6,
            fg_color="#FF5F57", hover_color="#E0443E", command=self.destroy
        )
        self.btn_close.pack(side="right", padx=2)

        # Botão Maximizar (Verde Mac)
        self.btn_max = ctk.CTkButton(
            self.btn_container, text="", width=12, height=12, corner_radius=6,
            fg_color="#28C840", hover_color="#1AAB2F"
        )
        self.btn_max.pack(side="right", padx=2)

        # Botão Minimizar (Amarelo Mac)
        self.btn_min = ctk.CTkButton(
            self.btn_container, text="", width=12, height=12, corner_radius=6,
            fg_color="#FEBC2E", hover_color="#D9A322"
        )
        self.btn_min.pack(side="right", padx=2)

        # ÁREA DE MENSAGENS (Scrollable)
        self.scrollable_frame = ctk.CTkScrollableFrame(
            self.main_container,
            fg_color="transparent",
            corner_radius=0
        )
        self.scrollable_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Dados Mockados (5 mensagens)
        mock_messages = [
            {"from": "João Silva", "text": "E aí, tudo certo para a reunião de amanhã?", "time": "14:20"},
            {"from": "Maria Souza", "text": "Pode me enviar aquele arquivo que conversamos mais cedo?", "time": "13:45"},
            {"from": "Grupo Trabalho", "text": "Novo deploy realizado em produção. Favor testarem as rotas de API.", "time": "12:10"},
            {"from": "Suporte TI", "text": "Sua solicitação #1234 foi finalizada com sucesso.", "time": "10:30"},
            {"from": "Mãe", "text": "Não esquece de passar no mercado na volta! ❤️", "time": "09:15"},
        ]

        for msg in mock_messages:
            self.create_message_card(msg)

        # Drag and Drop functionality for the title bar
        self.title_bar.bind("<ButtonPress-1>", self.start_move)
        self.title_bar.bind("<B1-Motion>", self.do_move)
        self.title_label.bind("<ButtonPress-1>", self.start_move)
        self.title_label.bind("<B1-Motion>", self.do_move)

    def create_message_card(self, data):
        # Card de Mensagem
        card = ctk.CTkFrame(
            self.scrollable_frame,
            fg_color="#FFFFFF",
            corner_radius=12,
            border_width=1,
            border_color="#E5E5EA"
        )
        card.pack(fill="x", pady=5, padx=5)

        # Nome do Remetente
        lbl_from = ctk.CTkLabel(
            card,
            text=data["from"],
            font=ctk.CTkFont(family="SF Pro Text", size=13, weight="bold"),
            text_color="#000000"
        )
        lbl_from.pack(anchor="w", padx=15, pady=(10, 0))

        # Texto da Mensagem
        lbl_text = ctk.CTkLabel(
            card,
            text=data["text"],
            font=ctk.CTkFont(family="SF Pro Text", size=13),
            text_color="#3A3A3C",
            wraplength=380,
            justify="left"
        )
        lbl_text.pack(anchor="w", padx=15, pady=(5, 10))

        # Horário (Canto Inferior Direito)
        lbl_time = ctk.CTkLabel(
            card,
            text=data["time"],
            font=ctk.CTkFont(family="SF Pro Text", size=10),
            text_color="#8E8E93"
        )
        lbl_time.place(relx=1.0, rely=1.0, x=-10, y=-5, anchor="se")

    def start_move(self, event):
        self.x = event.x
        self.y = event.y

    def do_move(self, event):
        deltax = event.x - self.x
        deltay = event.y - self.y
        x = self.winfo_x() + deltax
        y = self.winfo_y() + deltay
        self.geometry(f"+{x}+{y}")

if __name__ == "__main__":
    app = HistoryMockup()
    app.mainloop()
