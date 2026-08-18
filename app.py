import streamlit as st
from agent import run_agent

st.set_page_config(
    page_title="مشاور هوشمند املاک",
    page_icon="🏠",
    layout="centered",
)

st.markdown("""
<style>

@import url('https://cdn.jsdelivr.net/gh/rastikerdar/vazirmatn@v33.003/Vazirmatn-font-face.css');

* {
    font-family: 'Vazirmatn', sans-serif !important;
    direction: rtl;
}

.stApp {
    background: linear-gradient(180deg, #fafafa 0%, #f4f4f6 100%);
}

.block-container {
    max-width: 720px;
    padding-top: 3rem;
    padding-bottom: 3rem;
}

h1 {
    text-align: center;
    font-weight: 700;
    font-size: 2rem;
    color: #1f2933;
    margin-bottom: 0.25rem;
}

.subtitle {
    text-align: center;
    color: #8a8f98;
    font-size: 0.95rem;
    margin-bottom: 2.5rem;
}

label p {
    font-size: 0.95rem !important;
    color: #444 !important;
    font-weight: 500 !important;
}

textarea {
    border-radius: 14px !important;
    border: 1.5px solid #e3e3e8 !important;
    background-color: #ffffff !important;
    padding: 14px !important;
    font-size: 0.95rem !important;
    box-shadow: 0 1px 3px rgba(0,0,0,0.02) !important;
    transition: border-color 0.2s ease;
}

textarea:focus {
    border-color: #6c63ff !important;
    box-shadow: 0 0 0 3px rgba(108,99,255,0.12) !important;
}

.stButton {
    display: flex;
    justify-content: center;
    margin-top: 1.2rem;
}

.stButton > button {
    background: linear-gradient(135deg, #6c63ff, #5a52e0);
    color: #ffffff;
    border: none;
    border-radius: 12px;
    padding: 0.6rem 2.4rem;
    font-size: 1rem;
    font-weight: 600;
    box-shadow: 0 4px 14px rgba(108,99,255,0.3);
    transition: transform 0.15s ease, box-shadow 0.15s ease;
}

.stButton > button:hover {
    transform: translateY(-2px);
    box-shadow: 0 6px 18px rgba(108,99,255,0.4);
    color: #ffffff;
}

.stButton > button:active {
    transform: translateY(0px);
}

div[data-testid="stAlert"] {
    border-radius: 12px;
    font-size: 0.9rem;
}

.chat-wrap {
    margin-bottom: 1.8rem;
}

.bubble {
    padding: 12px 16px;
    border-radius: 14px;
    margin-bottom: 10px;
    font-size: 0.92rem;
    line-height: 1.9;
    max-width: 85%;
}

.bubble.user {
    background: #eef0ff;
    color: #2b2b40;
    margin-left: auto;
    border-bottom-left-radius: 4px;
}

.bubble.assistant {
    background: #ffffff;
    color: #2b2b40;
    border: 1px solid #ececf1;
    margin-right: auto;
    border-bottom-right-radius: 4px;
    box-shadow: 0 1px 4px rgba(0,0,0,0.03);
}

</style>
""", unsafe_allow_html=True)

st.markdown("<h1>🏠 مشاور هوشمند املاک</h1>", unsafe_allow_html=True)
st.markdown("<div class='subtitle'>مشخصات ملک خود را وارد کنید تا قیمت پیشنهادی را ببینید</div>", unsafe_allow_html=True)

if "chat_history" not in st.session_state:
    st.session_state.chat_history = None  # آرگومان history برای run_agent (context مکالمه)
if "messages" not in st.session_state:
    st.session_state.messages = []  

if st.session_state.messages:
    st.markdown("<div class='chat-wrap'>", unsafe_allow_html=True)
    for msg in st.session_state.messages:
        role_class = "user" if msg["role"] == "user" else "assistant"
        st.markdown(f"<div class='bubble {role_class}'>{msg['content']}</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

user_input = st.text_area(
    "مشخصات ملک را وارد کنید:",
    placeholder="مثلاً: یک آپارتمان 120 متری در عظیمیه، ساخت 1400، دو خواب...",
    height=120,
)

if st.button("پیش‌بینی قیمت"):
    if user_input.strip():
        st.session_state.messages.append({"role": "user"})
        with st.spinner("در حال تحلیل قیمت..."):
            try:
                answer, history = run_agent(user_input, st.session_state.chat_history)
                st.session_state.chat_history = history
                st.session_state.messages.append({"role": "assistant", "content": answer})
            except Exception as e:
                st.error(f"خطا در تحلیل: {e}")
        st.rerun()
    else:
        st.warning("لطفاً مشخصات ملک را وارد کنید.")
