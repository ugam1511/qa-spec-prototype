import streamlit as st
import pandas as pd
import fitz
import io
from datetime import date, datetime
import uuid
import gspread
from google.oauth2.service_account import Credentials

# ============================================================
# 1. PAGE CONFIG + STYLING
# ============================================================

st.set_page_config(page_title="SpecStream", layout="wide")

st.markdown("""
<style>
body { background-color:#F4F7FA; }

.hero-card {
    background: linear-gradient(135deg, #111827 0%, #1D4ED8 100%);
    color:white;
    padding:30px;
    border-radius:20px;
    margin-bottom:22px;
    box-shadow:0 8px 24px rgba(0,0,0,0.12);
}
.hero-card h1 { color:white; margin-bottom:4px; font-size:40px; }
.hero-card p { color:#E5E7EB; font-size:16px; }

.section-title {
    font-size:22px;
    font-weight:800;
    color:#111827;
    margin-top:18px;
    margin-bottom:10px;
}

.kpi-card {
    background:white;
    border:1px solid #E5E7EB;
    border-radius:18px;
    padding:20px;
    box-shadow:0 2px 10px rgba(0,0,0,0.06);
    min-height:120px;
}
.kpi-label { color:#6B7280; font-size:13px; font-weight:700; }
.kpi-value { color:#111827; font-size:32px; font-weight:900; margin-top:6px; }
.kpi-note { color:#6B7280; font-size:12px; margin-top:4px; }

.module-card-clean {
    background:white;
    border:1px solid #E5E7EB;
    border-radius:20px;
    padding:22px 18px;
    height:210px;
    box-sizing:border-box;
    box-shadow:0 2px 10px rgba(0,0,0,0.06);
    margin-bottom:4px;
    transition: all 0.18s ease-in-out;
}
.module-card-clean:hover {
    transform: translateY(-4px);
    border-color:#2563EB;
    box-shadow:0 10px 24px rgba(37,99,235,0.18);
}
.module-title-clean {
    text-align:center;
    font-size:22px;
    font-weight:900;
    color:#111827;
    margin-bottom:14px;
}
.module-desc-clean {
    text-align:center;
    color:#6B7280;
    font-size:14px;
    line-height:1.45;
}

/* Hide the visible Streamlit button but keep it clickable */
div[data-testid="stButton"] > button[kind="secondary"] {
    background: transparent;
    color: transparent;
    border: 0;
    height: 0px;
    padding: 0;
    margin: 0;
}

.panel-card {
    background:white;
    border:1px solid #E5E7EB;
    border-radius:18px;
    padding:18px;
    box-shadow:0 2px 10px rgba(0,0,0,0.06);
    margin-bottom:16px;
}

.workload-item {
    border-left:5px solid #2563EB;
    padding:10px 12px;
    margin-bottom:10px;
    background:#F9FAFB;
    border-radius:10px;
}
.email-action {
    border-left:5px solid #F59E0B;
    padding:10px 12px;
    margin-bottom:10px;
    background:#FFFBEB;
    border-radius:10px;
}
.activity-item {
    padding:9px 0;
    border-bottom:1px solid #E5E7EB;
}

.status-pill-green {
    background:#DCFCE7; color:#166534; padding:5px 10px;
    border-radius:999px; font-size:12px; font-weight:800;
}
.status-pill-yellow {
    background:#FEF3C7; color:#92400E; padding:5px 10px;
    border-radius:999px; font-size:12px; font-weight:800;
}
.status-pill-red {
    background:#FEE2E2; color:#991B1B; padding:5px 10px;
    border-radius:999px; font-size:12px; font-weight:800;
}
.status-pill-blue {
    background:#DBEAFE; color:#1E40AF; padding:5px 10px;
    border-radius:999px; font-size:12px; font-weight:800;
}

.field-card {
    border:1px solid #d9dee5;
    border-radius:12px;
    padding:14px;
    margin-bottom:12px;
    background:#fff;
    box-shadow:0 1px 4px rgba(0,0,0,0.05);
}
.table-header {
    font-weight:700;
    background-color:#eef1f5;
    padding:10px;
    border-radius:8px;
    margin-bottom:10px;
}
.source-text { font-size:12px; color:#666; }
.conf-high {
    border:1px solid #ccc; padding:7px; border-radius:7px;
    text-align:center; font-weight:bold;
}
.conf-medium {
    background-color:#fff3cd; color:#856404; border:1px solid #ffeeba;
    padding:7px; border-radius:7px; text-align:center; font-weight:bold;
}
.conf-low {
    background-color:#f8d7da; color:#721c24; border:1px solid #f5c6cb;
    padding:7px; border-radius:7px; text-align:center; font-weight:bold;
}
.save-card {
    border:1px solid #badbcc;
    background-color:#d1e7dd;
    color:#0f5132;
    border-radius:12px;
    padding:18px;
    margin-top:18px;
}
.placeholder-box {
    background:white;
    border:1px solid #E5E7EB;
    border-radius:18px;
    padding:20px;
    box-shadow:0 2px 10px rgba(0,0,0,0.06);
    margin-bottom:16px;
}
</style>
""", unsafe_allow_html=True)

# ============================================================
# 2. CONSTANTS
# ============================================================

