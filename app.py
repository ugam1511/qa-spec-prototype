import streamlit as st
import pandas as pd
import fitz
import io
from datetime import date, datetime
import uuid
import gspread
from google.oauth2.service_account import Credentials

st.set_page_config(page_title="SpecStream", layout="wide")

st.markdown("""
<style>
.field-card {
    border: 1px solid #d9dee5;
    border-radius: 12px;
    padding: 14px;
    margin-bottom: 12px;
    background: #ffffff;
    box-shadow: 0 1px 4px rgba(0,0,0,0.05);
}
.table-header {
    font-weight: 700;
    background-color: #eef1f5;
    padding: 10px;
    border-radius: 8px;
    margin-bottom: 10px;
}
.source-text {
    font-size: 12px;
    color: #666;
}
.conf-high {
    border: 1px solid #ccc;
    padding: 7px;
    border-radius: 7px;
    text-align: center;
    font-weight: bold;
}
.conf-medium {
    background-color: #fff3cd;
    color: #856404;
    border: 1px solid #ffeeba;
    padding: 7px;
    border-radius: 7px;
    text-align: center;
    font-weight: bold;
}
.conf-low {
    background-color: #f8d7da;
    color: #721c24;
    border: 1px solid #f5c6cb;
    padding: 7px;
    border-radius: 7px;
    text-align: center;
    font-weight: bold;
}
.save-card {
    border: 1px solid #badbcc;
    background-color: #d1e7dd;
    color: #0f5132;
    border-radius: 12px;
    padding: 18px;
    margin-top: 18px;
}
</style>
""", unsafe_allow_html=True)

EXPORT_COLUMNS = [
    "SKU", "Name", "Supplier code",
    "Celery", "Cereals", "Crustaceans", "Eggs", "Fish", "Lupin", "Milk",
    "Molluscs", "Mustard", "Nuts", "Peanuts", "Sesame Seeds", "Soya",
    "Sulphur dioxide", "Vegetarian", "Vegan", "Contains GM Protein/DNA",
    "Palm oil", "Coeliacs", "Halal", "Kosher", "Organic",
    "KJ", "Kcal", "Fat", "Saturates", "Carbs", "Sugars", "Fibre",
    "Protein", "Salt", "Ingredients table"
]


def get_google_sheet():
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]

    creds = Credentials.from_service_account_info(
        dict(st.secrets["gcp_service_account"]),
        scopes=scopes
    )

    client = gspread.authorize(creds)
    return client.open(st.secrets["google"]["sheet_name"])


def append_to_sheet(tab_name, row_dict):
    sheet = get_google_sheet()
    worksheet = sheet.worksheet(tab_name)
    headers = worksheet.row_values(1)
    row = [row_dict.get(header, "") for header in headers]
    worksheet.append_row(row, value_input_option="USER_ENTERED")


def confidence_class(confidence):
    return {
        "High": "conf-high",
        "Medium": "conf-medium",
        "Low": "conf-low"
    }.get(confidence, "conf-high")


def extract_pdf_text(pdf_bytes):
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    return [{"page": i + 1, "text": page.get_text()} for i, page in enumerate(doc)]


