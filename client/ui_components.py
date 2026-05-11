import customtkinter as ctk
from config_manager import CONFIG

class ToastNotification(ctk.CTkToplevel):
    def __init__(self, master, sender, message):
        super().__init__(master)
        self.title("W.A.N.D. Notification")
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        
        # Truque para cantos arredondados: janela transparente e frame interno arredondado
        transparent_color = "#000001"
        self.attributes("-transparentcolor", transparent_color)
        self.configure(fg_color=transparent_color)
        
        width = CONFIG['toast_width']
        height = CONFIG['toast_height']
        
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x = screen_width - width - 20
        y = screen_height - height - 60
        self.geometry(f"{width}x{height}+{x}+{y}")

        # Container Principal Arredondado
        self.container = ctk.CTkFrame(
            self, 
            fg_color="#1EA952", 
            corner_radius=15, 
            border_width=1, 
            border_color="#075E54"
        )
        self.container.pack(fill="both", expand=True, padx=2, pady=2)

        self.container.grid_columnconfigure(0, weight=1)
        
        # Header
        self.header_frame = ctk.CTkFrame(self.container, fg_color="transparent")
        self.header_frame.grid(row=0, column=0, sticky="ew", padx=15, pady=(12, 0))
        self.header_frame.grid_columnconfigure(0, weight=1)

        # Sombra do Nome
        self.lbl_sender_shadow = ctk.CTkLabel(
            self.header_frame, 
            text=sender, 
            font=ctk.CTkFont(family="Segoe UI", weight="bold", size=15), 
            text_color="#075E54"
        )
        self.lbl_sender_shadow.grid(row=0, column=0, sticky="w", padx=(1, 0), pady=(1, 0))

        self.lbl_sender = ctk.CTkLabel(
            self.header_frame, 
            text=sender, 
            font=ctk.CTkFont(family="Segoe UI", weight="bold", size=15), 
            text_color="#FFFFFF"
        )
        self.lbl_sender.grid(row=0, column=0, sticky="w")

        self.btn_close = ctk.CTkButton(
            self.header_frame, 
            text="✕", 
            width=30, 
            height=30, 
            fg_color="transparent", 
            hover_color="#128C7E", 
            text_color="#FFFFFF",
            font=ctk.CTkFont(size=16),
            command=self.destroy
        )
        self.btn_close.grid(row=0, column=1, sticky="e")

        # Sombra da Mensagem
        self.lbl_message_shadow = ctk.CTkLabel(
            self.container, 
            text=message, 
            wraplength=width-40, 
            justify="left", 
            text_color="#075E54",
            font=ctk.CTkFont(family="Segoe UI", size=13)
        )
        self.lbl_message_shadow.grid(row=1, column=0, sticky="w", padx=(16, 0), pady=(6, 21))

        # Mensagem Principal
        self.lbl_message = ctk.CTkLabel(
            self.container, 
            text=message, 
            wraplength=width-40, 
            justify="left", 
            text_color="#F0F2F5",
            font=ctk.CTkFont(family="Segoe UI", size=13)
        )
        self.lbl_message.grid(row=1, column=0, sticky="w", padx=15, pady=(5, 20))
