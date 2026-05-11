import customtkinter as ctk
from config_manager import CONFIG
from PIL import Image
import io
import base64

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
        
        width = CONFIG['toast_width']
        height = CONFIG['toast_height']
        
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
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

        self.force_on_top()

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