EXPORT_COLUMNS = [
    "SKU", "Name", "Supplier code", "Celery", "Cereals", "Crustaceans", "Eggs", "Fish", "Lupin", "Milk",
    "Molluscs", "Mustard", "Nuts", "Peanuts", "Sesame Seeds", "Soya", "Sulphur dioxide",
    "Vegetarian", "Vegan", "Contains GM Protein/DNA", "Palm oil", "Coeliacs", "Halal", "Kosher", "Organic",
    "KJ", "Kcal", "Fat", "Saturates", "Carbs", "Sugars", "Fibre", "Protein", "Salt", "Ingredients table"
]

DISPLAY_FIELDS = [c for c in EXPORT_COLUMNS if c not in ["SKU", "Supplier code"]]

ALLERGEN_FIELDS = [
    "Celery", "Cereals", "Crustaceans", "Eggs", "Fish", "Lupin", "Milk",
    "Molluscs", "Mustard", "Nuts", "Peanuts", "Sesame Seeds", "Soya", "Sulphur dioxide"
]

# ============================================================
# 3. GOOGLE SHEETS FUNCTIONS
# ============================================================

def get_google_sheet():
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_info(dict(st.secrets["gcp_service_account"]), scopes=scopes)
    client = gspread.authorize(creds)
    return client.open(st.secrets["google"]["sheet_name"])


def append_to_sheet(tab_name, row_dict, sheet=None):
    if sheet is None:
        sheet = get_google_sheet()
    ws = sheet.worksheet(tab_name)
    headers = ws.row_values(1)
    ws.append_row([row_dict.get(h, "") for h in headers], value_input_option="USER_ENTERED")

# ============================================================
# 4. EXTRACTION FUNCTIONS
# ============================================================

def confidence_class(conf):
    return {"High": "conf-high", "Medium": "conf-medium", "Low": "conf-low"}.get(conf, "conf-high")


def extract_pdf_text(pdf_bytes):
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    return [{"page": i + 1, "text": page.get_text()} for i, page in enumerate(doc)]


def row(field, value, confidence="High", page=1, sources=None):
    return {"Field": field, "Value": value, "Confidence": confidence, "Page": page, "Sources": sources or []}


def normalise_rows(raw_rows):
    by_field = {r["Field"]: r for r in raw_rows}
    final = []
    for field in DISPLAY_FIELDS:
        if field in by_field:
            final.append(by_field[field])
        elif field in ALLERGEN_FIELDS:
            final.append(row(field, "No", "Medium", 1, ["No evidence extracted in mock mode"]))
        else:
            final.append(row(field, "", "Low", 1, ["Field not extracted in mock mode"]))
    return final