def mock_extract(pages):
    joined = "\n".join(p["text"] for p in pages).lower()

    if "ground cumin" in joined:
        return [
            {"Field": "Name", "Value": "GROUND CUMIN", "Confidence": "High", "Page": 1, "Sources": ["Product Name GROUND CUMIN"]},
            {"Field": "Ingredients table", "Value": "Cumin", "Confidence": "High", "Page": 1, "Sources": ["Ingredients declaration Cumin"]},
            {"Field": "Peanuts", "Value": "May Contain", "Confidence": "Medium", "Page": 4, "Sources": ["Peanuts", "Possible airborne cross contamination"]},
            {"Field": "Vegetarian", "Value": "Suitable", "Confidence": "High", "Page": 3, "Sources": ["Vegetarians YES"]},
            {"Field": "Vegan", "Value": "Suitable", "Confidence": "High", "Page": 3, "Sources": ["Vegans YES"]},
            {"Field": "Contains GM Protein/DNA", "Value": "No", "Confidence": "High", "Page": 5, "Sources": ["This product needs declaration as GMO No"]},
            {"Field": "Palm oil", "Value": "No", "Confidence": "High", "Page": 1, "Sources": ["Ingredients declaration Cumin"]},
            {"Field": "Coeliacs", "Value": "Suitable (claimed)", "Confidence": "High", "Page": 3, "Sources": ["Coeliacs YES"]},
            {"Field": "Halal", "Value": "Suitable (not certified)", "Confidence": "High", "Page": 3, "Sources": ["Halal YES", "Not Certified"]},
            {"Field": "Kosher", "Value": "Suitable (not certified)", "Confidence": "High", "Page": 3, "Sources": ["Kosher YES", "Not Certified"]},
            {"Field": "Organic", "Value": "No", "Confidence": "High", "Page": 5, "Sources": ["No organic claim found"]},
            {"Field": "KJ", "Value": "1783", "Confidence": "High", "Page": 3, "Sources": ["kj 1783"]},
            {"Field": "Kcal", "Value": "427", "Confidence": "High", "Page": 3, "Sources": ["kcal 427"]},
            {"Field": "Fat", "Value": "22.3", "Confidence": "High", "Page": 3, "Sources": ["Fat (g) 22.3"]},
            {"Field": "Saturates", "Value": "1.5", "Confidence": "High", "Page": 3, "Sources": ["Saturates (g) 1.5"]},
            {"Field": "Carbs", "Value": "33.7", "Confidence": "High", "Page": 3, "Sources": ["Carbohydrate (g) 33.7"]},
            {"Field": "Sugars", "Value": "2.3", "Confidence": "High", "Page": 3, "Sources": ["Sugar (g) 2.3"]},
            {"Field": "Fibre", "Value": "Not stated", "Confidence": "Medium", "Page": 3, "Sources": ["Nutrition information per 100g"]},
            {"Field": "Protein", "Value": "17.8", "Confidence": "High", "Page": 3, "Sources": ["Protein (g) 17.8"]},
            {"Field": "Salt", "Value": "0.42", "Confidence": "High", "Page": 3, "Sources": ["Salt (g) 0.42"]},
        ]

    if "ananas" in joined or "pineapple" in joined:
        return [
            {"Field": "Name", "Value": "Pineapple Paste", "Confidence": "High", "Page": 1, "Sources": ["ANANAS", "PINEAPPLE"]},
            {"Field": "Ingredients table", "Value": "Glucose syrup, Saccharose syrup, Citric acid, Vegetable fibre (Inulin), Flavours, Pectin, E100, E160b", "Confidence": "High", "Page": 1, "Sources": ["GLUCOSE SYRUP", "SACCHAROSE SYRUP", "CITRIC ACID", "VEGETABLE FIBER", "FLAVOURS", "PECTIN", "E100", "E160b"]},
            {"Field": "Milk", "Value": "May Contain", "Confidence": "High", "Page": 1, "Sources": ["MILK", "MAY CONTAIN TRACES"]},
            {"Field": "Nuts", "Value": "May Contain", "Confidence": "High", "Page": 1, "Sources": ["SHELLED NUTS"]},
            {"Field": "Soya", "Value": "May Contain", "Confidence": "High", "Page": 1, "Sources": ["SOY"]},
            {"Field": "Vegetarian", "Value": "Suitable", "Confidence": "High", "Page": 1, "Sources": ["Composition"]},
            {"Field": "Vegan", "Value": "Suitable", "Confidence": "Medium", "Page": 1, "Sources": ["FLAVOURS"]},
            {"Field": "Contains GM Protein/DNA", "Value": "No", "Confidence": "High", "Page": 1, "Sources": ["It doesn't contain OGM ingredients"]},
            {"Field": "Palm oil", "Value": "Review Required", "Confidence": "Medium", "Page": 1, "Sources": ["FLAVOURS"]},
            {"Field": "Coeliacs", "Value": "Suitable", "Confidence": "High", "Page": 1, "Sources": ["No gluten-containing ingredients identified"]},
            {"Field": "Halal", "Value": "No", "Confidence": "High", "Page": 1, "Sources": ["No halal statement found"]},
            {"Field": "Kosher", "Value": "No", "Confidence": "High", "Page": 1, "Sources": ["No kosher statement found"]},
            {"Field": "Organic", "Value": "No", "Confidence": "High", "Page": 1, "Sources": ["No organic claim found"]},
            {"Field": "KJ", "Value": "1160.11", "Confidence": "High", "Page": 1, "Sources": ["1160,11 Kj"]},
            {"Field": "Kcal", "Value": "277.36", "Confidence": "High", "Page": 1, "Sources": ["277,36 Kcal"]},
            {"Field": "Fat", "Value": "0.39", "Confidence": "High", "Page": 1, "Sources": ["FATS 0,39"]},
            {"Field": "Saturates", "Value": "0.04", "Confidence": "High", "Page": 1, "Sources": ["saturated 0,04"]},
            {"Field": "Carbs", "Value": "67.79", "Confidence": "High", "Page": 1, "Sources": ["CARBOHYDRATES 67,79"]},
            {"Field": "Sugars", "Value": "67.51", "Confidence": "High", "Page": 1, "Sources": ["sugars 67,51"]},
            {"Field": "Fibre", "Value": "0.38", "Confidence": "High", "Page": 1, "Sources": ["FIBER 0,38"]},
            {"Field": "Protein", "Value": "0.76", "Confidence": "High", "Page": 1, "Sources": ["PROTEINS 0,76"]},
            {"Field": "Salt", "Value": "0", "Confidence": "High", "Page": 1, "Sources": ["SALT 0 g"]},
        ]

    if "bresaola" in joined or "punta d'anca" in joined or "punta d’anca" in joined:
        return [
            {"Field": "Name", "Value": "BRESAOLA INTERA – PUNTA D'ANCA – VACUUM PACKED", "Confidence": "High", "Page": 1, "Sources": ["BRESAOLA INTERA", "PUNTA D’ANCA", "VACUUM PACKED"]},
            {"Field": "Ingredients table", "Value": "Beef, Salt, Dextrose, Natural flavours, Sodium nitrite (E250), Potassium nitrate (E252)", "Confidence": "High", "Page": 1, "Sources": ["Carne bovina", "Beef", "Sale", "Salt", "Destrosio", "Dextrose", "Aromi naturali", "Natural flavours", "E250", "E252"]},
            {"Field": "Vegetarian", "Value": "No", "Confidence": "High", "Page": 1, "Sources": ["Carne bovina", "Beef"]},
            {"Field": "Vegan", "Value": "No", "Confidence": "High", "Page": 1, "Sources": ["Carne bovina", "Beef"]},
            {"Field": "Contains GM Protein/DNA", "Value": "No", "Confidence": "High", "Page": 3, "Sources": ["OGM", "GMO", "NO"]},
            {"Field": "Palm oil", "Value": "Review Required", "Confidence": "Medium", "Page": 1, "Sources": ["Aromi naturali", "Natural flavours"]},
            {"Field": "Coeliacs", "Value": "Suitable (claimed)", "Confidence": "High", "Page": 4, "Sources": ["SENZA GLUTINE", "GLUTENFREI"]},
            {"Field": "Halal", "Value": "No", "Confidence": "High", "Page": 4, "Sources": ["if raw material has been butchered with Halal rite", "Lot code encoding"]},
            {"Field": "Kosher", "Value": "No", "Confidence": "High", "Page": 1, "Sources": ["No kosher statement found"]},
            {"Field": "Organic", "Value": "No", "Confidence": "High", "Page": 1, "Sources": ["No organic claim found"]},
            {"Field": "KJ", "Value": "665", "Confidence": "High", "Page": 2, "Sources": ["Energy value", "KJ", "665"]},
            {"Field": "Kcal", "Value": "159", "Confidence": "High", "Page": 2, "Sources": ["Energy value", "Kcal", "159"]},
            {"Field": "Fat", "Value": "4", "Confidence": "High", "Page": 2, "Sources": ["Grassi", "Fat", "4"]},
            {"Field": "Saturates", "Value": "1", "Confidence": "High", "Page": 2, "Sources": ["saturated fatty acids", "1"]},
            {"Field": "Carbs", "Value": "<1", "Confidence": "High", "Page": 2, "Sources": ["Carbohydrates", "< 1"]},
            {"Field": "Sugars", "Value": "<1", "Confidence": "High", "Page": 2, "Sources": ["of which sugars", "< 1"]},
            {"Field": "Fibre", "Value": "0", "Confidence": "High", "Page": 2, "Sources": ["Fibre", "Fibers", "0"]},
            {"Field": "Protein", "Value": "30", "Confidence": "High", "Page": 2, "Sources": ["Proteins", "30"]},
            {"Field": "Salt", "Value": "3.7", "Confidence": "High", "Page": 2, "Sources": ["Sale", "Salt", "3,7"]},
        ]

    return [{"Field": "Name", "Value": "Not extracted", "Confidence": "Low", "Page": 1, "Sources": ["Unknown document format in mock mode"]}]


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


