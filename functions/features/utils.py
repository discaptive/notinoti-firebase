def clean_string(st: str) -> str:
    result = st.replace("\t", "").replace("\n", "").replace("\r", "").strip()
    return result