def mock_extract(pages):
    joined = "\n".join(p["text"] for p in pages).lower()

    if "ground cumin" in joined:
        raw = [
            row("Name", "GROUND CUMIN", "High", 1, ["Product Name GROUND CUMIN"]),
            row("Ingredients table", "Cumin", "High", 1, ["Ingredients declaration Cumin"]),
            row("Celery", "No", "High", 4, ["Celery", "Present in Product No"]),
            row("Cereals", "No", "High", 4, ["Cereals containing gluten", "Present in Product No"]),
            row("Crustaceans", "No", "High", 4, ["Crustaceans", "Present in Product No"]),
            row("Eggs", "No", "High", 4, ["Egg", "Present in Product No"]),
            row("Fish", "No", "High", 4, ["Fish", "Present in Product No"]),
            row("Lupin", "No", "High", 4, ["Lupin", "Present in Product No"]),
            row("Milk", "No", "High", 4, ["Milk and dairy products", "Present in Product No"]),
            row("Molluscs", "No", "High", 4, ["Molluscs", "Present in Product No"]),
            row("Mustard", "No", "High", 4, ["Mustard", "Present in Product No"]),
            row("Nuts", "No", "Medium", 5, ["Nut & Peanut Statement"]),
            row("Peanuts", "May Contain", "Medium", 4, ["Peanuts", "Possible airborne cross contamination"]),
            row("Sesame Seeds", "No", "High", 4, ["Sesame Seeds", "Present in Product No"]),
            row("Soya", "No", "High", 4, ["Soybeans", "Present in Product No"]),
            row("Sulphur dioxide", "No", "High", 4, ["Sulphur dioxide", "Present in Product No"]),
            row("Vegetarian", "Suitable", "High", 3, ["Vegetarians YES"]),
            row("Vegan", "Suitable", "High", 3, ["Vegans YES"]),
            row("Contains GM Protein/DNA", "No", "High", 5, ["This product needs declaration as GMO No"]),
            row("Palm oil", "No", "High", 1, ["Ingredients declaration Cumin"]),
            row("Coeliacs", "Suitable (claimed)", "High", 3, ["Coeliacs YES"]),
            row("Halal", "Suitable (not certified)", "High", 3, ["Halal YES", "Not Certified"]),
            row("Kosher", "Suitable (not certified)", "High", 3, ["Kosher YES", "Not Certified"]),
            row("Organic", "No", "High", 5, ["No organic claim found"]),
            row("KJ", "1783", "High", 3, ["kj 1783"]),
            row("Kcal", "427", "High", 3, ["kcal 427"]),
            row("Fat", "22.3", "High", 3, ["Fat (g) 22.3"]),
            row("Saturates", "1.5", "High", 3, ["Saturates (g) 1.5"]),
            row("Carbs", "33.7", "High", 3, ["Carbohydrate (g) 33.7"]),
            row("Sugars", "2.3", "High", 3, ["Sugar (g) 2.3"]),
            row("Fibre", "Not stated", "Medium", 3, ["Nutrition information per 100g"]),
            row("Protein", "17.8", "High", 3, ["Protein (g) 17.8"]),
            row("Salt", "0.42", "High", 3, ["Salt (g) 0.42"]),
        ]
        return normalise_rows(raw)

    if "ananas" in joined or "pineapple" in joined:
        raw = [
            row("Name", "Pineapple Paste", "High", 1, ["ANANAS", "PINEAPPLE"]),
            row("Ingredients table", "Glucose syrup, Saccharose syrup, Citric acid, Vegetable fibre (Inulin), Flavours, Pectin, E100, E160b", "High", 1, ["GLUCOSE SYRUP", "SACCHAROSE SYRUP", "CITRIC ACID", "VEGETABLE FIBER", "FLAVOURS", "PECTIN", "E100", "E160b"]),
            row("Milk", "May Contain", "High", 1, ["MILK", "MAY CONTAIN TRACES"]),
            row("Nuts", "May Contain", "High", 1, ["SHELLED NUTS"]),
            row("Soya", "May Contain", "High", 1, ["SOY"]),
            row("Vegetarian", "Suitable", "High", 1, ["Composition"]),
            row("Vegan", "Suitable", "Medium", 1, ["FLAVOURS"]),
            row("Contains GM Protein/DNA", "No", "High", 1, ["It doesn't contain OGM ingredients"]),
            row("Palm oil", "Review Required", "Medium", 1, ["FLAVOURS"]),
            row("Coeliacs", "Suitable", "High", 1, ["No gluten-containing ingredients identified"]),
            row("Halal", "No", "High", 1, ["No halal statement found"]),
            row("Kosher", "No", "High", 1, ["No kosher statement found"]),
            row("Organic", "No", "High", 1, ["No organic claim found"]),
            row("KJ", "1160.11", "High", 1, ["1160,11 Kj"]),
            row("Kcal", "277.36", "High", 1, ["277,36 Kcal"]),
            row("Fat", "0.39", "High", 1, ["FATS 0,39"]),
            row("Saturates", "0.04", "High", 1, ["saturated 0,04"]),
            row("Carbs", "67.79", "High", 1, ["CARBOHYDRATES 67,79"]),
            row("Sugars", "67.51", "High", 1, ["sugars 67,51"]),
            row("Fibre", "0.38", "High", 1, ["FIBER 0,38"]),
            row("Protein", "0.76", "High", 1, ["PROTEINS 0,76"]),
            row("Salt", "0", "High", 1, ["SALT 0 g"]),
        ]
        return normalise_rows(raw)

    if "bresaola" in joined or "punta d'anca" in joined or "punta d’anca" in joined:
        raw = [
            row("Name", "BRESAOLA INTERA – PUNTA D'ANCA – VACUUM PACKED", "High", 1, ["BRESAOLA INTERA", "PUNTA D’ANCA", "VACUUM PACKED"]),
            row("Ingredients table", "Beef, Salt, Dextrose, Natural flavours, Sodium nitrite (E250), Potassium nitrate (E252)", "High", 1, ["Carne bovina", "Beef", "Sale", "Salt", "Destrosio", "Dextrose", "Aromi naturali", "Natural flavours", "E250", "E252"]),
            row("Celery", "No", "High", 3, ["Sedano", "Celery"]),
            row("Cereals", "No", "High", 4, ["SENZA GLUTINE", "GLUTENFREI"]),
            row("Crustaceans", "No", "High", 3, ["Crostacei", "Crustaceans"]),
            row("Eggs", "No", "High", 3, ["Uova", "Eggs"]),
            row("Fish", "No", "High", 3, ["Pesce", "Fish"]),
            row("Lupin", "No", "High", 3, ["Lupini", "Lupins"]),
            row("Milk", "No", "High", 3, ["Latte", "Milk"]),
            row("Molluscs", "No", "High", 3, ["Molluschi", "Shellfish"]),
            row("Mustard", "No", "High", 3, ["Senape", "Mustard"]),
            row("Nuts", "No", "High", 3, ["Frutta a guscio", "Nuts"]),
            row("Peanuts", "No", "High", 3, ["Arachidi", "Peanuts"]),
            row("Sesame Seeds", "No", "High", 3, ["Semi di sesamo", "Sesame"]),
            row("Soya", "No", "High", 3, ["Soia", "Soy"]),
            row("Sulphur dioxide", "No", "High", 3, ["Anidride solforosa", "Sulphites"]),
            row("Vegetarian", "No", "High", 1, ["Carne bovina", "Beef"]),
            row("Vegan", "No", "High", 1, ["Carne bovina", "Beef"]),
            row("Contains GM Protein/DNA", "No", "High", 3, ["OGM", "GMO", "NO"]),
            row("Palm oil", "Review Required", "Medium", 1, ["Aromi naturali", "Natural flavours"]),
            row("Coeliacs", "Suitable (claimed)", "High", 4, ["SENZA GLUTINE", "GLUTENFREI"]),
            row("Halal", "No", "High", 4, ["if raw material has been butchered with Halal rite", "Lot code encoding"]),
            row("Kosher", "No", "High", 1, ["No kosher statement found"]),
            row("Organic", "No", "High", 1, ["No organic claim found"]),
            row("KJ", "665", "High", 2, ["Energy value", "KJ", "665"]),
            row("Kcal", "159", "High", 2, ["Energy value", "Kcal", "159"]),
            row("Fat", "4", "High", 2, ["Grassi", "Fat", "4"]),
            row("Saturates", "1", "High", 2, ["saturated fatty acids", "1"]),
            row("Carbs", "<1", "High", 2, ["Carbohydrates", "< 1"]),
            row("Sugars", "<1", "High", 2, ["of which sugars", "< 1"]),
            row("Fibre", "0", "High", 2, ["Fibre", "Fibers", "0"]),
            row("Protein", "30", "High", 2, ["Proteins", "30"]),
            row("Salt", "3.7", "High", 2, ["Sale", "Salt", "3,7"]),
        ]
        return normalise_rows(raw)

    return normalise_rows([row("Name", "Not extracted", "Low", 1, ["Unknown document format in mock mode"])])


