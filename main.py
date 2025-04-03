import fitz, time, io, re, os
from PIL import Image
from google import genai
from google.genai import types


class GeminiLatexConverter:
    def __init__(self, api_key, output_tex="output.tex"):
        self.client = genai.Client(api_key=api_key)
        self.output_tex = output_tex
        self.latex_header = """\\documentclass{article}
\\usepackage[russian]{babel}
\\usepackage{amsmath, amssymb}
\\usepackage[utf8]{inputenc}
\\usepackage{graphicx}
\\usepackage{tabularx}
\\usepackage{multirow}
\\begin{document}
"""
        self.latex_footer = "\\end{document}\n"
        self.rpm_limit = 30
        self.request_count = 0
        self.max_context_length = 4000

    def clean_latex_output(self, text):
        """Очистка сгенерированного LaTeX от артефактов"""
        # Удаление markdown code blocks
        text = re.sub(r'```latex?\s*', '', text, flags=re.IGNORECASE)
        text = re.sub(r'```\s*', '', text)
        
        # Удаление HTML-подобных тегов
        text = re.sub(r'<.*?>', '', text)
        
        # Удаление повторяющихся пустых строк
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        # # Фикс некорректных спецсимволов
        # replacements = {
        #     r'\\%': '%',
        #     r'\\_': '_',
        #     r'\\#': '#',
        #     r'\\&': '&',
        #     r'\\$': '$',
        #     r'\\~': '~',
        #     r'\\^': '^'
        # }
        
        # for pattern, replacement in replacements.items():
        #     text = re.sub(pattern, replacement, text)
        
        # Удаление ошибочных заголовков
        text = re.sub(
            r'\\usepackage{*?\\documentclass.*?\\begin{document}?\\end{document}?begin{document}?end{document}?documentclass.*?usepackage{*',
            '',
            text,
            flags=re.DOTALL
        )
        
        # Удаление случайных подписей картинок
        text = re.sub(
            r'\\begin{figure}.*?\\end{figure}',
            '',
            text,
            flags=re.DOTALL
        )
        
        # Удаление пустых окружений
        text = re.sub(
            r'\\begin{(equation|tabular)}\s*\\end{\1}',
            '',
            text,
            flags=re.IGNORECASE
        )
        
        return text

    def pdf_to_images(self, pdf_path, dpi=300):
        """Convert PDF to list of PIL Images"""
        doc = fitz.open(pdf_path)
        images = []
        for page in doc:
            pix = page.get_pixmap(dpi=dpi)
            img_data = pix.tobytes("png")
            images.append(Image.open(io.BytesIO(img_data)))
        return images
    
    def process_directory(self, img_dir, dpi=300):
        """Обработка всех изображений в директории"""
        images = []
        valid_ext = ('.png', '.jpg', '.jpeg', '.bmp', '.tiff')
        
        # Сортировка файлов по имени
        files = sorted([f for f in os.listdir(img_dir) 
                      if f.lower().endswith(valid_ext)],
                      key=lambda x: os.path.splitext(x)[0])
        
        for f in files:
            img_path = os.path.join(img_dir, f)
            try:
                images.append(Image.open(img_path))
            except Exception as e:
                print(f"Ошибка загрузки {img_path}: {e}")
        
        return images

    def process_image(self, image, previous_response=None, retries=3):
        """Process single image with Gemini API"""
        contents = []
        prompt = ("Преобразуйте это изображение в LaTeX, сохраняя таблицы (используя tabularx), "
                  "формулы (в окружении equation) и структуру с сохранением "
                  "структуры и заголовками (кроме begin{document} и end{document})."
                  "** символ форматирования не поддерживается.")
        
        if previous_response:
            prompt = ("Продолжите перевод в LaTeX данной картинки, сохраняя таблицы (используя tabularx), "
                      "формулы (в окружении equation) и структуру для этого изображения, "
                      f"учитывая предыдущий контекст:\n{previous_response}\n"
                      "Сохраняйте структуру и заголовки (кроме begin{document} и end{document}). "
                      "** символ форматирования не поддерживается.")
        
        contents.append(prompt)
        contents.append(image)
        
        for _ in range(retries):
            try:
                # RPM rate limiting
                if self.request_count >= self.rpm_limit:
                    time.sleep(60)
                    self.request_count = 0
                
                response = self.client.models.generate_content(
                    model="gemini-2.0-flash-lite",
                    contents=contents
                    #generation_config=types.GenerationConfig(temperature=0.0)
                )
                response_text = response.text.strip()
                cleaned_text = self.clean_latex_output(response_text)
                self.request_count += 1
                return cleaned_text
            except Exception as e:
                print(f"Ошибка: {e}. Повторная попытка...")
                time.sleep(2)
        return None

    def convert_pdf_to_latex(self, pdf_path, dpi=300):
        """Main conversion workflow"""
        images = self.pdf_to_images(pdf_path, dpi)
        latex_content = self.latex_header
        previous_response = None
        
        for idx, image in enumerate(images):
            print(f"Обработка страницы {idx+1}/{len(images)}...")
            response_text = self.process_image(image, previous_response)
            
            if response_text:
                # Validate and clean LaTeX output
                if "\\documentclass" in response_text:
                    response_text = response_text.split("\\begin{document}")[-1].split("\\end{document}")[0]
                
    def _init_output_file(self):
        """Инициализация LaTeX файла с заголовком"""
        with open(self.output_tex, "w", encoding="utf-8") as f:
            f.write(self.latex_header)

    def _save_page(self, page_content, page_num):
        """Постепенное сохранение страниц в файл"""
        with open(self.output_tex, "a", encoding="utf-8") as f:
            f.write(f"\n% Страница {page_num}\n{page_content}\n")

    def _finalize_output(self):
        """Добавление завершающей части документа"""
        with open(self.output_tex, "a", encoding="utf-8") as f:
            f.write(self.latex_footer)

    def convert_to_latex(self, source, source_type='pdf', dpi=300):
        """
        Основной метод конвертации
        :param source: путь к PDF файлу или директории с изображениями
        :param source_type: 'pdf' или 'directory'
        :param dpi: разрешение для PDF
        """
        self._init_output_file()
        
        if source_type == 'pdf':
            images = self.pdf_to_images(source, dpi)
        elif source_type == 'directory':
            images = self.process_directory(source)
        else:
            raise ValueError("Неподдерживаемый тип источника")

        previous_response = None
        
        for idx, image in enumerate(images):
            print(f"Обработка страницы {idx+1}/{len(images)}...")
            response_text = self.process_image(image, previous_response)
            
            if response_text:
                # Ограничение контекста для предыдущих ответов
                previous_response = response_text[-self.max_context_length:]
                
                # Очистка и сохранение
                self._save_page(response_text, idx+1)
                
                # Контроль памяти: периодическая сборка мусора
                if idx % 10 == 0:
                    import gc
                    gc.collect()
            else:
                print(f"Ошибка обработки страницы {idx+1}")

            # Базовый контроль RPM
            time.sleep(60 / self.rpm_limit + 0.5)

        self._finalize_output()
        print(f"LaTeX документ сохранен в {self.output_tex}")
# Пример использования
if __name__ == "__main__":
    converter = GeminiLatexConverter(api_key="AIzaSyAYf80IwompkZPlEeWnOWYn3Fd8BaifSpw")
    
    # Для PDF файла:
    converter.convert_to_latex("input.pdf", source_type='pdf')
    
    # Для директории с изображениями:
    # converter.convert_to_latex(os.path.join(os.getcwd(), "images"), source_type='directory')