def make_export_row(metadata, edited_values):
    row = {col: "" for col in EXPORT_COLUMNS}
    row["SKU"] = metadata["sku"]
    row["Name"] = metadata["name"]
    row["Supplier code"] = metadata["supplier_code"]

    for field, value in edited_values.items():
        if field in row:
            row[field] = value

    return pd.DataFrame([row], columns=EXPORT_COLUMNS)


def save_to_google_sheets(metadata, edited_values, rows, uploaded_filename):
    spec_id = "SPEC-" + datetime.now().strftime("%Y%m%d-%H%M%S") + "-" + str(uuid.uuid4())[:8].upper()
    medium_low_count = sum(1 for row in rows if row["Confidence"] in ["Medium", "Low"])
    extraction_status = "Pending Review" if medium_low_count > 0 else "Reviewed"

    product_record = {
        "SKU": metadata["sku"],
        "Product_Name": metadata["name"],
        "Product_Status": "Active",
        "Notes": ""
    }

    supplier_record = {
        "Supplier_Code": metadata["supplier_code"],
        "Supplier_Name": metadata["supplier_name"],
        "Supplier_Status": "Active",
        "Notes": ""
    }

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

    append_to_sheet("Products", product_record)
    append_to_sheet("Suppliers", supplier_record)
    append_to_sheet("Specifications", specification_record)

    for row in rows:
        field = row["Field"]
        extracted_record = {
            "Spec_ID": spec_id,
            "Field": field,
            "Value": row["Value"],
            "Confidence": row["Confidence"],
            "Source_Page": row["Page"],
            "Source_Text": ", ".join(row["Sources"]),
            "Edited_Value": edited_values.get(field, row["Value"]),
            "Review_Required": "Yes" if row["Confidence"] in ["Medium", "Low"] else "No"
        }
        append_to_sheet("Extracted_Data", extracted_record)

    return {
        "spec_id": spec_id,
        "sku": metadata["sku"],
        "product_name": metadata["name"],
        "supplier_code": metadata["supplier_code"],
        "supplier_name": metadata["supplier_name"],
        "spec_status": "Current",
        "product_status": "Active",
        "version": "1",
        "file_name": uploaded_filename,
        "drive_path": specification_record["Drive_Path"],
        "upload_date": metadata["upload_date"],
        "extraction_status": extraction_status,
        "fields_extracted": len(rows),
        "fields_requiring_review": medium_low_count
    }