def render_highlighted_page(pdf_bytes, page_number, source_terms):
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    page = doc[page_number - 1]
    hit_count = 0
    for term in source_terms:
        if not term:
            continue
        rects = page.search_for(term)
        if not rects:
            for word in term.split()[:6]:
                rects.extend(page.search_for(word))
        for rect in rects:
            annot = page.add_highlight_annot(rect)
            annot.update()
            hit_count += 1
    pix = page.get_pixmap(matrix=fitz.Matrix(1.7, 1.7), alpha=False)
    return pix.tobytes("png"), hit_count

# ============================================================
# 5. SAVE + EXPORT FUNCTIONS
# ============================================================

def make_export_row(metadata, edited_values):
    export_row = {col: "" for col in EXPORT_COLUMNS}
    export_row["SKU"] = metadata["sku"]
    export_row["Name"] = metadata["name"]
    export_row["Supplier code"] = metadata["supplier_code"]
    for field, value in edited_values.items():
        if field in export_row:
            export_row[field] = value
    return pd.DataFrame([export_row], columns=EXPORT_COLUMNS)


def build_extracted_data_row(spec_id, metadata, edited_values, rows):
    export_row = make_export_row(metadata, edited_values).iloc[0].to_dict()
    medium_low_count = sum(1 for r in rows if r["Confidence"] in ["Medium", "Low"])
    evidence = [{"Field": r["Field"], "Confidence": r["Confidence"], "Source_Page": r["Page"], "Source_Text": r["Sources"]} for r in rows]

    extracted_row = {
        "Spec_ID": spec_id,
        "SKU": metadata["sku"],
        "Name": metadata["name"],
        "Supplier_Code": metadata["supplier_code"],
        "Confidence_Summary": f"{medium_low_count} fields require review",
        "Review_Required": "Yes" if medium_low_count > 0 else "No",
        "Evidence_JSON": str(evidence)
    }

    for col in EXPORT_COLUMNS:
        if col == "Supplier code":
            continue
        extracted_row[col] = export_row.get(col, "")

    return extracted_row


def save_to_google_sheets(metadata, edited_values, rows, uploaded_filename):
    spec_id = "SPEC-" + datetime.now().strftime("%Y%m%d-%H%M%S") + "-" + str(uuid.uuid4())[:8].upper()
    medium_low_count = sum(1 for r in rows if r["Confidence"] in ["Medium", "Low"])

    product_record = {"SKU": metadata["sku"], "Product_Name": metadata["name"], "Product_Status": "Active", "Notes": ""}
    supplier_record = {"Supplier_Code": metadata["supplier_code"], "Supplier_Name": metadata["supplier_name"], "Supplier_Status": "Active", "Notes": ""}

    specification_record = {
        "Spec_ID": spec_id,
        "SKU": metadata["sku"],
        "Supplier_Code": metadata["supplier_code"],
        "Spec_Status": "Current",
        "Version": "1",
        "File_Name": uploaded_filename,
        "Drive_Path": f"Specifications/{metadata['supplier_code']}/{metadata['sku']}.pdf",
        "Upload_Date": metadata["upload_date"],
        "Archive_Date": ""
    }

    extracted_data_row = build_extracted_data_row(spec_id, metadata, edited_values, rows)

    sheet = get_google_sheet()
    append_to_sheet("Products", product_record, sheet)
    append_to_sheet("Suppliers", supplier_record, sheet)
    append_to_sheet("Specifications", specification_record, sheet)
    append_to_sheet("Extracted_Data", extracted_data_row, sheet)

    return {
        "spec_id": spec_id,
        "sku": metadata["sku"],
        "product_name": metadata["name"],
        "supplier_code": metadata["supplier_code"],
        "supplier_name": metadata["supplier_name"],
        "spec_status": "Current",
        "version": "1",
        "upload_date": metadata["upload_date"],
        "extraction_status": "Pending Review" if medium_low_count > 0 else "Reviewed",
        "fields_extracted": len(rows),
        "fields_requiring_review": medium_low_count
    }

