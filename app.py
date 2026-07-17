import streamlit as st
import io
from docx import Document
import pdfplumber

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
        if not raw_text_to_translate.strip() and not uploaded_file:
            st.warning("Пожалуйста, введите текст или загрузите файл.")
        else:
            with st.spinner("Перевод в процессе..."):
                st.success("Парсер отработал. Текст готов к передаче в модуль перевода!")
                # Выводим финальный текст в блок кода, чтобы убедиться в правильности структуры
                st.markdown("### Финальный текст для перевода:")
                st.code(raw_text_to_translate, language="text")
    else:
        st.info("Результат перевода появится здесь после запуска процесса.")
