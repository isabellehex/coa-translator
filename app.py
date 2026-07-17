import streamlit as st
import io
from docx import Document
import pdfplumber
import requests
import csv

# ==========================================
# ЗАГРУЗКА СЛОВАРЯ ИЗ CSV
# ==========================================
@st.cache_data  # Кэшируем, чтобы не перечитывать файл при каждом клике
def load_dictionary(file_path="dictionary.csv"):
    """Читает CSV словарь из репозитория и переводит в dict с нижним регистром в ключах"""
    coa_dict = {}
    try:
        with open(file_path, mode='r', encoding='utf-8') as f:
            reader = csv.reader(f, delimiter=';')
            next(reader)  # Пропускаем заголовок english;russian
            for row in reader:
                if len(row) >= 2:
                    eng_phrase = row[0].strip().lower()
                    rus_phrase = row[1].strip()
                    coa_dict[eng_phrase] = rus_phrase
    except Exception as e:
        st.error(f"Не удалось загрузить dictionary.csv: {e}")
    return coa_dict

# Загружаем словарь в память
COA_DICTIONARY = load_dictionary()

# ==========================================
# 1. НАСТРОЙКА СТРАНИЦЫ
# ==========================================
st.set_page_config(
    page_title="Переводчик Сертификатов Анализа (CoA)",
    page_icon="🧪",
    layout="wide"
)

# ==========================================
# 2. МОДУЛЬ ПАРСИНГА (DOCX & PDF)
# ==========================================

def parse_docx(file_bytes) -> str:
    """Извлекает текст и таблицы из DOCX, разделяя ячейки знаком '|'"""
    doc = Document(io.BytesIO(file_bytes))
    full_text = []
    
    for element in doc.element.body:
        # Чтение обычных абзацев
        if element.tag.endswith('p'):
            for paragraph in doc.paragraphs:
                if paragraph._element == element:
                    if paragraph.text.strip():
                        full_text.append(paragraph.text)
                    break
        
        # Чтение таблиц
        elif element.tag.endswith('tbl'):
            for table in doc.tables:
                if table._element == element:
                    for row in table.rows:
                        row_text = [cell.text.strip().replace("\n", " ") for cell in row.cells]
                        # Убираем дубликаты из-за объединенных ячеек
                        unique_row_text = []
                        for cell in row_text:
                            if not unique_row_text or unique_row_text[-1] != cell:
                                unique_row_text.append(cell)
                        full_text.append(" | ".join(unique_row_text))
                    break
                    
    return "\n".join(full_text)


def parse_pdf(file_bytes) -> str:
    """Извлекает текст из PDF. Если на странице есть таблица, форматирует её через '|'"""
    full_text = []
    
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for page in pdf.pages:
            # Извлекаем таблицы со страницы
            tables = page.extract_tables()
            table_index = 0
            
            # Извлекаем весь текст страницы как строки
            page_text = page.extract_text()
            if page_text:
                lines = page_text.split("\n")
                for line in lines:
                    # Если строка похожа на заголовок таблицы или мы заходим в зону таблицы, 
                    # pdfplumber может вернуть её и в тексте, и в таблице.
                    # Для простоты: если нашли таблицы, преобразуем их и добавляем в текст.
                    full_text.append(line)
            
            # Если pdfplumber нашел структуры таблиц, мы можем вывести их отдельно в конце 
            # или вместо сырого текста. Для CoA лучше всего вытащить строки таблиц:
            if tables:
                full_text.append("\n--- Обнаружена таблица показателей ---")
                for table in tables:
                    for row in table:
                        # Фильтруем None значения, которые бывают при пустых ячейках
                        row_text = [str(cell).strip().replace("\n", " ") if cell else "" for cell in row]
                        full_text.append(" | ".join(row_text))
                        
    return "\n".join(full_text)


