import streamlit as st

from agent import run_agent

st.title("🏠 مشاور هوشمند املاک")

# حفظ تاریخچه‌ی مکالمه بین اجراهای مختلف Streamlit (برای اطلاعات ناقص چندمرحله‌ای)
if "history" not in st.session_state:
    st.session_state.history = None

user_input = st.text_area(
    "مشخصات ملک را وارد کنید:",
    placeholder="مثلاً: یک آپارتمان 120 متری در عظیمیه، ساخت 1400، دو خواب..."
)

if st.button("پیش‌بینی قیمت"):
    if user_input.strip():
        with st.spinner("در حال تحلیل ملک و محاسبه قیمت..."):
            try:
                answer, updated_history = run_agent(
                    user_input, history=st.session_state.history
                )
                st.session_state.history = updated_history
            except Exception as e:
                st.error(f"خطایی در اجرای Agent رخ داد: {e}")
            else:
                st.markdown(answer)
    else:
        st.warning("لطفاً مشخصات ملک را وارد کنید.")