# ============================================================
# 6. REUSABLE UI COMPONENTS
# ============================================================

def kpi_card(label, value, note):
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-label">{label}</div>
        <div class="kpi-value">{value}</div>
        <div class="kpi-note">{note}</div>
    </div>
    """, unsafe_allow_html=True)


def clickable_module(name, desc, mode, icon):
    st.markdown(
        f"""
        <div class="module-card-clean">
            <div class="module-title-clean">{icon}<br>{name}</div>
            <div class="module-desc-clean">{desc}</div>
        </div>
        """,
        unsafe_allow_html=True
    )

    if st.button(" ", key=f"module_{mode}", use_container_width=True):
        st.session_state["mode"] = mode
        st.rerun()


def module_placeholder(title, description, fields, workflows, automation):
    if st.button("← Back to dashboard"):
        st.session_state["mode"] = "home"
        st.rerun()

    st.title(title)
    st.write(description)

    st.markdown('<div class="placeholder-box">', unsafe_allow_html=True)
    st.subheader("What this module will manage")
    for item in workflows:
        st.write(f"• {item}")
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="placeholder-box">', unsafe_allow_html=True)
    st.subheader("Core fields")
    for f in fields:
        st.text_input(f, disabled=True)
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="placeholder-box">', unsafe_allow_html=True)
    st.subheader("Future automation")
    for item in automation:
        st.write(f"• {item}")
    st.markdown('</div>', unsafe_allow_html=True)

# ============================================================
# 7. PAGE FUNCTIONS
# ============================================================

def dashboard_page():
    st.markdown("""
    <div class="hero-card">
        <h1>SpecStream</h1>
        <p>Food Quality Management System — specifications, complaints, quality events, communications, audits, environmental monitoring and NPD in one connected platform.</p>
    </div>
    """, unsafe_allow_html=True)

    search_text = st.text_input(
        "🔍 Search products, suppliers, specifications, complaints, CAPA, audits or communications",
        placeholder="Example: SKU, supplier code, product name, customer, allergen, complaint ID..."
    )

    if search_text:
        st.info("Search results will be activated in Stage 2. This bar will search across all QMS records.")

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        kpi_card("Total Specifications", "1,284", "Across all suppliers")
    with c2:
        kpi_card("Current Workload", "47", "Open tasks across QA")
    with c3:
        kpi_card("Email Actions", "23", "Detected from inbox")
    with c4:
        kpi_card("Approved Suppliers", "96", "Active supplier base")

    st.markdown('<div class="section-title">Current Workload</div>', unsafe_allow_html=True)
    w1, w2, w3 = st.columns(3)

    with w1:
        st.markdown("""
        <div class="panel-card">
            <h4>Open Technical Reviews</h4>
            <div class="workload-item"><b>14</b> specification fields requiring QA review</div>
            <div class="workload-item"><b>7</b> supplier documents due for renewal</div>
            <div class="workload-item"><b>3</b> formulations requiring confirmation</div>
        </div>
        """, unsafe_allow_html=True)

    with w2:
        st.markdown("""
        <div class="panel-card">
            <h4>Open Quality Records</h4>
            <div class="workload-item"><b>6</b> open complaints</div>
            <div class="workload-item"><b>5</b> open CAPA / quality events</div>
            <div class="workload-item"><b>4</b> internal audit actions due</div>
        </div>
        """, unsafe_allow_html=True)

    with w3:
        st.markdown("""
        <div class="panel-card">
            <h4>Supplier / Customer Follow-up</h4>
            <div class="workload-item"><b>9</b> supplier responses awaiting review</div>
            <div class="workload-item"><b>4</b> customer forms awaiting completion</div>
            <div class="workload-item"><b>2</b> certificates requested by customers</div>
        </div>
        """, unsafe_allow_html=True)

    left, right = st.columns([0.62, 0.38])

    with left:
        st.markdown('<div class="section-title">QMS Modules</div>', unsafe_allow_html=True)

        modules = [
            ("Specifications", "AI-assisted specification extraction, review, evidence checking and export.", "specifications", "📄"),
            ("Complaints", "Customer complaint records, evidence, product links, supplier links and status tracking.", "complaints", "⚠️"),
            ("CAPA / Quality Events", "Internal incidents, recalls, date extensions, holds, concessions and quality events.", "capa", "✅"),
            ("Supplier Communications", "Supplier emails, certificates, specification requests, contacts and technical communication history.", "supplier_comms", "🏭"),
            ("Customer Communications", "Customer requests, certificates, forms, questionnaires and recurring technical responses.", "customer_comms", "🤝"),
            ("Environmental Monitoring", "Sampling schedules, results, failures, retests, trends and corrective actions.", "environment", "🧪"),
            ("Internal Audits", "Audit schedules, checklists, findings, non-conformances and closures.", "audits", "📋"),
            ("NPD", "New product development workflow, trials, specs, artwork, allergen/nutrition checks and launch approvals.", "npd", "🚀"),
            ("KPI Trends", "Management view of trends, open workload, supplier performance and quality indicators.", "kpis", "📊"),
            ("Email Actions", "Future Outlook-linked inbox scan that classifies emails into actionable QMS tasks.", "email_actions", "📧"),
        ]

        mcols = st.columns(2, gap="small")

        for idx, (name, desc, mode, icon) in enumerate(modules):
            with mcols[idx % 2]:
                clickable_module(name, desc, mode, icon)

    with right:
        st.markdown('<div class="section-title">Email Actions</div>', unsafe_allow_html=True)
        st.markdown("""
        <div class="panel-card">
            <div class="email-action"><b>Complaint notification detected</b><br>Customer email mentions foreign body and attached images.</div>
            <div class="email-action"><b>Supplier certificate received</b><br>BRC certificate attached. Suggested action: file under supplier approval.</div>
            <div class="email-action"><b>Customer questionnaire request</b><br>Nutrition/allergen form attached. Suggested action: customer communication.</div>
            <div class="email-action"><b>Updated specification received</b><br>Supplier has sent a revised PDF specification.</div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown('<div class="section-title">Recent Activity</div>', unsafe_allow_html=True)
        st.markdown("""
        <div class="panel-card">
            <div class="activity-item">09:15 — Ground Cumin specification reviewed <span class="status-pill-green">Approved</span></div>
            <div class="activity-item">09:02 — Pineapple Paste saved to database <span class="status-pill-yellow">Review</span></div>
            <div class="activity-item">Yesterday — Bresaola specification extracted <span class="status-pill-green">Complete</span></div>
            <div class="activity-item">Yesterday — Complaint workflow added <span class="status-pill-blue">Planned</span></div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown('<div class="section-title">System Status</div>', unsafe_allow_html=True)
        st.success("Google Sheets database connected")
        st.info("Production plan: Microsoft login, SharePoint, Azure SQL and approved AI API")


def kpi_page():
    if st.button("← Back to dashboard"):
        st.session_state["mode"] = "home"
        st.rerun()

    st.title("KPI Trends")
    st.write("This page will become the management dashboard for QA performance, supplier trends and workload visibility.")

    c1, c2 = st.columns(2)

    with c1:
        st.subheader("Complaints by Month")
        df = pd.DataFrame({"Month": ["Jan", "Feb", "Mar", "Apr", "May", "Jun"], "Complaints": [8, 6, 9, 5, 7, 4]})
        st.line_chart(df.set_index("Month"))

        st.subheader("Specification Review Status")
        df2 = pd.DataFrame({"Status": ["Approved", "Pending", "Review Required", "Expired"], "Count": [984, 214, 61, 25]})
        st.bar_chart(df2.set_index("Status"))

    with c2:
        st.subheader("CAPA / Quality Events")
        df3 = pd.DataFrame({"Month": ["Jan", "Feb", "Mar", "Apr", "May", "Jun"], "Events": [3, 4, 2, 6, 5, 3]})
        st.line_chart(df3.set_index("Month"))

        st.subheader("Supplier Document Compliance")
        df4 = pd.DataFrame({"Category": ["Current", "Due Soon", "Expired"], "Count": [84, 9, 3]})
        st.bar_chart(df4.set_index("Category"))

    st.markdown('<div class="placeholder-box">', unsafe_allow_html=True)
    st.subheader("Future KPI examples")
    st.write("• Complaint rate by product / supplier")
    st.write("• CAPA closure time")
    st.write("• Supplier response time")
    st.write("• Specification review backlog")
    st.write("• Audit non-conformance trends")
    st.write("• Environmental monitoring failures and retests")
    st.write("• Customer questionnaire workload")
    st.markdown('</div>', unsafe_allow_html=True)


def email_actions_page():
    if st.button("← Back to dashboard"):
        st.session_state["mode"] = "home"
        st.rerun()

    st.title("Email Actions")
    st.write("This module represents the future Outlook-linked inbox scan. It will identify emails that need QA action and classify them automatically.")

    st.markdown('<div class="placeholder-box">', unsafe_allow_html=True)
    st.subheader("How it will work")
    st.write("• Scan emails received by the associated user or shared QA mailbox")
    st.write("• Classify emails as complaint, supplier certificate, specification update, customer form request, audit evidence, or general QA communication")
    st.write("• Extract suggested customer, supplier, product code and attachments")
    st.write("• Create an action card for the user to acknowledge")
    st.write("• Once acknowledged, move the item into the relevant QMS module or workload queue")
    st.markdown('</div>', unsafe_allow_html=True)

    st.subheader("Example detected email actions")

    examples = [
        ("Complaint notification", "Customer reports foreign body with attached images.", "Suggested: Create Complaint"),
        ("Supplier certificate received", "BRC certificate attached from SUP014.", "Suggested: File under Supplier Communications"),
        ("Updated specification", "Supplier sent revised specification for SKU ABC123.", "Suggested: Add Updated Specification"),
        ("Customer questionnaire", "Customer asks for nutrition and allergen form completion.", "Suggested: Create Customer Communication"),
    ]

    for title, desc, action in examples:
        st.markdown('<div class="email-action">', unsafe_allow_html=True)
        st.markdown(f"**{title}**")
        st.write(desc)
        st.info(action)
        st.markdown('</div>', unsafe_allow_html=True)


def specifications_module():
    if st.button("← Back to dashboard"):
        st.session_state["mode"] = "home"
        st.rerun()

    st.subheader("Specifications")

    sku = st.text_input("SKU / Product Code *")
    product_name = st.text_input("Product Name *")
    supplier_code = st.text_input("Supplier Code *")
    supplier_name = st.text_input("Supplier Name *")
    uploaded_file = st.file_uploader("Upload PDF Specification *", type=["pdf"])

    required_complete = sku.strip() and product_name.strip() and supplier_code.strip() and supplier_name.strip() and uploaded_file

    if not required_complete:
        st.warning("Enter SKU, product name, supplier code, supplier name and upload a PDF before extraction/export/save.")
        return

    metadata = {
        "sku": sku.strip(),
        "name": product_name.strip(),
        "supplier_code": supplier_code.strip(),
        "supplier_name": supplier_name.strip(),
        "upload_date": str(date.today())
    }

    pdf_bytes = uploaded_file.read()
    pages = extract_pdf_text(pdf_bytes)
    rows = mock_extract(pages)

    if "pdf_viewer_open" not in st.session_state:
        st.session_state["pdf_viewer_open"] = False
    if "selected_row" not in st.session_state:
        st.session_state["selected_row"] = None

    if st.session_state["pdf_viewer_open"] and st.session_state["selected_row"]:
        left, right = st.columns([1, 1])
    else:
        left = st.container()
        right = None

    edited_values = {}

    with left:
        st.subheader("Extracted Results")
        st.write(f"**SKU:** {metadata['sku']}")
        st.write(f"**Product Name:** {metadata['name']}")
        st.write(f"**Supplier Code:** {metadata['supplier_code']}")
        st.write(f"**Supplier Name:** {metadata['supplier_name']}")

        h1, h2, h3 = st.columns([0.30, 0.52, 0.18])
        h1.markdown('<div class="table-header">Field</div>', unsafe_allow_html=True)
        h2.markdown('<div class="table-header">Value</div>', unsafe_allow_html=True)
        h3.markdown('<div class="table-header">Confidence</div>', unsafe_allow_html=True)

        for i, r in enumerate(rows):
            st.markdown('<div class="field-card">', unsafe_allow_html=True)
            c1, c2, c3 = st.columns([0.30, 0.52, 0.18])
            c1.markdown(f"**{r['Field']}**")

            if c2.button(str(r["Value"]), key=f"value_click_{i}", use_container_width=True):
                st.session_state["selected_row"] = r
                st.session_state["pdf_viewer_open"] = True
                st.rerun()

            c2.markdown(f'<div class="source-text">Source text: {", ".join(r["Sources"])}</div>', unsafe_allow_html=True)
            c3.markdown(f'<div class="{confidence_class(r["Confidence"])}">{r["Confidence"]}</div>', unsafe_allow_html=True)

            edited_value = st.text_input(f"Edit {r['Field']}", value=r["Value"], key=f"edit_{i}", label_visibility="collapsed")
            edited_values[r["Field"]] = edited_value
            st.markdown('</div>', unsafe_allow_html=True)

        export_df = make_export_row(metadata, edited_values)
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            export_df.to_excel(writer, index=False, sheet_name="Export")

        st.download_button(
            "Download Excel in Required Format",
            output.getvalue(),
            file_name=f"{metadata['sku']}_spec_export.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

        st.markdown("---")
        st.subheader("Save Specification")

        if st.button("Save record to SpecStream"):
            try:
                save_summary = save_to_google_sheets(metadata, edited_values, rows, uploaded_file.name)
                st.session_state["saved_summary"] = save_summary
                st.success("Specification saved successfully to Google Sheets.")
            except Exception as e:
                st.error("Save failed.")
                st.exception(e)

        if "saved_summary" in st.session_state:
            saved = st.session_state["saved_summary"]
            st.markdown(
                f"""
                <div class="save-card">
                    <h3>Saved Successfully</h3>
                    <b>Spec ID:</b> {saved["spec_id"]}<br>
                    <b>SKU:</b> {saved["sku"]}<br>
                    <b>Product:</b> {saved["product_name"]}<br>
                    <b>Supplier:</b> {saved["supplier_code"]} - {saved["supplier_name"]}<br>
                    <b>Spec Status:</b> {saved["spec_status"]}<br>
                    <b>Version:</b> {saved["version"]}<br>
                    <b>Upload Date:</b> {saved["upload_date"]}<br>
                    <b>Extraction Status:</b> {saved["extraction_status"]}<br>
                    <b>Fields Extracted:</b> {saved["fields_extracted"]}<br>
                    <b>Fields Requiring Review:</b> {saved["fields_requiring_review"]}<br>
                </div>
                """,
                unsafe_allow_html=True
            )

    if right is not None:
        with right:
            selected = st.session_state["selected_row"]
            top1, top2 = st.columns([0.7, 0.3])
            top1.subheader("PDF Source Viewer")

            if top2.button("Close"):
                st.session_state["pdf_viewer_open"] = False
                st.session_state["selected_row"] = None
                st.rerun()

            st.info(f"Selected field: {selected['Field']} | Page: {selected['Page']} | Sources: {', '.join(selected['Sources'])}")

            image_bytes, hit_count = render_highlighted_page(pdf_bytes, int(selected["Page"]), selected["Sources"])
            if hit_count == 0:
                st.warning("No exact highlight found. Showing source page only.")
            st.image(image_bytes, use_container_width=True)

# ============================================================
# 8. APP ROUTER
# ============================================================

if "mode" not in st.session_state:
    st.session_state["mode"] = "home"

if st.session_state["mode"] == "home":
    dashboard_page()

elif st.session_state["mode"] == "specifications":
    specifications_module()

elif st.session_state["mode"] == "kpis":
    kpi_page()

elif st.session_state["mode"] == "email_actions":
    email_actions_page()

elif st.session_state["mode"] == "complaints":
    module_placeholder(
        "Complaints",
        "Customer complaint management module.",
        ["Complaint ID", "Complaint Category", "Date Notification Received", "Customer Code", "Product Code(s)", "Supplier per SKU", "Status", "Evidence / Email Folder"],
        ["Log customer complaints and link them to products, suppliers and evidence.", "Track open/closed status and complaint category.", "Store emails, photos, videos and investigation documents.", "Create complaint timelines and recurring issue trends."],
        ["Future Outlook email detection for complaint notifications.", "Automatic attachment filing.", "AI-assisted complaint categorisation.", "Trend analysis by product, supplier and customer."]
    )

elif st.session_state["mode"] == "capa":
    module_placeholder(
        "CAPA / Quality Events",
        "Internal incidents, recalls, date extensions, concessions, holds and other quality events.",
        ["CAPA / Event ID", "Event Type", "Date Notification Received", "Customer Code if Applicable", "Product Code(s)", "Supplier per SKU", "Status", "Evidence / Communication Folder"],
        ["Manage internal quality events separately from customer complaints.", "Record recalls, date extensions, stock holds, concessions and internal incidents.", "Link events to affected SKUs, suppliers and supporting evidence.", "Track closure and current workload."],
        ["AI-assisted event classification.", "Automatic reminder for open actions.", "Link related specifications and supplier documents.", "Management KPI reporting."]
    )

elif st.session_state["mode"] == "supplier_comms":
    module_placeholder(
        "Supplier Communications",
        "Supplier communication history, requests, certificates, specifications and contacts.",
        ["Supplier Code", "Supplier Name", "Contact Person", "Communication Type", "Linked Product/SKU", "Status", "Email / Attachment Records"],
        ["Store supplier communication by supplier and product.", "Track requests for specifications, certificates, questionnaires and technical clarifications.", "Keep key supplier contacts and recurring documents visible.", "Reuse previous communication history."],
        ["Future Outlook capture from supplier emails.", "Automatic detection of certificates and specifications.", "Supplier response tracking.", "Document expiry reminders."]
    )

elif st.session_state["mode"] == "customer_comms":
    module_placeholder(
        "Customer Communications",
        "Customer requests, certificates, forms, questionnaires and recurring technical responses.",
        ["Customer Code", "Customer Name", "Request Type", "Linked Product/SKU", "Form / Certificate Requested", "Status", "Previous Similar Response"],
        ["Manage customer requests for certificates, specs, technical forms and questionnaires.", "Keep previous responses searchable for recurring customer forms.", "Link customer requests to products and suppliers.", "Track open requests and closure status."],
        ["Future Outlook capture from customer emails.", "AI-assisted form completion suggestions.", "Reusable answer library.", "Customer workload reporting."]
    )

elif st.session_state["mode"] == "environment":
    module_placeholder(
        "Environmental Monitoring",
        "Environmental monitoring schedule, results, retests, failures and trending.",
        ["Sample ID", "Site / Area", "Sample Type", "Date Taken", "Result", "Limit", "Status", "Corrective Action"],
        ["Schedule and record environmental swabs and test results.", "Track failures, retests and corrective actions.", "Trend results by site area and organism.", "Link failures to quality events where required."],
        ["Automatic trend alerts.", "Retest reminders.", "AI-assisted failure summaries.", "Dashboard reporting."]
    )

elif st.session_state["mode"] == "audits":
    module_placeholder(
        "Internal Audits",
        "Internal audits, checklists, findings, non-conformances and closure evidence.",
        ["Audit ID", "Audit Area", "Audit Date", "Auditor", "Finding", "Severity", "Owner", "Due Date", "Status"],
        ["Plan internal audits and manage checklists.", "Record findings, non-conformances and closure evidence.", "Track owners and due dates.", "Link audit findings to quality events."],
        ["Audit schedule reminders.", "Finding trend analysis.", "AI-assisted audit summaries.", "Automatic overdue action reporting."]
    )

elif st.session_state["mode"] == "npd":
    module_placeholder(
        "NPD",
        "New product development workflow from trial to launch approval.",
        ["Project ID", "Product Name", "Customer", "Stage", "Trial Date", "Specification Status", "Artwork Status", "Launch Status"],
        ["Track new product development from concept to launch.", "Manage trial information, specifications, artwork, allergens and nutrition.", "Track approval status and launch readiness.", "Link NPD products into the live specification system."],
        ["Launch checklist automation.", "AI-assisted allergen/nutrition checks.", "Artwork/specification comparison.", "Stage-gate workflow."]
    )