def extract_text_from_file(uploaded_file) -> str:
    """Управляющая функция: проверяет расширение и запускает нужный парсер"""
    file_bytes = uploaded_file.read()
    file_name = uploaded_file.name.lower()
    
    if file_name.endswith(".docx"):
        return parse_docx(file_bytes)
    elif file_name.endswith(".pdf"):
        return parse_pdf(file_bytes)
    elif file_name.endswith(".txt"):
        return file_bytes.decode("utf-8")
    else:
        raise ValueError("Неподдерживаемый формат файла")

# ==========================================
# 3. ПРОВЕРКА ПОДКЛЮЧЕНИЯ (SECRETS)
# ==========================================
def check_secrets():
    status = {"yandex": False, "github": False}
    if "yandex" in st.secrets:
        y_sec = st.secrets["yandex"]
        if y_sec.get("folder_id") and y_sec.get("api_key"):
            status["yandex"] = True
    if "github" in st.secrets:
        g_sec = st.secrets["github"]
        if g_sec.get("token") and g_sec.get("repo") and g_sec.get("branch"):
            status["github"] = True
    return status

secrets_status = check_secrets()

# ==========================================
# 3. БОКОВАЯ ПАНЕЛЬ (SIDEBAR)
# ==========================================
with st.sidebar:
    st.header("⚙️ Настройки и Статус")
    st.subheader("Интеграции")
    
    if secrets_status["yandex"]:
        st.success("Yandex GPT API: Подключено")
    else:
        st.error("Yandex GPT API: Ключи не найдены")
        
    if secrets_status["github"]:
        st.success("GitHub Repository: Подключено")
    else:
        st.error("GitHub Repository: Данные не найдены")
        
    st.write("---")
    st.caption("Ключи берутся автоматически из Streamlit Secrets.")

# ==========================================
# МОДУЛЬ ГИБРИДНОГО ПЕРЕВОДА
# ==========================================

def translate_via_yandex_gpt(text: str) -> str:
    """Отправляет текст на перевод в Yandex GPT при отсутствии в словаре"""
    if not text.strip():
        return text
        
    if "yandex" not in st.secrets:
        return f"[Ключи Yandex не найдены] {text}"
        
    folder_id = st.secrets["yandex"]["folder_id"]
    api_key = st.secrets["yandex"]["api_key"]
    
    url = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"
    headers = {
        "Authorization": f"Api-Key {api_key}",
        "Content-Type": "application/json"
    }
    
    data = {
        "modelUri": f"gpt://{folder_id}/yandexgpt-lite",
        "completionOptions": {
            "stream": False,
            "temperature": 0.1,  # Низкая температура для строгого перевода без фантазий
            "maxTokens": "2000"
        },
        "messages": [
            {
                "role": "system",
                "text": (
                    "Ты профессиональный переводчик химической и лабораторной документации. "
                    "Переведи предоставленный текст на русский язык. Сохраняй химическую терминологию. "
                    "Переводи строго только сам текст. Не изменяй формулы, цифры, даты, сокращения "
                    "физических величин (например, °C) или спецсимволы. Не добавляй никаких пояснений, "
                    "комментариев от себя или вводных фраз. Выдавай только чистый перевод."
                )
            },
            {
                "role": "user",
                "text": text
            }
        ]
    }
    
    try:
        response = requests.post(url, headers=headers, json=data, timeout=15)
        if response.status_code == 200:
            result = response.json()
            translated_text = result["result"]["alternatives"][0]["message"]["text"]
            return translated_text.strip()
        else:
            return f"[Ошибка API {response.status_code}] {text}"
    except Exception as e:
        return f"[Ошибка подключения: {e}] {text}"


