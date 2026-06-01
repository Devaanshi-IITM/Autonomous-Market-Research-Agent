# app.py
# =============================================
# Competitive Intelligence Pipeline
# =============================================
# Run with: streamlit run app.py

import os
import time
import streamlit as st
import pypdf
import io
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(
    page_title="CompeteIQ — Competitive Intelligence",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');
* { font-family: 'Space Grotesk', sans-serif; }

.stApp { background: linear-gradient(135deg, #0a0e1a 0%, #0f172a 50%, #0a0e1a 100%); }

.main-header {
    background: linear-gradient(90deg, #f59e0b, #ef4444, #8b5cf6);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    font-size: 2.5rem; font-weight: 700; letter-spacing: -1px;
}
.sub-header { color: #64748b; font-size: 1rem; margin-top: 0; }

.step-card {
    background: #1e293b;
    border: 1px solid #334155;
    border-radius: 12px;
    padding: 16px 20px;
    margin: 8px 0;
    color: #e2e8f0;
}
.step-active {
    border-left: 4px solid #f59e0b;
    background: #1c1a0f;
}
.step-done {
    border-left: 4px solid #22c55e;
    background: #0f1c12;
}

.score-high   { color: #ef4444; font-weight: 700; font-size: 1.3rem; }
.score-medium { color: #f59e0b; font-weight: 700; font-size: 1.3rem; }
.score-low    { color: #22c55e; font-weight: 700; font-size: 1.3rem; }

.brief-container {
    background: #1e293b;
    border: 1px solid #334155;
    border-radius: 12px;
    padding: 24px;
    color: #e2e8f0;
}

section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0f172a, #0a0e1a);
    border-right: 1px solid #1e293b;
}
.stButton > button {
    background: linear-gradient(135deg, #f59e0b, #ef4444) !important;
    color: white !important; border: none !important;
    border-radius: 10px !important; font-weight: 600 !important;
}
.stTextInput > div > div > input, .stTextArea > div > div > textarea {
    background: #1e293b !important; border: 1px solid #334155 !important;
    color: #e2e8f0 !important; border-radius: 8px !important;
}
hr { border-color: #1e293b !important; }
code { font-family: 'JetBrains Mono', monospace !important;
       background: #1e293b !important; color: #f59e0b !important; }
</style>
""", unsafe_allow_html=True)


# ── SESSION STATE ──────────────────────────
if "result"         not in st.session_state: st.session_state.result = None
if "running"        not in st.session_state: st.session_state.running = False
if "history"        not in st.session_state: st.session_state.history = []
if "indexed_files"  not in st.session_state: st.session_state.indexed_files = []
if "past_briefs"    not in st.session_state: st.session_state.past_briefs = []

api_keys_ready = bool(os.getenv("GROQ_API_KEY"))


# ── SIDEBAR ────────────────────────────────
with st.sidebar:
    st.markdown("## 🎯 CompeteIQ")
    st.markdown("*Automated Competitive Intelligence*")
    st.divider()

    # Internal docs upload
    st.markdown("### 📄 Your Internal Docs")
    st.caption("Upload strategy docs, product roadmaps, pricing sheets — the agent will compare competitors against these.")

    uploaded_files = st.file_uploader(
        "Upload docs", accept_multiple_files=True, type=["txt", "pdf", "md"],
        label_visibility="collapsed",
    )

    if uploaded_files:
        current_files = [f.name for f in uploaded_files]
        if current_files != st.session_state.indexed_files:
            try:
                from vectordb.chroma_store import add_documents
                with st.spinner("Indexing..."):
                    texts = []
                    for f in uploaded_files:
                        if f.name.lower().endswith(".pdf"):
                            reader = pypdf.PdfReader(io.BytesIO(f.read()))
                            text = "\n\n".join(
                                p.extract_text() for p in reader.pages if p.extract_text()
                            )
                            texts.append(text)
                        else:
                            texts.append(f.read().decode("utf-8", errors="ignore"))
                    metadatas = [{"source": f.name} for f in uploaded_files]
                    from vectordb.chroma_store import add_documents
                    add_documents(texts, metadatas)
                    st.session_state.indexed_files = current_files
                    st.success(f"✅ {len(uploaded_files)} file(s) indexed!")
            except Exception as e:
                st.error(f"❌ {e}")

    if st.button("🗑️ Clear Docs", use_container_width=True):
        import shutil
        import gc
        # Release ChromaDB connections before deleting
        try:
            from vectordb.chroma_store import get_vector_store
            store = get_vector_store()
            store._client.clear_system_cache()
            del store
            gc.collect()
        except Exception:
            pass
        try:
            if os.path.exists("./chroma_db"):
                shutil.rmtree("./chroma_db")
            if os.path.exists("./chroma_db/bm25_docs.json"):
                os.remove("./chroma_db/bm25_docs.json")
            st.session_state.indexed_files = []
            st.success("✅ Cleared!")
            st.rerun()
        except Exception as e:
            st.warning(f"Could not fully clear — restart the app and try again. Error: {e}")


    st.divider()

    # Past briefs
    # Past briefs — loaded from disk, survive refresh
    st.markdown("### 📋 Past Briefs")
    from utils.storage import load_briefs, clear_briefs
    disk_briefs = load_briefs()

    if disk_briefs:
        for i, brief in enumerate(disk_briefs[:10]):
            col_a, col_b = st.columns([4, 1])
            with col_a:
                if st.button(f"📄 {brief['title']}", key=f"brief_{i}", use_container_width=True):
                    st.session_state.result = brief["result"]
                    st.rerun()
        if st.button("🗑️ Clear All Briefs", use_container_width=True):
            from utils.storage import clear_briefs
            import shutil
            import gc
            clear_briefs()
            try:
                from vectordb.chroma_store import get_vector_store
                store = get_vector_store()
                store._client.clear_system_cache()
                del store
                gc.collect()
            except Exception:
                pass
            try:
                if os.path.exists("./chroma_db"):
                    shutil.rmtree("./chroma_db")
                st.session_state.result = None
                st.session_state.indexed_files = []
                st.success("✅ All cleared!")
                st.rerun()
            except Exception as e:
                st.warning(f"Could not fully clear — restart the app and try again. Error: {e}")
        
    else:
        st.caption("No briefs generated yet.")

    st.divider()

    # Pipeline steps legend
    st.markdown("### ⚙️ Pipeline Steps")
    st.markdown("""
    <div style='font-size:0.82rem; color:#64748b; line-height:2'>
    🔍 <b style='color:#f59e0b'>Scraper</b> — searches web<br>
    🧠 <b style='color:#8b5cf6'>Analyzer</b> — compares docs<br>
    📊 <b style='color:#06b6d4'>Scorer</b> — rates threats 1-10<br>
    ✍️ <b style='color:#22c55e'>Reporter</b> — writes brief
    </div>
    """, unsafe_allow_html=True)


# ── MAIN AREA ──────────────────────────────
st.markdown('<p class="main-header">🎯 CompeteIQ</p>', unsafe_allow_html=True)
st.markdown('<p class="sub-header">Automated Competitive Intelligence Pipeline • Powered by Groq + LangGraph</p>', unsafe_allow_html=True)
st.divider()

if not api_keys_ready:
    st.error("❌ GROQ_API_KEY missing. Add it to your `.env` file and restart.")
    st.stop()

# ── INPUT FORM ─────────────────────────────
with st.container():
    st.markdown("### 🎯 Configure Intelligence Run")

    col1, col2 = st.columns(2)

    with col1:
        your_company = st.text_input(
            "Your Company Name",
            placeholder="e.g. Acme Corp",
            help="Used for context in the analysis",
        )
        competitors_input = st.text_area(
            "Competitors to Track",
            placeholder="One per line:\nNotion\nLinear\nJira",
            height=120,
            help="Enter each competitor on a new line",
        )

    with col2:
        focus_area = st.text_input(
            "Focus Area",
            placeholder="e.g. AI features, pricing changes, product roadmap",
            help="What specifically should the agent look for?",
        )
        extra_context = st.text_area(
            "Additional Context (optional)",
            placeholder="e.g. We are a B2B SaaS company focused on project management for remote teams. Our main differentiator is offline-first sync.",
            height=120,
            help="Tell the agent more about your business for better analysis",
        )

    run_button = st.button(
        "🚀 Run Intelligence Pipeline",
        use_container_width=True,
        disabled=st.session_state.running,
    )


# ── RUN PIPELINE ───────────────────────────
if run_button:
    # Validate inputs
    if not competitors_input.strip():
        st.error("❌ Please enter at least one competitor.")
        st.stop()
    if not focus_area.strip():
        st.error("❌ Please enter a focus area.")
        st.stop()

    competitors = [c.strip() for c in competitors_input.strip().split("\n") if c.strip()]

    if len(competitors) == 0:
        st.error("❌ No valid competitors found.")
        st.stop()

    st.session_state.running = True
    st.session_state.result = None

    # Progress display
    st.divider()
    st.markdown("### ⚡ Pipeline Running...")

    progress_bar = st.progress(0)
    status_text = st.empty()

    step_cols = st.columns(4)
    step_labels = ["🔍 Scraping Web", "🧠 Analyzing", "📊 Scoring", "✍️ Writing Brief"]
    step_placeholders = [col.empty() for col in step_cols]

    def update_step(active_step: int):
        for i, placeholder in enumerate(step_placeholders):
            if i < active_step:
                placeholder.markdown(f"""
                <div class="step-card step-done">✅ {step_labels[i]}</div>
                """, unsafe_allow_html=True)
            elif i == active_step:
                placeholder.markdown(f"""
                <div class="step-card step-active">⚡ {step_labels[i]}</div>
                """, unsafe_allow_html=True)
            else:
                placeholder.markdown(f"""
                <div class="step-card">⏳ {step_labels[i]}</div>
                """, unsafe_allow_html=True)

    try:
        from agents.pipeline import run_intelligence_pipeline

        update_step(0)
        progress_bar.progress(10)
        status_text.markdown("`🔍 Scraping competitor data from the web...`")

        # Run the full pipeline
        # We use a callback to update UI during pipeline execution
        result = run_intelligence_pipeline(
                competitors=competitors,
                focus_area=focus_area,
                your_company=your_company or "Our Company",
            )

        if not isinstance(result, dict):
            raise ValueError(f"Pipeline returned unexpected type: {type(result)}")

        for i, step in enumerate(result.get("history", [])):
            update_step(i + 1)
            progress_bar.progress(25 * (i + 1))
            time.sleep(0.3)

        
        status_text.markdown("`🔍 Running pipeline — this takes 2-3 minutes...`")

        st.session_state.result = result
        st.session_state.running = False

        # Save to past briefs
        # Save to disk — persists across refreshes
        from utils.storage import save_brief
        title = f"{', '.join(competitors[:2])} — {datetime.now().strftime('%b %d %H:%M')}"
        save_brief(title, result)
        
        time.sleep(0.5)
        st.rerun()

    except Exception as e:
        st.session_state.running = False
        progress_bar.empty()
        status_text.empty()
        st.error(f"❌ Pipeline error: {e}")


# ── DISPLAY RESULTS ────────────────────────
if st.session_state.result:
    result = st.session_state.result

    st.divider()
    st.markdown("### 📋 Intelligence Brief")

    # Tabs for different views
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📄 Full Brief", "📊 Threat Scores", "🧪 Eval & Metrics", "🔍 Raw Research", "📥 Export"
    ])

    with tab1:
        st.markdown(
            f'<div class="brief-container">{result["final_brief"]}</div>',
            unsafe_allow_html=True,
        )

    with tab2:
        st.markdown("#### Competitor Threat Scores")
        scores_text = result.get("scores_data", "")

        if scores_text:
            # Parse scores from the structured output
            blocks = scores_text.split("---")
            cols = st.columns(min(len(blocks), 3))

            for i, block in enumerate(blocks):
                if not block.strip():
                    continue
                col = cols[i % len(cols)]
                with col:
                    lines = {
                        line.split(":")[0].strip(): line.split(":", 1)[1].strip()
                        for line in block.strip().split("\n")
                        if ":" in line
                    }
                    name  = lines.get("COMPETITOR", f"Competitor {i+1}")
                    score = lines.get("SCORE", "?")
                    trend = lines.get("TREND", "?")
                    threat = lines.get("TOP THREAT", "")
                    oppty  = lines.get("TOP OPPORTUNITY", "")

                    try:
                        score_int = int(score)
                        score_class = "score-high" if score_int >= 7 else "score-medium" if score_int >= 4 else "score-low"
                    except Exception:
                        score_class = "score-medium"

                    st.markdown(f"""
                    <div class="step-card" style="text-align:center;">
                        <div style="font-size:1rem;font-weight:700;color:#e2e8f0;">{name}</div>
                        <div class="{score_class}">{score}/10</div>
                        <div style="color:#64748b;font-size:0.85rem;">Trend: {trend}</div>
                        <hr style="border-color:#334155;margin:8px 0;">
                        <div style="font-size:0.8rem;color:#f87171;">⚠️ {threat}</div>
                        <div style="font-size:0.8rem;color:#4ade80;margin-top:4px;">💡 {oppty}</div>
                    </div>
                    """, unsafe_allow_html=True)
        else:
            st.info("No scores data available.")

    with tab3:
        st.markdown("#### Pipeline Quality Metrics")

        eval_scores = result.get("eval_scores", {})
        timings     = result.get("timings", {})
        total_time  = result.get("total_time", 0)

        # ── Latency breakdown ──
        st.markdown("**⏱ Latency Breakdown**")
        if timings:
            t_cols = st.columns(len(timings))
            for i, (step, secs) in enumerate(timings.items()):
                t_cols[i].metric(f"🔹 {step.title()}", secs)
        st.metric("🕐 Total Pipeline Time", f"{total_time}s")

        st.divider()
             
        # ── Retrieval Quality ──

        # ── Retrieval Quality ──
        st.markdown("**🔍 Retrieval Quality (Hybrid Search)**")
        retrieval = eval_scores.get("retrieval", {})

        if eval_scores.get("evaluated") and retrieval:
            r1, r2, r3, r4 = st.columns(4)
            r1.metric(
                "Retrieval Score",
                f"{retrieval.get('retrieval_score', 0)}/1.0",
                help="Combined retrieval quality score",
            )
            r2.metric(
                "Keyword Coverage",
                f"{retrieval.get('keyword_coverage', 0)}/1.0",
                help="How many query keywords appear in retrieved chunks",
            )
            r3.metric(
                "Chunk Diversity",
                f"{retrieval.get('chunk_diversity', 0)}/1.0",
                help="How varied the retrieved chunks are",
            )
            r4.metric(
                "Chunks Retrieved",
                retrieval.get("chunks_retrieved", 0),
                help="Number of chunks retrieved via hybrid search",
            )

            st.markdown("**Average Chunk Length:**")
            avg_len = retrieval.get("avg_chunk_length", 0)
            st.progress(min(avg_len / 500, 1.0))
            st.caption(f"{avg_len} characters average")

            st.markdown("**Issues / Notes:**")
            for issue in retrieval.get("issues", []):
                if issue == "No issues found":
                    st.success(f"✅ {issue}")
                else:
                    st.warning(f"⚠️ {issue}")

        else:
            st.info("Upload internal docs to see retrieval quality metrics.")

        st.divider()
        from utils.observability import LANGSMITH_ENABLED
        if LANGSMITH_ENABLED:
            st.success("✅ LangSmith tracing active — view traces at https://smith.langchain.com")
        else:
            st.info("💡 Add LANGCHAIN_API_KEY to .env to enable LangSmith tracing.")
    
        st.divider()

        # ── Pipeline Info ──
        st.markdown("**⚙️ Retrieval Architecture**")
        st.markdown("""
        | Component | Technology | Purpose |
        |-----------|-----------|---------|
        | Vector Search | ChromaDB + all-MiniLM-L6-v2 | Semantic similarity |
        | Keyword Search | BM25 (rank-bm25) | Exact keyword matching |
        | Reranker | cross-encoder/ms-marco-MiniLM-L-6-v2 | Precision ranking |
        | Evaluation | Heuristic scoring | Coverage + diversity |
        """)

        st.divider()
        from utils.observability import LANGSMITH_ENABLED
        if LANGSMITH_ENABLED:
            st.success("✅ LangSmith tracing active — view traces at https://smith.langchain.com")
        else:
            st.info("💡 Add LANGCHAIN_API_KEY to .env to enable LangSmith tracing.")

    with tab4:
        with st.expander("🔍 Raw Scraped Data", expanded=False):
            st.text(result.get("scraped_data", "No scraped data."))
        with st.expander("🧠 Analysis Data", expanded=False):
            st.text(result.get("analysis_data", "No analysis data."))

    with tab5:
        st.markdown("#### Export Intelligence Brief")

        col1, col2 = st.columns(2)

        with col1:
            # Download as markdown text
            st.download_button(
                label="📄 Download as Text",
                data=result["final_brief"],
                file_name=f"intel_brief_{datetime.now().strftime('%Y%m%d_%H%M')}.txt",
                mime="text/plain",
                use_container_width=True,
            )

        with col2:
            # Download as PDF
            try:
                from utils.pdf_generator import generate_pdf
                competitors_list = [c.strip() for c in competitors_input.strip().split("\n") if c.strip()] if 'competitors_input' in dir() else ["Competitors"]
                pdf_bytes = generate_pdf(
                    brief_text=result["final_brief"],
                    competitors=competitors_list,
                    focus_area=focus_area if 'focus_area' in dir() else "",
                )
                st.download_button(
                    label="📥 Download as PDF",
                    data=pdf_bytes,
                    file_name=f"intel_brief_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                )
            except Exception as e:
                st.warning(f"PDF export unavailable: {e}")

        st.markdown("---")
        st.markdown("**Pipeline Steps Completed:**")
        for step in result.get("history", []):
            st.markdown(f"• {step}")


# ── EMPTY STATE ────────────────────────────
elif not st.session_state.running:
    st.markdown("""
    <div style="text-align:center; padding: 60px 20px; color: #475569;">
        <div style="font-size: 3rem;">🎯</div>
        <div style="font-size: 1.2rem; font-weight: 600; color: #64748b; margin-top: 12px;">
            Ready to run competitive intelligence
        </div>
        <div style="font-size: 0.9rem; margin-top: 8px;">
            Enter your competitors and focus area above, then click Run.
        </div>
        <div style="margin-top: 24px; font-size: 0.85rem; color: #334155;">
            💡 Tip: Upload your internal strategy docs in the sidebar for deeper analysis
        </div>
    </div>
    """, unsafe_allow_html=True)

# Footer
st.divider()
st.markdown("""
<div style="text-align:center;color:#334155;font-size:0.75rem;padding:8px;">
CompeteIQ • LangGraph + LangChain + Groq + ChromaDB + Tavily<br>
<span style="color:#f59e0b;">Automated Competitive Intelligence Pipeline</span>
</div>""", unsafe_allow_html=True)

