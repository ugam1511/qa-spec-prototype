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
body {
    background-color: #F4F7FA;
}
.main-title {
    font-size: 38px;
    font-weight: 800;
    color: #111827;
    margin-bottom: 0px;
}
.subtitle {
    font-size: 16px;
    color: #6B7280;
    margin-bottom: 20px;
}
.hero-card {
    background: linear-gradient(135deg, #1F2937 0%, #2563EB 100%);
    color: white;
    padding: 28px;
    border-radius: 18px;
    margin-bottom: 24px;
}
.hero-card h1 {
    color: white;
    margin-bottom: 4px;
}
.hero-card p {
    color: #E5E7EB;
    font-size: 16px;
}
.kpi-card {
    background: white;
    border: 1px solid #E5E7EB;
    border-radius: 16px;
    padding: 20px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.05);
}
.kpi-label {
    color: #6B7280;
    font-size: 13px;
    font-weight: 600;
}
.kpi-value {
    color: #111827;
    font-size: 30px;
    font-weight: 800;
}
.kpi-note {
    font-size: 12px;
    color: #6B7280;
}
.module-card {
    border:1px solid #E5E7EB;
    border-radius:16px;
    padding:18px;
    margin-bottom:14px;
    background:#fff;
    box-shadow:0 2px 8px rgba(0,0,0,0.05);
}
.module-card h3 {
    margin-bottom: 4px;
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
.source-text {
    font-size:12px;
    color:#666;
}
.conf-high {
    border:1px solid #ccc;
    padding:7px;
    border-radius:7px;
    text-align:center;
    font-weight:bold;
}
.conf-medium {
    background-color:#fff3cd;
    color:#856404;
    border:1px solid #ffeeba;
    padding:7px;
    border-radius:7px;
    text-align:center;
    font-weight:bold;
}
.conf-low {
    background-color:#f8d7da;
    color:#721c24;
    border:1px solid #f5c6cb;
    padding:7px;
    border-radius:7px;
    text-align:center;
    font-weight:bold;
}
.save-card {
    border:1px solid #badbcc;
    background-color:#d1e7dd;
    color:#0f5132;
    border-radius:12px;
    padding:18px;
    margin-top:18px;
}
.activity-card {
    background:white;
    border:1px solid #E5E7EB;
    border-radius:16px;
    padding:18px;
    box-shadow:0 2px 8px rgba(0,0,0,0.05);
    margin-bottom:14px;
}
.status-pill-green {
    background:#DCFCE7;
    color:#166534;
    padding:5px 10px;
    border-radius:999px;
    font-size:12px;
    font-weight:700;
}
.status-pill-yellow {
    background:#FEF3C7;
    color:#92400E;
    padding:5px 10px;
    border-radius:999px;
    font-size:12px;
    font-weight:700;
}
.status-pill-blue {
    background:#DBEAFE;
    color:#1E40AF;
    padding:5px 10px;
    border-radius:999px;
    font-size:12px;
    font-weight:700;
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
    st.markdown(
        f"""
        <div class="kpi-card">
            <div class="kpi-label">{label}</div>
            <div class="kpi-value">{value}</div>
            <div class="kpi-note">{note}</div>
        </div>
        """,
        unsafe_allow_html=True
    )


def activity_item(time, text, status=""):
    st.markdown(f"**{time}** — {text} {status}")


def module_placeholder(title, description, fields):
    if st.button("← Back to dashboard"):
        st.session_state["mode"] = "home"
        st.rerun()

    st.title(title)
    st.write(description)
    st.info("This module is included in the SpecStream roadmap. The full workflow will be built after the pilot is approved.")

    st.subheader("Planned record fields")
    for f in fields:
        st.text_input(f, disabled=True)

    st.subheader("Planned capabilities")
    st.markdown("""
- Search and filter records
- Attach emails, PDFs, photos, videos and evidence
- Link to products, suppliers and specifications
- Track open/closed status
- Maintain full communication history
- Export reports
- AI assistant support in future
""")

# ============================================================
# 7. PAGE FUNCTIONS
# ============================================================

def dashboard_page():
    st.markdown(
        """
        <div class="hero-card">
            <h1>SpecStream</h1>
            <p>Food Quality Management System — specifications, complaints, quality events, supplier communications, audits and NPD in one connected platform.</p>
        </div>
        """,
        unsafe_allow_html=True
    )

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        kpi_card("Total Specifications", "1,284", "Across all suppliers")
    with c2:
        kpi_card("Pending Reviews", "14", "Require technical approval")
    with c3:
        kpi_card("Open Quality Events", "18", "CAPA, holds, recalls")
    with c4:
        kpi_card("Approved Suppliers", "96", "Active supplier base")

    st.markdown("### Quick Actions")
    q1, q2, q3, q4 = st.columns(4)
    if q1.button("＋ Upload Specification", use_container_width=True):
        st.session_state["mode"] = "specifications"
        st.rerun()
    if q2.button("🔎 Search Records", use_container_width=True):
        st.info("Search will be activated in Stage 2.")
    if q3.button("📧 Mail Capture", use_container_width=True):
        st.info("Mail Capture prototype will be added after dashboard/search.")
    if q4.button("📊 Reports", use_container_width=True):
        st.info("Reports module planned for pilot phase.")

    left, right = st.columns([0.62, 0.38])

    with left:
        st.markdown("### QA Modules")

        modules = [
            ("Specifications", "AI-assisted specification extraction, review, evidence checking and export.", "specifications"),
            ("Complaints", "Customer complaint records, evidence, product links, supplier links and status tracking.", "complaints"),
            ("CAPA / Quality Events", "Internal incidents, recalls, date extensions, holds, concessions and quality events.", "capa"),
            ("Supplier Communications", "Supplier emails, certificates, specification requests, contacts and technical communication history.", "supplier_comms"),
            ("Customer Communications", "Customer requests, certificates, forms, questionnaires and recurring technical responses.", "customer_comms"),
            ("Environmental Monitoring", "Sampling schedules, results, failures, retests, trends and corrective actions.", "environment"),
            ("Internal Audits", "Audit schedules, checklists, findings, non-conformances and closures.", "audits"),
            ("NPD", "New product development workflow, trials, specs, artwork, allergen/nutrition checks and launch approvals.", "npd"),
        ]

        for name, desc, mode in modules:
            st.markdown('<div class="module-card">', unsafe_allow_html=True)
            c1, c2 = st.columns([0.75, 0.25])
            c1.markdown(f"### {name}")
            c1.write(desc)
            if c2.button(f"Open", key=f"open_{mode}", use_container_width=True):
                st.session_state["mode"] = mode
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

    with right:
        st.markdown("### Recent Activity")
        st.markdown('<div class="activity-card">', unsafe_allow_html=True)
        activity_item("09:15", "Ground Cumin specification reviewed", '<span class="status-pill-green">Approved</span>')
        activity_item("09:02", "Pineapple Paste saved to database", '<span class="status-pill-yellow">Review</span>')
        activity_item("Yesterday", "Bresaola specification extracted", '<span class="status-pill-green">Complete</span>')
        activity_item("Yesterday", "Complaint workflow added to roadmap", '<span class="status-pill-blue">Planned</span>')
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown("### Pending Reviews")
        st.markdown('<div class="activity-card">', unsafe_allow_html=True)
        st.write("• Pineapple Paste — Palm oil review")
        st.write("• Ground Cumin — Peanut cross-contamination")
        st.write("• Bresaola — Natural flavours review")
        st.write("• 11 other specification fields requiring QA check")
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown("### Specification Status")
        status_df = pd.DataFrame({
            "Status": ["Approved", "Pending Review", "Requires Update", "Expired"],
            "Count": [984, 214, 61, 25]
        })
        st.bar_chart(status_df.set_index("Status"))

        st.markdown("### System Status")
        st.success("Google Sheets database connected")
        st.info("SharePoint, Microsoft login and AI API planned for production pilot")


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

elif st.session_state["mode"] == "complaints":
    module_placeholder(
        "Complaints",
        "Customer complaint management module.",
        ["Complaint ID", "Complaint Category", "Date Notification Received", "Customer Code", "Product Code(s)", "Supplier per SKU", "Status", "Evidence / Email Folder"]
    )

elif st.session_state["mode"] == "capa":
    module_placeholder(
        "CAPA / Quality Events",
        "Internal incidents, recalls, date extensions, concessions, holds and other quality events.",
        ["CAPA / Event ID", "Event Type", "Date Notification Received", "Customer Code if Applicable", "Product Code(s)", "Supplier per SKU", "Status", "Evidence / Communication Folder"]
    )

elif st.session_state["mode"] == "supplier_comms":
    module_placeholder(
        "Supplier Communications",
        "Supplier communication history, requests, certificates, specifications and contacts.",
        ["Supplier Code", "Supplier Name", "Contact Person", "Communication Type", "Linked Product/SKU", "Status", "Email / Attachment Records"]
    )

elif st.session_state["mode"] == "customer_comms":
    module_placeholder(
        "Customer Communications",
        "Customer requests, certificates, forms, questionnaires and recurring technical responses.",
        ["Customer Code", "Customer Name", "Request Type", "Linked Product/SKU", "Form / Certificate Requested", "Status", "Previous Similar Response"]
    )

elif st.session_state["mode"] == "environment":
    module_placeholder(
        "Environmental Monitoring",
        "Environmental monitoring schedule, results, retests, failures and trending.",
        ["Sample ID", "Site / Area", "Sample Type", "Date Taken", "Result", "Limit", "Status", "Corrective Action"]
    )

elif st.session_state["mode"] == "audits":
    module_placeholder(
        "Internal Audits",
        "Internal audits, checklists, findings, non-conformances and closure evidence.",
        ["Audit ID", "Audit Area", "Audit Date", "Auditor", "Finding", "Severity", "Owner", "Due Date", "Status"]
    )

elif st.session_state["mode"] == "npd":
    module_placeholder(
        "NPD",
        "New product development workflow from trial to launch approval.",
        ["Project ID", "Product Name", "Customer", "Stage", "Trial Date", "Specification Status", "Artwork Status", "Launch Status"]
    )