def translate_cell_or_line(text: str) -> str:
    """Логика перевода элемента: проверка на цифры -> поиск в CSV-словаре -> YandexGPT"""
    cleaned = text.strip()
    
    if not cleaned:
        return ""
        
    # 1. Защита для чистых цифр, формул, диапазонов и дат (чтобы не гонять их в сеть)
    # Если в строке есть цифры, но абсолютно нет букв (например, "58-61-7", "233 - 238 °C", "< 0.001%")
    if any(char.isdigit() for char in cleaned) and not any(char.isalpha() for char in cleaned):
        return cleaned
        
    # 2. Ищем фразу в словаре из CSV (сверяем в нижнем регистре)
    if cleaned.lower() in COA_DICTIONARY:
        return COA_DICTIONARY[cleaned.lower()]
        
    # 3. Если совпадений нет — отдаем в YandexGPT
    return translate_via_yandex_gpt(cleaned)


def process_coa_translation(raw_text: str) -> str:
    """Разбивает текст на строки, бережно переводит ячейки таблиц через '|' и собирает обратно"""
    translated_lines = []
    lines = raw_text.split("\n")
    
    for line in lines:
        if "|" in line:
            # Строка является частью таблицы — бьем на ячейки, сохраняя разметку
            cells = line.split("|")
            translated_cells = [translate_cell_or_line(cell) for cell in cells]
            translated_lines.append(" | ".join(translated_cells))
        else:
            # Обычный текст (шапка, дисклеймеры)
            translated_lines.append(translate_cell_or_line(line))
            
    return "\n".join(translated_lines)

# ==========================================
# 4. ОСНОВНАЯ ЧАСТЬ ИНТЕРФЕЙСА
# ==========================================
st.title("🧪 Переводчик Сертификатов Анализа (CoA)")
st.write("Гибридный перевод паспортов качества: Словари + Yandex GPT.")

col_input, col_preview = st.columns([1, 1])

# Здесь будет храниться сырой текст, который мы отдадим переводчику
raw_text_to_translate = ""

with col_input:
    st.subheader("📥 Входные данные")
    
    tab_text, tab_file = st.tabs(["📝 Вставить текст", "📄 Загрузить файл"])
    
    with tab_text:
        input_text = st.text_area(
            "Вставьте скопированный текст сертификата:",
            height=300,
            placeholder="PRODUCT NAME | ADENOSINE\nCAS NUMBER | 58-61-7..."
        )
        if input_text:
            raw_text_to_translate = input_text
        
    with tab_file:
        uploaded_file = st.file_uploader(
            "Выберите файл сертификата (.docx, .pdf, .txt)", 
            type=["docx", "pdf", "txt"]
        )
        if uploaded_file is not None:
            try:
                # Запускаем наш универсальный парсер
                raw_text_to_translate = extract_text_from_file(uploaded_file)
                st.success(f"Файл '{uploaded_file.name}' успешно распарсен!")

                
                # Показываем блок предпросмотра, чтобы увидеть, как проставились разделители '|'
                with st.expander("🔍 Посмотреть результат парсинга файла"):
                    st.text(raw_text_to_translate[:1500] + ("..." if len(raw_text_to_translate) > 1500 else ""))
            except Exception as e:
                st.error(f"Ошибка при парсинге файла: {e}")

    st.write("---")
    start_translation = st.button("🚀 Начать перевод", type="primary", use_container_width=True)

with col_preview:
    st.subheader("📤 Результат перевода")
    
    if start_translation:
        if not raw_text_to_translate.strip():
            st.warning("Пожалуйста, введите текст или загрузите файл.")
        else:
            with st.spinner("Перевод в процессе... Сверяемся со словарем и запрашиваем Yandex GPT..."):
                # Запуск функции гибридного перевода
                translated_result = process_coa_translation(raw_text_to_translate)
                
                st.success("Перевод успешно завершен!")
                
                tab_res_text, tab_res_docx = st.tabs(["👀 Предпросмотр текста", "💾 Скачать документ"])
                
                with tab_res_text:
                    st.markdown("### Переведенный текст:")
                    st.text_area("Результат:", value=translated_result, height=400)
                    
                with tab_res_docx:
                    st.info("Перевод готов. На следующем шаге мы настроим экспорт этого текста обратно в файл .docx")
    else:
        st.info("Результат перевода появится здесь после запуска процесса.")
