import streamlit as st
import sys
import os
import json
import traceback

sys.path.insert(0, os.path.dirname(__file__))

from utils.pdf_utils import extract_text_pdfplumber, pdf_to_base64, is_text_pdf
import modules.uc11_integrity as uc11
import modules.uc12_math as uc12
import modules.uc13_diff as uc13
import modules.uc14_injector as uc14

# ── Page config ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="AcadCheck — Validare Fișe Disciplină",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CSS ─────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@300;400;500&family=Fraunces:ital,opsz,wght@0,9..144,700;1,9..144,400&display=swap');

html, body, [class*="css"] { font-family: 'DM Mono', monospace; }
h1, h2, h3 { font-family: 'Fraunces', serif !important; }

.stApp { background: #0e0e0e; color: #e8e8e8; }

/* Sidebar */
section[data-testid="stSidebar"] {
    background: #111 !important;
    border-right: 1px solid #2a2a2a;
}

/* Cards */
.card {
    background: #161616;
    border: 1px solid #2a2a2a;
    padding: 16px 20px;
    margin-bottom: 10px;
    border-radius: 0;
}

/* Status badges */
.badge {
    display: inline-block;
    font-size: 10px;
    font-weight: 600;
    padding: 2px 10px;
    text-transform: uppercase;
    letter-spacing: 1px;
    font-family: 'DM Mono', monospace;
}
.badge-ok    { background: #1a3d2e; color: #5ef5a0; border-left: 3px solid #5ef5a0; }
.badge-warn  { background: #3d2e1a; color: #ffb347; border-left: 3px solid #ffb347; }
.badge-error { background: #3d1a1a; color: #ff5e5e; border-left: 3px solid #ff5e5e; }
.badge-info  { background: #1a2d0e; color: #c8f560; border-left: 3px solid #c8f560; }

/* Status rows */
.status-row {
    display: flex;
    align-items: flex-start;
    gap: 12px;
    padding: 10px 14px;
    margin-bottom: 6px;
    border-left: 3px solid #2a2a2a;
    background: #161616;
    font-size: 13px;
}
.status-row.ok    { border-color: #5ef5a0; }
.status-row.warn  { border-color: #ffb347; }
.status-row.error { border-color: #ff5e5e; }
.status-row.info  { border-color: #c8f560; }

.status-content { flex: 1; }
.status-title { font-weight: 500; margin-bottom: 2px; }
.status-detail { color: #666; font-size: 11px; }

/* Diff */
.diff-removed { background: #3d1a1a; color: #ff5e5e; padding: 6px 12px; margin: 3px 0; border-left: 3px solid #ff5e5e; font-size: 12px; }
.diff-added   { background: #1a3d2e; color: #5ef5a0; padding: 6px 12px; margin: 3px 0; border-left: 3px solid #5ef5a0; font-size: 12px; }
.diff-same    { color: #444; padding: 6px 12px; margin: 3px 0; font-size: 12px; }
.diff-changed { background: #3d2e1a; color: #ffb347; padding: 6px 12px; margin: 3px 0; border-left: 3px solid #ffb347; font-size: 12px; }

/* Draft fields */
.draft-field {
    display: flex;
    gap: 12px;
    padding: 6px 0;
    border-bottom: 1px solid #1e1e1e;
    font-size: 12px;
    align-items: baseline;
}
.draft-key   { color: #666; min-width: 220px; }
.draft-val   { flex: 1; }
.draft-extracted { color: #c8f560; }
.draft-todo      { color: #ffb347; font-style: italic; }
.draft-missing   { color: #ff5e5e; font-style: italic; }

/* Score circle */
.score-big {
    font-family: 'Fraunces', serif;
    font-size: 56px;
    font-weight: 700;
    line-height: 1;
}
.score-ok   { color: #5ef5a0; }
.score-warn { color: #ffb347; }
.score-err  { color: #ff5e5e; }

/* Metric cards */
.metric-row { display: flex; gap: 12px; margin-bottom: 20px; flex-wrap: wrap; }
.metric-card {
    flex: 1; min-width: 100px;
    background: #161616;
    border: 1px solid #2a2a2a;
    padding: 14px;
    text-align: center;
}
.metric-num { font-family: 'Fraunces', serif; font-size: 36px; font-weight: 700; display: block; }
.metric-lbl { font-size: 10px; text-transform: uppercase; letter-spacing: 1.5px; color: #666; }
.metric-ok   .metric-num { color: #5ef5a0; }
.metric-warn .metric-num { color: #ffb347; }
.metric-err  .metric-num { color: #ff5e5e; }
.metric-acc  .metric-num { color: #c8f560; }

/* Section headers */
.section-label {
    font-size: 10px;
    text-transform: uppercase;
    letter-spacing: 2px;
    color: #444;
    padding-bottom: 6px;
    border-bottom: 1px solid #2a2a2a;
    margin: 16px 0 10px 0;
}

/* Divider */
hr { border-color: #2a2a2a !important; }

/* Upload area cosmetics */
[data-testid="stFileUploader"] {
    background: #161616 !important;
    border: 1px dashed #2a2a2a !important;
}
</style>
""", unsafe_allow_html=True)


# ── Helpers ──────────────────────────────────────────────────────────────────
def score_color(score: int) -> str:
    if score >= 80:
        return "ok"
    elif score >= 50:
        return "warn"
    return "err"


def status_row(status: str, title: str, detail: str = ""):
    badge_labels = {"ok": "OK", "warn": "ATENȚIE", "error": "EROARE", "info": "INFO"}
    label = badge_labels.get(status, status.upper())
    detail_html = f'<div class="status-detail">{detail}</div>' if detail else ""
    st.markdown(f"""
    <div class="status-row {status}">
        <span class="badge badge-{status}">{label}</span>
        <div class="status-content">
            <div class="status-title">{title}</div>
            {detail_html}
        </div>
    </div>
    """, unsafe_allow_html=True)


def metric_card(num, label, cls="acc"):
    return f'<div class="metric-card metric-{cls}"><span class="metric-num">{num}</span><span class="metric-lbl">{label}</span></div>'


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown('<p style="font-family:Fraunces,serif;font-size:22px;color:#c8f560;font-weight:700;margin:0">AcadCheck</p>', unsafe_allow_html=True)
    st.markdown('<p style="font-size:11px;color:#444;letter-spacing:2px;text-transform:uppercase;margin:0 0 16px 0">Nivel 1 — Validare Structurală</p>', unsafe_allow_html=True)
    st.divider()

    tool = st.radio(
        "Alege instrumentul",
        options=["uc11", "uc12", "uc13", "uc14"],
        format_func=lambda x: {
            "uc11": "🛡️  1.1 · Integrity Guard",
            "uc12": "🔢  1.2 · Math Checker",
            "uc13": "📊  1.3 · Syllabus Diff",
            "uc14": "🏗️  1.4 · Competency Injector",
        }[x],
        label_visibility="collapsed",
    )

    st.divider()
    st.markdown("""
    <div style="font-size:11px;color:#444;line-height:1.8">
    <b style="color:#666">Metoda procesare PDF:</b><br>
    → Direct via Claude API<br>
    → Fallback: extracție text<br><br>
    <b style="color:#666">Model:</b> claude-opus-4-5<br>
    <b style="color:#666">Versiune:</b> 1.0.0
    </div>
    """, unsafe_allow_html=True)

    st.divider()
    if st.button("🗑️ Resetează sesiunea", use_container_width=True):
        st.session_state.clear()
        st.rerun()


# ── Main area ─────────────────────────────────────────────────────────────────

TITLES = {
    "uc11": ("🛡️ Integrity Guard", "Verificare structură și câmpuri obligatorii"),
    "uc12": ("🔢 Math Checker", "Consistență numerică — ore, ponderi, credite"),
    "uc13": ("📊 Syllabus Diff", "Comparație vizuală între versiuni"),
    "uc14": ("🏗️ Competency Injector", "Generare schelet document nou"),
}

title, subtitle = TITLES[tool]
st.markdown(f'<h1 style="font-family:Fraunces,serif;margin-bottom:4px">{title}</h1>', unsafe_allow_html=True)
st.markdown(f'<p style="color:#666;font-size:13px;margin-bottom:24px">{subtitle}</p>', unsafe_allow_html=True)

# ── Upload ────────────────────────────────────────────────────────────────────
st.markdown('<div class="section-label">Upload fișă disciplină (PDF)</div>', unsafe_allow_html=True)

if tool == "uc13":
    col1, col2 = st.columns(2)
    with col1:
        st.markdown('<p style="font-size:11px;color:#666;margin-bottom:4px">VERSIUNEA VECHE / ACTUALĂ</p>', unsafe_allow_html=True)
        pdf_main = st.file_uploader("Fișa principală", type=["pdf"], key="main_pdf", label_visibility="collapsed")
    with col2:
        st.markdown('<p style="font-size:11px;color:#666;margin-bottom:4px">VERSIUNEA NOUĂ / TEMPLATE NOU (opțional)</p>', unsafe_allow_html=True)
        pdf_compare = st.file_uploader("Fișa pentru comparație", type=["pdf"], key="compare_pdf", label_visibility="collapsed")
else:
    pdf_main = st.file_uploader(
        "Încarcă Fișa Disciplinei în format PDF",
        type=["pdf"],
        key="main_pdf",
        label_visibility="collapsed",
    )
    pdf_compare = None

# ── Info bar dacă e fișier încărcat ──────────────────────────────────────────
if pdf_main:
    size_kb = len(pdf_main.getvalue()) / 1024
    text_check = is_text_pdf(pdf_main.getvalue())
    cols = st.columns([3, 1, 1])
    with cols[0]:
        st.markdown(f'<div class="card" style="padding:10px 16px"><span style="color:#c8f560">📄 {pdf_main.name}</span> <span style="color:#444;font-size:11px">· {size_kb:.1f} KB · {"text PDF ✓" if text_check else "scanat/imagine"}</span></div>', unsafe_allow_html=True)

# ── Run button ────────────────────────────────────────────────────────────────
st.markdown("")
run_col, _ = st.columns([1, 3])
with run_col:
    run_clicked = st.button(
        f"▶ Rulează analiza",
        disabled=(pdf_main is None),
        use_container_width=True,
        type="primary",
    )

# ── Execution ─────────────────────────────────────────────────────────────────
result_key = f"result_{tool}"

if run_clicked and pdf_main:
    pdf_bytes = pdf_main.getvalue()
    pdf_b64 = pdf_to_base64(pdf_bytes)
    extracted = extract_text_pdfplumber(pdf_bytes)

    with st.spinner("Se procesează documentul..."):
        try:
            if tool == "uc11":
                result = uc11.run(pdf_bytes, pdf_b64, extracted)
            elif tool == "uc12":
                result = uc12.run(pdf_bytes, pdf_b64, extracted)
            elif tool == "uc13":
                pdf_bytes_cmp = pdf_compare.getvalue() if pdf_compare else None
                pdf_b64_cmp = pdf_to_base64(pdf_bytes_cmp) if pdf_bytes_cmp else None
                extracted_cmp = extract_text_pdfplumber(pdf_bytes_cmp) if pdf_bytes_cmp else ""
                result = uc13.run(pdf_bytes, pdf_b64, extracted, pdf_bytes_cmp, pdf_b64_cmp, extracted_cmp)
            elif tool == "uc14":
                result = uc14.run(pdf_bytes, pdf_b64, extracted)

            st.session_state[result_key] = result
        except Exception as e:
            st.error(f"Eroare la procesare: {e}")
            with st.expander("Detalii tehnice"):
                st.code(traceback.format_exc())

# ── Results ───────────────────────────────────────────────────────────────────
if result_key in st.session_state:
    result = st.session_state[result_key]
    st.divider()

    # ─────────────────── UC 1.1 ───────────────────────────────────────────────
    if tool == "uc11":
        score = result.get("scor_integritate", 0)
        sc = score_color(score)

        meta = result.get("metadata", {})
        st.markdown(f"""
        <div class="card">
        <div style="font-size:11px;color:#444;text-transform:uppercase;letter-spacing:2px;margin-bottom:8px">Document analizat</div>
        <b style="font-size:15px;color:#e8e8e8">{meta.get('disciplina','—')}</b><br>
        <span style="color:#666;font-size:12px">{meta.get('institutie','')} · {meta.get('facultate','')} · An {meta.get('an_studiu','?')} · Sem {meta.get('semestru','?')} · {meta.get('credite','?')} credite</span>
        </div>
        """, unsafe_allow_html=True)

        campuri_ok = result.get("campuri_ok", [])
        campuri_lipsa = result.get("campuri_lipsa", [])
        sectiuni = result.get("sectiuni", [])
        erori = [s for s in sectiuni if s.get("status") == "error"]
        avertismente = [s for s in sectiuni if s.get("status") == "warn"]

        st.markdown(f"""
        <div class="metric-row">
            {metric_card(score, "Scor integritate", sc)}
            {metric_card(len(campuri_ok), "Câmpuri OK", "ok")}
            {metric_card(len(campuri_lipsa), "Câmpuri lipsă", "warn" if campuri_lipsa else "ok")}
            {metric_card(len(erori), "Erori", "err" if erori else "ok")}
            {metric_card(len(avertismente), "Avertizări", "warn" if avertismente else "ok")}
        </div>
        """, unsafe_allow_html=True)

        if result.get("rezumat"):
            st.markdown(f'<div class="card" style="color:#aaa;font-size:12px;line-height:1.7"><b style="color:#666;font-size:10px;letter-spacing:2px;text-transform:uppercase">Rezumat</b><br>{result["rezumat"]}</div>', unsafe_allow_html=True)

        # Sectiuni
        st.markdown('<div class="section-label">Structura documentului</div>', unsafe_allow_html=True)
        for s in sectiuni:
            status_row(s.get("status", "info"), s.get("nume", ""), s.get("detalii", ""))

        # Campuri lipsa
        if campuri_lipsa:
            st.markdown('<div class="section-label">Câmpuri lipsă sau incomplete</div>', unsafe_allow_html=True)
            for c in campuri_lipsa:
                status_row("error", c)

        # Semnaturi
        sigs = result.get("semnaturi", {})
        if sigs:
            st.markdown('<div class="section-label">Semnături</div>', unsafe_allow_html=True)
            sig_map = {
                "decan": "Decan",
                "director_departament": "Director departament",
                "titular_curs": "Titular curs",
                "titular_seminar": "Titular seminar",
            }
            for key, label in sig_map.items():
                val = sigs.get(key, "absent")
                st_code = "ok" if val == "prezent" else ("warn" if val == "partial" else "error")
                status_row(st_code, label, val)

        # Bibliografie
        bib = result.get("bibliografie", {})
        if bib:
            st.markdown('<div class="section-label">Bibliografie</div>', unsafe_allow_html=True)
            for key, label in [("curs_prezenta", "Bibliografie curs"), ("seminar_prezenta", "Bibliografie seminar")]:
                val = bib.get(key, False)
                status_row("ok" if val else "error", label, "Prezentă" if val else "Lipsă")
            ncurs = bib.get("numar_surse_curs", 0)
            nsem = bib.get("numar_surse_seminar", 0)
            status_row("info", f"Surse curs: {ncurs} · Surse seminar: {nsem}")

        with st.expander("📋 JSON brut"):
            st.json(result)

    # ─────────────────── UC 1.2 ───────────────────────────────────────────────
    elif tool == "uc12":
        score = result.get("scor_consistenta", 0)
        sc = score_color(score)
        verificari = result.get("verificari", [])
        alerte = result.get("alerte", [])
        erori_v = [v for v in verificari if v.get("status") == "error"]
        ok_v = [v for v in verificari if v.get("status") == "ok"]
        alerte_err = [a for a in alerte if a.get("severitate") == "error"]
        alerte_warn = [a for a in alerte if a.get("severitate") == "warn"]

        st.markdown(f"""
        <div class="metric-row">
            {metric_card(score, "Scor consistență", sc)}
            {metric_card(len(ok_v), "Verificări OK", "ok")}
            {metric_card(len(erori_v), "Erori numerice", "err" if erori_v else "ok")}
            {metric_card(len(alerte_err), "Alerte critice", "err" if alerte_err else "ok")}
            {metric_card(len(alerte_warn), "Avertizări", "warn" if alerte_warn else "ok")}
        </div>
        """, unsafe_allow_html=True)

        if result.get("rezumat"):
            st.markdown(f'<div class="card" style="color:#aaa;font-size:12px;line-height:1.7"><b style="color:#666;font-size:10px;letter-spacing:2px;text-transform:uppercase">Rezumat</b><br>{result["rezumat"]}</div>', unsafe_allow_html=True)

        # Valori extrase
        vals = result.get("valori_extrase", {})
        if vals:
            st.markdown('<div class="section-label">Valori extrase din document</div>', unsafe_allow_html=True)
            col1, col2 = st.columns(2)
            items = [(k.replace("_", " ").title(), v) for k, v in vals.items() if v is not None]
            mid = len(items) // 2
            with col1:
                for lbl, val in items[:mid]:
                    st.markdown(f'<div class="draft-field"><span class="draft-key">{lbl}</span><span class="draft-val draft-extracted">{val}</span></div>', unsafe_allow_html=True)
            with col2:
                for lbl, val in items[mid:]:
                    st.markdown(f'<div class="draft-field"><span class="draft-key">{lbl}</span><span class="draft-val draft-extracted">{val}</span></div>', unsafe_allow_html=True)

        # Verificari
        st.markdown('<div class="section-label">Verificări matematice</div>', unsafe_allow_html=True)
        for v in verificari:
            st_code = v.get("status", "info")
            if st_code == "na":
                st_code = "info"
            detail = v.get("mesaj", "")
            if v.get("valoare_calculata") is not None and v.get("valoare_declarata") is not None:
                detail += f" | Calculat: {v['valoare_calculata']} · Declarat: {v['valoare_declarata']}"
            status_row(st_code, v.get("descriere", ""), detail)

        # Alerte
        if alerte:
            st.markdown('<div class="section-label">Alerte</div>', unsafe_allow_html=True)
            for a in alerte:
                sev = a.get("severitate", "info")
                if sev == "error":
                    sev = "error"
                msg = a.get("mesaj", "")
                detail = f"Câmp: {a.get('camp','')} · Găsit: {a.get('valoare_gasita','')} · Așteptat: {a.get('valoare_asteptata','')}"
                status_row(sev, msg, detail)

        with st.expander("📋 JSON brut"):
            st.json(result)

    # ─────────────────── UC 1.3 ───────────────────────────────────────────────
    elif tool == "uc13":
        nivel_impact = result.get("nivel_impact", "—")
        nr_schimbari = result.get("numar_schimbari_totale", 0)
        impact_color = {"minor": "ok", "moderat": "warn", "major": "err"}.get(nivel_impact, "info")
        sectiuni_cmp = result.get("sectiuni_comparate", [])
        modificate = [s for s in sectiuni_cmp if s.get("status") == "modificat"]
        adaugate = [s for s in sectiuni_cmp if s.get("status") == "adaugat"]
        eliminate = [s for s in sectiuni_cmp if s.get("status") == "eliminat"]
        identice = [s for s in sectiuni_cmp if s.get("status") == "identic"]

        st.markdown(f"""
        <div class="metric-row">
            {metric_card(nr_schimbari, "Schimbări totale", impact_color)}
            {metric_card(len(identice), "Secțiuni identice", "ok")}
            {metric_card(len(modificate), "Modificate", "warn" if modificate else "ok")}
            {metric_card(len(adaugate), "Adăugate", "info")}
            {metric_card(len(eliminate), "Eliminate", "err" if eliminate else "ok")}
        </div>
        """, unsafe_allow_html=True)

        st.markdown(f'<span class="badge badge-{impact_color}">Impact: {nivel_impact.upper()}</span>', unsafe_allow_html=True)
        st.markdown("")

        if result.get("rezumat_executive"):
            st.markdown(f'<div class="card" style="color:#aaa;font-size:12px;line-height:1.7"><b style="color:#666;font-size:10px;letter-spacing:2px;text-transform:uppercase">Rezumat executiv</b><br>{result["rezumat_executive"]}</div>', unsafe_allow_html=True)

        # Diff vizual
        st.markdown('<div class="section-label">Comparație secțiuni</div>', unsafe_allow_html=True)
        for s in sectiuni_cmp:
            status = s.get("status", "identic")
            css_class = {
                "identic": "diff-same",
                "modificat": "diff-changed",
                "adaugat": "diff-added",
                "eliminat": "diff-removed",
            }.get(status, "diff-same")

            icon = {"identic": "═", "modificat": "~", "adaugat": "+", "eliminat": "−"}.get(status, " ")
            desc = s.get("descriere_schimbare", "")
            vechi = s.get("continut_vechi", "")
            nou = s.get("continut_nou", "")

            st.markdown(f"""
            <div class="{css_class}">
                <b>[{icon}] {s.get("sectiune","")}</b>
                {f'<br><span style="opacity:.7;font-size:11px">{desc}</span>' if desc else ""}
                {f'<br><span style="opacity:.5;font-size:10px">VECHI: {vechi[:100]}</span>' if vechi and vechi != "N/A - comparatie cu standard" and status == "modificat" else ""}
                {f'<br><span style="opacity:.5;font-size:10px">NOU: {nou[:100]}</span>' if nou and status == "modificat" else ""}
            </div>
            """, unsafe_allow_html=True)

        # Campuri modificate numeric/textual
        campuri_mod = result.get("campuri_modificate", [])
        if campuri_mod:
            st.markdown('<div class="section-label">Câmpuri modificate</div>', unsafe_allow_html=True)
            for c in campuri_mod:
                status_row(
                    "warn",
                    c.get("camp", ""),
                    f'{c.get("valoare_veche","?")} → {c.get("valoare_noua","?")} [{c.get("tip_schimbare","")}]',
                )

        # Avertizari importante
        avert = result.get("avertizari_importante", [])
        if avert:
            st.markdown('<div class="section-label">⚠️ Avertizări importante pentru profesor</div>', unsafe_allow_html=True)
            for a in avert:
                status_row(
                    "warn",
                    a.get("mesaj", ""),
                    a.get("actiune_necesara", ""),
                )

        with st.expander("📋 JSON brut"):
            st.json(result)

    # ─────────────────── UC 1.4 ───────────────────────────────────────────────
    elif tool == "uc14":
        completitudine = result.get("completitudine_procent", 0)
        sc = score_color(completitudine)
        campuri_preluate = result.get("campuri_preluate", [])
        campuri_todo = result.get("campuri_de_completat", [])
        recomandari = result.get("recomandari", [])
        draft = result.get("draft", {})

        st.markdown(f"""
        <div class="metric-row">
            {metric_card(completitudine, "Completitudine %", sc)}
            {metric_card(len(campuri_preluate), "Câmpuri preluate", "ok")}
            {metric_card(len(campuri_todo), "De completat", "warn" if campuri_todo else "ok")}
            {metric_card(len(draft), "Secțiuni", "acc")}
        </div>
        """, unsafe_allow_html=True)

        if result.get("nota_an_universitar"):
            st.markdown(f'<div class="card" style="border-left:3px solid #ffb347;color:#ffb347;font-size:12px">⚠️ {result["nota_an_universitar"]}</div>', unsafe_allow_html=True)

        # Draft sectiuni
        st.markdown('<div class="section-label">Schelet generat</div>', unsafe_allow_html=True)

        for sec_key, sec_data in draft.items():
            if not isinstance(sec_data, dict):
                continue
            sec_title = sec_data.get("titlu", sec_key)
            campuri = sec_data.get("campuri", {})
            if not campuri:
                # sectiuni cu structura diferita (preconditii, etc)
                campuri_alt = {k: v for k, v in sec_data.items() if k != "titlu" and isinstance(v, dict)}
                campuri = campuri_alt

            with st.expander(f"📌 {sec_title}", expanded=(sec_key in ["sectiunea_1", "sectiunea_2", "sectiunea_3"])):
                for camp_key, camp_data in campuri.items():
                    if not isinstance(camp_data, dict):
                        continue
                    sursa = camp_data.get("sursa", "lipsa")
                    valoare = camp_data.get("valoare", "")
                    nota = camp_data.get("nota", "")
                    label = camp_key.replace("_", " ").title()

                    if sursa == "extras" and valoare:
                        val_display = str(valoare)[:120] if isinstance(valoare, str) else json.dumps(valoare, ensure_ascii=False)[:120]
                        css = "draft-extracted"
                        icon = "✓"
                    elif sursa == "de_completat":
                        val_display = "[ de completat ]"
                        css = "draft-todo"
                        icon = "○"
                    else:
                        val_display = "[ lipsă ]"
                        css = "draft-missing"
                        icon = "✗"

                    nota_html = f'<span style="color:#444;font-size:10px;margin-left:8px">{nota}</span>' if nota else ""
                    st.markdown(
                        f'<div class="draft-field"><span class="draft-key">{icon} {label}</span>'
                        f'<span class="draft-val {css}">{val_display}{nota_html}</span></div>',
                        unsafe_allow_html=True,
                    )

        # Recomandari
        if recomandari:
            st.markdown('<div class="section-label">Recomandări</div>', unsafe_allow_html=True)
            for r in recomandari:
                status_row("info", r)

        # De completat
        if campuri_todo:
            st.markdown('<div class="section-label">Câmpuri de completat manual</div>', unsafe_allow_html=True)
            for c in campuri_todo:
                status_row("warn", c)

        with st.expander("📋 JSON brut"):
            st.json(result)
