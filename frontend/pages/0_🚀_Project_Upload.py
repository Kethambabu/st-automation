"""
AI Test Platform — Main Project Upload Entrance

This is the very first page of the application where users upload
their raw ZIP file holding their codebase. It traverses the FastAPI boundary
to unzip, analyze the python AST tree, and finally ask the AI generator
to spin up tests for it.
"""

import streamlit as st
import requests

API_BASE = "http://127.0.0.1:8000"

st.set_page_config(page_title="Project Upload", page_icon="🚀", layout="wide")

# ── Sidebar ───────────────────────────────────────────────────────
with st.sidebar:
    st.header("🚀 Upload Pipeline")
    st.markdown("""
**Steps:**
1. Enter project name & upload ZIP
2. Wait for AST analysis
3. Generate AI test spec
4. Download or review in **AI Test Reviewer**
""")
    st.divider()
    if "project_id" in st.session_state:
        st.caption("Current Project ID")
        st.code(st.session_state.project_id, language=None)

st.title("🚀 Upload & Analyze Project")
st.markdown("Upload your source code ZIP to trigger AST extraction and AI test generation.")

st.divider()

col1, col2 = st.columns([1, 1.2], gap="large")

# ── 1. Upload Section ─────────────────────────────────────────────
with col1:
    st.subheader("① Source Code Upload")
    project_name = st.text_input("Project Name", value="My Backend System")
    uploaded_zip = st.file_uploader("Upload Project Archive (.zip)", type=["zip"])

    if st.button("Extract & Analyze Codebase 🔍", type="primary", use_container_width=True):
        if not uploaded_zip:
            st.error("Please upload a ZIP file first.")
        else:
            with st.spinner("Uploading and extracting ZIP…"):
                files = {"file": (uploaded_zip.name, uploaded_zip.getvalue(), "application/zip")}
                data = {"project_name": project_name}
                try:
                    upload_resp = requests.post(
                        f"{API_BASE}/api/v1/upload/zip", files=files, data=data, timeout=300
                    )
                    if upload_resp.status_code == 202:
                        res_json = upload_resp.json()
                        st.session_state.project_id = res_json.get("project_id")
                        st.session_state.do_analysis = True
                        st.session_state.analysis_complete = False
                        st.session_state.generated_markdown = None
                        st.success(f"✅ Extracted! Project ID: `{st.session_state.project_id}`")
                    else:
                        st.error(f"Upload failed ({upload_resp.status_code}): {upload_resp.text}")
                except requests.exceptions.ConnectionError:
                    st.error("❌ Backend not reachable.")
                    st.code("cd backend && uvicorn main:app --reload")
                except Exception as e:
                    st.error(f"Error: {e}")

# ── 2. Analysis Results ───────────────────────────────────────────
with col2:
    if "project_id" in st.session_state and st.session_state.get("do_analysis"):
        st.subheader("② Structural Analysis Results")
        pid = st.session_state.project_id

        with st.spinner("Parsing Python AST — detecting functions, classes & API routes…"):
            try:
                analyze_resp = requests.post(f"{API_BASE}/api/v1/analysis/{pid}", timeout=300)

                if analyze_resp.status_code == 200:
                    s = analyze_resp.json()
                    st.success("✅ Codebase mapped successfully.")

                    st.metric("Python Files Scanned", s.get("total_files", 0))
                    sc1, sc2, sc3 = st.columns(3)
                    sc1.metric("Classes", s.get("total_classes", 0))
                    sc2.metric("Functions", s.get("total_functions", 0))
                    sc3.metric("API Routes", s.get("total_apis", 0))

                    st.session_state.analysis_complete = True
                    st.session_state.do_analysis = False
                else:
                    st.error(f"Analysis failed ({analyze_resp.status_code}): {analyze_resp.text}")
            except Exception as e:
                st.error(f"Analysis error: {e}")

# ── 3. AI Test Generation ─────────────────────────────────────────
if st.session_state.get("analysis_complete"):
    st.divider()
    st.subheader("③ AI Automated Test Generation")
    st.markdown(
        "The AST summary is chunked and sent to **Groq LLaMA 3** to generate "
        "Functional, Edge Case, Negative, and Security test cases."
    )

    if st.button("Generate Tests with AI 🧠", use_container_width=True):
        pid = st.session_state.project_id
        with st.spinner("Invoking Groq LLM — this may take up to 45 seconds…"):
            try:
                gen_resp = requests.post(f"{API_BASE}/api/v1/generation/{pid}", timeout=600)

                if gen_resp.status_code == 200:
                    st.balloons()
                    st.success("Test specification generated!")
                    st.session_state.generated_markdown = gen_resp.json().get("markdown_output", "")
                else:
                    st.error(f"Generation failed ({gen_resp.status_code}): {gen_resp.text}")
            except requests.exceptions.ReadTimeout:
                st.error("❌ Timed out. The codebase may be too large — try again.")
            except requests.exceptions.ConnectionError:
                st.error("❌ Backend not reachable.")
            except Exception as e:
                st.error(f"Error: {e}")

# ── 4. Download & Preview ─────────────────────────────────────────
if st.session_state.get("generated_markdown"):
    st.divider()
    md = st.session_state.generated_markdown
    pid = st.session_state.get("project_id", "project")

    st.subheader("④ Download & Review")

    dl_col, info_col = st.columns([1, 2])
    with dl_col:
        st.download_button(
            label="💾 Download Test Spec (.md)",
            data=md.encode("utf-8"),
            file_name=f"{pid}_tests.md",
            mime="text/markdown",
            use_container_width=True,
        )
    with info_col:
        st.info("Switch to **AI Test Reviewer** in the sidebar to edit and convert to JSON.")

    with st.expander("Preview generated spec"):
        st.markdown(md)
