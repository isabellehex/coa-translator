import streamlit as st

# ==========================================
# 1. НАСТРОЙКА СТРАНИЦЫ
# ==========================================
st.set_page_config(
    page_title="Переводчик Сертификатов Анализа (CoA)",
    page_icon="🧪",
    layout="wide"
)

# ==========================================
# 2. ПРОВЕРКА ПОДКЛЮЧЕНИЯ (SECRETS)
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
        # Теперь официально поддерживаем PDF!
        uploaded_file = st.file_uploader(
            "Выберите файл сертификата (.docx, .pdf, .txt)", 
            type=["docx", "pdf", "txt"]
        )
        if uploaded_file is not None:
            st.success(f"Файл '{uploaded_file.name}' загружен.")
            st.info("Файл ожидает подключения модуля парсинга (DOCX / PDF).")
            # Сюда мы позже прикрутим вызов нужного парсера в зависимости от расширения

    st.write("---")
    start_translation = st.button("🚀 Начать перевод", type="primary", use_container_width=True)

with col_preview:
    st.subheader("📤 Результат перевода")
    
    if start_translation:
        if not raw_text_to_translate.strip() and not uploaded_file:
            st.warning("Пожалуйста, введите текст или загрузите файл.")
        else:
            with st.spinner("Перевод в процессе..."):
                st.info("Интерфейс готов к работе. На каком шаге сфокусируемся дальше?")
    else:
        st.info("Результат перевода появится здесь после запуска процесса.")
