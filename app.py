from main import *
import tkinter as tk
from tkinter import ttk, filedialog, scrolledtext, messagebox
import threading
import os

class LatexConverterGUI:
    def __init__(self, master):
        self.master = master
        master.title("PDF/Image to LaTeX Converter")
        master.geometry("800x600")

        # Variables
        self.source_type = tk.StringVar(value='pdf')
        self.api_key = tk.StringVar()
        self.file_path = tk.StringVar()
        self.output_path = tk.StringVar(value=os.getcwd())
        self.output_filename = tk.StringVar(value="output.tex")
        self.custom_prompt = tk.StringVar()
        self.running = False
        
        # Default prompt
        self.default_prompt = ""
        self.custom_prompt.set(self.default_prompt)

        # Create widgets
        self.create_widgets()

    def create_widgets(self):
        main_frame = ttk.Frame(self.master)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Source settings
        source_frame = ttk.LabelFrame(main_frame, text="Настройки источника")
        source_frame.grid(row=0, column=0, columnspan=2, sticky='we', pady=5)

        ttk.Label(source_frame, text="Тип источника:").grid(row=0, column=0, padx=5, pady=5, sticky='w')
        ttk.Radiobutton(source_frame, text="PDF файл", variable=self.source_type, value='pdf').grid(row=0, column=1, sticky='w')
        ttk.Radiobutton(source_frame, text="Папка с изображениями", variable=self.source_type, value='directory').grid(row=0, column=2, sticky='w')

        ttk.Label(source_frame, text="Путь к файлу/папке:").grid(row=1, column=0, padx=5, pady=5, sticky='w')
        ttk.Entry(source_frame, textvariable=self.file_path, width=50).grid(row=1, column=1, sticky='we', padx=5)
        ttk.Button(source_frame, text="Обзор", command=self.browse_file).grid(row=1, column=2, padx=5)

        # API Key
        api_frame = ttk.LabelFrame(main_frame, text="Настройки API")
        api_frame.grid(row=1, column=0, columnspan=2, sticky='we', pady=5)

        ttk.Label(api_frame, text="API ключ Gemini:").grid(row=0, column=0, padx=5, pady=5, sticky='w')
        ttk.Entry(api_frame, textvariable=self.api_key, width=50).grid(row=0, column=1, columnspan=2, sticky='we', padx=5)

        # Output settings
        output_frame = ttk.LabelFrame(main_frame, text="Настройки вывода")
        output_frame.grid(row=2, column=0, columnspan=2, sticky='we', pady=5)

        ttk.Label(output_frame, text="Папка сохранения:").grid(row=0, column=0, padx=5, pady=5, sticky='w')
        ttk.Entry(output_frame, textvariable=self.output_path, width=50).grid(row=0, column=1, sticky='we', padx=5)
        ttk.Button(output_frame, text="Обзор", command=self.browse_output).grid(row=0, column=2, padx=5)

        ttk.Label(output_frame, text="Имя файла:").grid(row=1, column=0, padx=5, pady=5, sticky='w')
        ttk.Entry(output_frame, textvariable=self.output_filename, width=50).grid(row=1, column=1, sticky='we', padx=5)

        # Prompt
        prompt_frame = ttk.LabelFrame(main_frame, text="Промпт")
        prompt_frame.grid(row=3, column=0, columnspan=2, sticky='we', pady=5)

        self.prompt_edit = scrolledtext.ScrolledText(prompt_frame, wrap=tk.WORD, width=85, height=8)
        self.prompt_edit.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.prompt_edit.insert(tk.INSERT, self.default_prompt)

        # Log
        log_frame = ttk.LabelFrame(main_frame, text="Лог выполнения")
        log_frame.grid(row=4, column=0, columnspan=2, sticky='nsew', pady=5)

        self.log_area = scrolledtext.ScrolledText(log_frame, wrap=tk.WORD, width=85, height=10)
        self.log_area.pack(fill=tk.BOTH, expand=True)

        # Control buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=5, column=0, columnspan=2, pady=10)

        self.start_btn = ttk.Button(button_frame, text="Начать конвертацию", command=self.start_conversion)
        self.start_btn.pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Остановить", command=self.stop_conversion).pack(side=tk.LEFT, padx=5)

        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(4, weight=1)

    def browse_file(self):
        if self.source_type.get() == 'pdf':
            path = filedialog.askopenfilename(filetypes=[("PDF files", "*.pdf")])
        else:
            path = filedialog.askdirectory()
        self.file_path.set(path)

    def browse_output(self):
        path = filedialog.askdirectory()
        if path:
            self.output_path.set(path)

    def log(self, message):
        self.log_area.insert(tk.END, message + "\n")
        self.log_area.see(tk.END)
        self.master.update_idletasks()

    def start_conversion(self):
        if self.running:
            return

        if not self.api_key.get():
            messagebox.showerror("Ошибка", "Введите API ключ!")
            return

        if not self.file_path.get():
            messagebox.showerror("Ошибка", "Выберите файл или папку!")
            return

        output_file = os.path.join(self.output_path.get(), self.output_filename.get())
        if os.path.exists(output_file):
            if not messagebox.askyesno("Подтверждение", "Файл уже существует. Перезаписать?"):
                return

        self.running = True
        self.start_btn['state'] = tk.DISABLED
        self.log_area.delete(1.0, tk.END)

        prompt = self.prompt_edit.get("1.0", tk.END).strip()
        thread = threading.Thread(
            target=self.run_conversion,
            args=(self.file_path.get(), 
                 self.source_type.get(),
                 self.api_key.get(),
                 prompt,
                 output_file)
        )
        thread.start()

    def stop_conversion(self):
        self.running = False

    def run_conversion(self, path, source_type, api_key, prompt, output_file):
        try:
            converter = GeminiLatexConverter(api_key=api_key, output_tex=output_file)
            converter.prompt_template = prompt
            converter.set_gui_callbacks(self.log)

            self.log("Начало конвертации...")
            converter.convert_to_latex(path, source_type=source_type)
            self.log("\nКонвертация успешно завершена!")
        except Exception as e:
            self.log(f"\nОшибка: {str(e)}")
        finally:
            self.master.after(0, lambda: self.start_btn.configure(state=tk.NORMAL))
            self.running = False


if __name__ == "__main__":
    root = tk.Tk()
    app = LatexConverterGUI(root)
    root.mainloop()