st.title("SpecStream")
st.caption("Google Sheets-connected version")

if "mode" not in st.session_state:
    st.session_state["mode"] = "home"

if st.session_state["mode"] == "home":
    st.subheader("Home")
    search = st.text_input("Search by SKU, product name, supplier code or supplier name")
    st.info("Search will be connected after save-to-database is verified.")

    if st.button("Add new product / specification"):
        st.session_state["mode"] = "add"
        st.rerun()

elif st.session_state["mode"] == "add":
    if st.button("← Back to home"):
        st.session_state["mode"] = "home"
        st.rerun()

    st.subheader("Add Product / Specification")

    sku = st.text_input("SKU / Product Code *")
    product_name = st.text_input("Product Name *")
    supplier_code = st.text_input("Supplier Code *")
    supplier_name = st.text_input("Supplier Name *")
    uploaded_file = st.file_uploader("Upload PDF Specification *", type=["pdf"])

    required_complete = sku.strip() and product_name.strip() and supplier_code.strip() and supplier_name.strip() and uploaded_file

    if not required_complete:
        st.warning("Enter SKU, product name, supplier code, supplier name and upload a PDF before extraction/export/save.")

    if required_complete:
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

            for i, row in enumerate(rows):
                st.markdown('<div class="field-card">', unsafe_allow_html=True)

                c1, c2, c3 = st.columns([0.30, 0.52, 0.18])
                c1.markdown(f"**{row['Field']}**")

                if c2.button(str(row["Value"]), key=f"value_click_{i}", use_container_width=True):
                    st.session_state["selected_row"] = row
                    st.session_state["pdf_viewer_open"] = True
                    st.rerun()

                c2.markdown(
                    f'<div class="source-text">Source text: {", ".join(row["Sources"])}</div>',
                    unsafe_allow_html=True
                )

                c3.markdown(
                    f'<div class="{confidence_class(row["Confidence"])}">{row["Confidence"]}</div>',
                    unsafe_allow_html=True
                )

                edited_value = st.text_input(
                    f"Edit {row['Field']}",
                    value=row["Value"],
                    key=f"edit_{i}",
                    label_visibility="collapsed"
                )

                edited_values[row["Field"]] = edited_value
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

                st.info(
                    f"Selected field: {selected['Field']} | "
                    f"Page: {selected['Page']} | "
                    f"Sources: {', '.join(selected['Sources'])}"
                )

                image_bytes, hit_count = render_highlighted_page(
                    pdf_bytes,
                    int(selected["Page"]),
                    selected["Sources"]
                )

                if hit_count == 0:
                    st.warning("No exact highlight found. Showing source page only.")

                st.image(image_bytes, use_container_width=True)
