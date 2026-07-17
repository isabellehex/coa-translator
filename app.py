import streamlit as st

# ==========================================
# 1. НАСТРОЙКА СТРАНИЦЫ И СТИЛЕЙ
# ==========================================
st.set_page_config(
    page_title="Переводчик Сертификатов Анализа (CoA)",
    page_icon="🧪",
    layout="wide"
)

# Простой CSS для красивого оформления плашек статуса
st.markdown("""
    <style>
    .status-box {
        padding: 10px;
        border-radius: 5px;
        margin-bottom: 10px;
    }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. ПРОВЕРКА ПОДКЛЮЧЕНИЯ (SECRETS)
# ==========================================
def check_secrets():
    """Проверяет наличие всех необходимых ключей в st.secrets"""
    status = {"yandex": False, "github": False}
    
    # Проверка Yandex GPT
    if "yandex" in st.secrets:
        y_sec = st.secrets["yandex"]
        if y_sec.get("folder_id") and y_sec.get("api_key"):
            status["yandex"] = True
            
    # Проверка GitHub
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
    
    # Отображение статуса подключения к сервисам
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
    st.caption("Ключи берутся автоматически из настроек Secrets вашего Streamlit Cloud.")

# ==========================================
# 4. ОСНОВНАЯ ЧАСТЬ ИНТЕРФЕЙСА
# ==========================================
st.title("🧪 Переводчик Сертификатов Анализа (CoA)")
st.write("Автоматический перевод паспортов качества с гибридной логикой: Словари + Yandex GPT.")

# Разделяем экран на две колонки: Ввод данных и Настройки словаря/Перевод
col_input, col_preview = st.columns([1, 1])

with col_input:
    st.subheader("📥 Входные данные")
    
    # Вкладки для разных способов загрузки
    tab_text, tab_file = st.tabs(["📝 Вставить текст", "📄 Загрузить файл"])
    
    with tab_text:
        input_text = st.text_area(
            "Вставьте скопированный текст сертификата анализа:",
            height=350,
            placeholder="PRODUCT NAME | ADENOSINE\nCAS NUMBER | 58-61-7..."
        )
        
    with tab_file:
        uploaded_file = st.file_uploader(
            "Выберите файл сертификата (.docx или .txt)", 
            type=["docx", "txt"]
        )
        if uploaded_file is not None:
            st.info(f"Файл {uploaded_file.name} успешно загружен! (Логика чтения будет добавлена на следующем шаге)")

    st.write("---")
    
    # Кнопка запуска процесса
    start_translation = st.button("🚀 Начать перевод сертификата", type="primary", use_container_width=True)

with col_preview:
    st.subheader("📤 Результат перевода")
    
    # Заглушка для демонстрации будущего вывода результатов
    if start_translation:
        if not input_text and not uploaded_file:
            st.warning("Пожалуйста, сначала введите текст или загрузите файл для перевода.")
        else:
            with st.spinner("Выполняется перевод..."):
                # Здесь будет вызываться наша функция перевода
                st.success("Перевод завершен! (Пока это демонстрация интерфейса)")
                
                # Вкладки для предпросмотра Markdown и готового файла
                tab_res_md, tab_res_docx = st.tabs(["👀 Предпросмотр текста", "💾 Скачать документ"])
                
                with tab_res_md:
                    st.markdown("### Пример переведенного документа (Markdown)")
                    st.markdown("""
**Сертификат анализа**  
**НАИМЕНОВАНИЕ ПРОДУКТА:** Аденозин для биохимии  
**НОМЕР CAS:** 58-61-7  
...
                    """)
                    
                with tab_res_docx:
                    st.write("Ваш документ готов к скачиванию:")
                    # Кнопка скачивания (пока заблокирована/пустая)
                    st.download_button(
                        label="📥 Скачать перевод (.docx)",
                        data=b"dummy data",
                        file_name="translated_coa.docx",
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        disabled=True
                    )
    else:
        st.info("Результат перевода и кнопка скачивания появятся здесь после запуска процесса.")

# ==========================================
# 5. СПРАВОЧНЫЙ БЛОК (СЛОВАРЬ)
# ==========================================
st.write("---")
with st.expander("📖 Посмотреть структуру базового словаря терминов"):
    st.write("Этот словарь используется для мгновенного перевода стандартных фраз без обращения к GPT:")
    
    # Для демонстрации выведем небольшую таблицу
    sample_dict = {
        "Английский термин": [
            "Certificate of Analysis", "PRODUCT NAME", "CAS NUMBER", 
            "Appearance", "White powder", "Assay", "Best before"
        ],
        "Русский перевод": [
            "Сертификат анализа", "НАИМЕНОВАНИЕ ПРОДУКТА", "НОМЕР CAS", 
            "Внешний вид", "Белый порошок", "Содержание основного вещества", "Годен до"
        ]
    }
    st.table(sample_dict)