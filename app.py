import streamlit as st
import pandas as pd
import fitz
import io

st.set_page_config(page_title="QA Spec Prototype", layout="wide")

st.markdown("""
<style>
div[data-testid="column"]:nth-of-type(2) {
    position: sticky;
    top: 1rem;
    align-self: flex-start;
    max-height: 92vh;
    overflow-y: auto;
    border-left: 1px solid #ddd;
    padding-left: 1rem;
}

.field-card {
    border: 1px solid #e1e4e8;
    border-radius: 10px;
    padding: 12px;
    margin-bottom: 12px;
    background-color: #fafafa;
}

.source-text {
    font-size: 12px;
    color: #666;
    margin-top: 4px;
}

.table-header {
    font-weight: 700;
    background-color: #f0f2f6;
    padding: 8px;
    border-radius: 6px;
    margin-bottom: 8px;
}

.conf-high {
    background-color: transparent;
    color: black;
    border: 1px solid #ddd;
    padding: 6px;
    border-radius: 6px;
    text-align: center;
    font-weight: bold;
}

.conf-medium {
    background-color: #fff3cd;
    color: #856404;
    border: 1px solid #ffeeba;
    padding: 6px;
    border-radius: 6px;
    text-align: center;
    font-weight: bold;
}

.conf-low {
    background-color: #f8d7da;
    color: #721c24;
    border: 1px solid #f5c6cb;
    padding: 6px;
    border-radius: 6px;
    text-align: center;
    font-weight: bold;
}
</style>
""", unsafe_allow_html=True)

st.title("QA Specification Extraction Prototype")
st.caption("v0.4 — cleaner table, sticky PDF evidence viewer, clickable source highlighting")

uploaded_file = st.file_uploader("Upload a PDF specification", type=["pdf"])


def confidence_class(confidence):
    if confidence == "High":
        return "conf-high"
    if confidence == "Medium":
        return "conf-medium"
    if confidence == "Low":
        return "conf-low"
    return "conf-high"


def extract_pdf_text(pdf_bytes):
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    pages = []
    for i, page in enumerate(doc):
        pages.append({"page": i + 1, "text": page.get_text()})
    return pages


def mock_extract(pages):
    joined = "\n".join(p["text"] for p in pages).lower()

    if "ground cumin" in joined:
        return [
            {"Field": "Product_Name", "Value": "GROUND CUMIN", "Confidence": "High", "Page": 1, "Sources": ["Product Name GROUND CUMIN"]},
            {"Field": "Product_Description", "Value": "Ground to a medium fine powder", "Confidence": "High", "Page": 1, "Sources": ["Ground to a medium fine powder"]},
            {"Field": "Ingredients_Full_Text", "Value": "Cumin", "Confidence": "High", "Page": 1, "Sources": ["Ingredients declaration Cumin"]},
            {"Field": "Allergens_Present", "Value": "None", "Confidence": "High", "Page": 4, "Sources": ["Allergens in product None"]},
            {"Field": "Allergens_May_Contain", "Value": "Peanuts (supply chain possible airborne cross-contamination)", "Confidence": "Medium", "Page": 4, "Sources": ["Peanuts", "Possible airborne cross contamination", "Customer to risk assess"]},
            {"Field": "Energy_kcal_100g", "Value": "427", "Confidence": "High", "Page": 3, "Sources": ["kcal 427"]},
            {"Field": "Energy_kJ_100g", "Value": "1783", "Confidence": "High", "Page": 3, "Sources": ["kj 1783"]},
            {"Field": "Protein_g_100g", "Value": "17.8", "Confidence": "High", "Page": 3, "Sources": ["Protein (g) 17.8"]},
            {"Field": "Salt_g_100g", "Value": "0.42", "Confidence": "High", "Page": 3, "Sources": ["Salt (g) 0.42"]},
            {"Field": "Origin_Summary", "Value": "India – processed in UK", "Confidence": "High", "Page": 1, "Sources": ["Origin India", "Processed in UK"]},
            {"Field": "Halal", "Value": "Suitable (not certified)", "Confidence": "High", "Page": 3, "Sources": ["Halal", "YES", "Not Certified"]},
            {"Field": "Kosher", "Value": "Suitable (not certified)", "Confidence": "High", "Page": 3, "Sources": ["Kosher", "YES", "Not Certified"]},
            {"Field": "GMO_Free", "Value": "Yes", "Confidence": "High", "Page": 5, "Sources": ["genetically modified varieties are known", "No", "This product needs declaration as GMO"]},
        ]

    if "ananas" in joined or "pineapple" in joined:
        return [
            {"Field": "Product_Name", "Value": "Pineapple Paste", "Confidence": "High", "Page": 1, "Sources": ["ANANAS", "PINEAPPLE"]},
            {"Field": "Product_Description", "Value": "Semifinished product in paste for gelato production. Not intended for direct consumption. Made in Italy.", "Confidence": "High", "Page": 1, "Sources": ["Semifinished product in paste for Gelato production", "not allowed direct consumption", "Made in Italy"]},
            {"Field": "Ingredients_Full_Text", "Value": "Glucose syrup, Saccharose syrup, Citric acid, Vegetable fibre (Inulin), Flavours, Pectin, E100, E160b", "Confidence": "High", "Page": 1, "Sources": ["GLUCOSE SYRUP", "SACCHAROSE SYRUP", "CITRIC ACID", "VEGETABLE FIBER", "FLAVOURS", "PECTIN", "E100", "E160b"]},
            {"Field": "Allergens_Present", "Value": "None declared", "Confidence": "High", "Page": 1, "Sources": ["MAY CONTAIN TRACES"]},
            {"Field": "Allergens_May_Contain", "Value": "Tree Nuts, Soy, Milk", "Confidence": "High", "Page": 1, "Sources": ["SHELLED NUTS", "SOY", "MILK"]},
            {"Field": "Energy_kcal_100g", "Value": "277.36", "Confidence": "High", "Page": 1, "Sources": ["277,36 Kcal"]},
            {"Field": "Energy_kJ_100g", "Value": "1160.11", "Confidence": "High", "Page": 1, "Sources": ["1160,11 Kj"]},
            {"Field": "Protein_g_100g", "Value": "0.76", "Confidence": "High", "Page": 1, "Sources": ["PROTEINS 0,76"]},
            {"Field": "Carbohydrates_g_100g", "Value": "67.79", "Confidence": "High", "Page": 1, "Sources": ["CARBOHYDRATES 67,79"]},
            {"Field": "Sugars_g_100g", "Value": "67.51", "Confidence": "High", "Page": 1, "Sources": ["sugars 67,51"]},
            {"Field": "Fat_g_100g", "Value": "0.39", "Confidence": "High", "Page": 1, "Sources": ["FATS 0,39"]},
            {"Field": "Saturates_g_100g", "Value": "0.04", "Confidence": "High", "Page": 1, "Sources": ["saturated 0,04"]},
            {"Field": "Fibre_g_100g", "Value": "0.38", "Confidence": "High", "Page": 1, "Sources": ["FIBER 0,38"]},
            {"Field": "Salt_g_100g", "Value": "0", "Confidence": "High", "Page": 1, "Sources": ["SALT 0 g"]},
            {"Field": "Origin_Summary", "Value": "Italy", "Confidence": "High", "Page": 1, "Sources": ["Made in Italy", "Prodotto in Italia"]},
            {"Field": "Lactose_Free", "Value": "Review Required", "Confidence": "Medium", "Page": 1, "Sources": ["MILK", "MAY CONTAIN TRACES"]},
            {"Field": "Palm_Oil_Free", "Value": "Review Required", "Confidence": "Medium", "Page": 1, "Sources": ["FLAVOURS"]},
            {"Field": "GMO_Free", "Value": "Yes", "Confidence": "High", "Page": 1, "Sources": ["It doesn't contain OGM ingredients"]},
        ]

    return [
        {"Field": "Product_Name", "Value": "Not extracted", "Confidence": "Low", "Page": 1, "Sources": [""]}
    ]


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

    pix = page.get_pixmap(matrix=fitz.Matrix(1.6, 1.6), alpha=False)
    return pix.tobytes("png"), hit_count


if uploaded_file:
    pdf_bytes = uploaded_file.read()
    pages = extract_pdf_text(pdf_bytes)
    rows = mock_extract(pages)

    if "pdf_viewer_open" not in st.session_state:
        st.session_state["pdf_viewer_open"] = False

    if "selected_row" not in st.session_state:
        st.session_state["selected_row"] = None

    if st.session_state["pdf_viewer_open"]:
        left, right = st.columns([1, 1])
    else:
        left = st.container()
        right = None

    with left:
        st.subheader("Extracted Results")

        h1, h2, h3 = st.columns([0.30, 0.52, 0.18])
        h1.markdown('<div class="table-header">Field</div>', unsafe_allow_html=True)
        h2.markdown('<div class="table-header">Value</div>', unsafe_allow_html=True)
        h3.markdown('<div class="table-header">Confidence</div>', unsafe_allow_html=True)

        edited_rows = []

        for i, row in enumerate(rows):
            with st.container():
                st.markdown('<div class="field-card">', unsafe_allow_html=True)

                c1, c2, c3 = st.columns([0.30, 0.52, 0.18])

                c1.markdown(f"**{row['Field']}**")

                if c2.button(str(row["Value"]), key=f"value_click_{i}", use_container_width=True):
                    st.session_state["selected_row"] = row
                    st.session_state["pdf_viewer_open"] = True
                    st.rerun()

                c2.markdown(
                    f'<div class="source-text">Source: {", ".join(row["Sources"])}</div>',
                    unsafe_allow_html=True
                )

                conf_class = confidence_class(row["Confidence"])
                c3.markdown(
                    f'<div class="{conf_class}">{row["Confidence"]}</div>',
                    unsafe_allow_html=True
                )

                edited_value = st.text_input(
                    f"Edit {row['Field']}",
                    value=row["Value"],
                    key=f"edit_{i}",
                    label_visibility="collapsed"
                )

                st.markdown('</div>', unsafe_allow_html=True)

            edited_rows.append({
                "Field": row["Field"],
                "Value": edited_value,
                "Confidence": row["Confidence"],
                "Source_Page": row["Page"],
                "Source_Terms": ", ".join(row["Sources"])
            })

        export_df = pd.DataFrame(edited_rows)

        output = io.BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            export_df.to_excel(writer, index=False, sheet_name="Extracted Spec")

        st.download_button(
            "Download Excel",
            output.getvalue(),
            file_name="extracted_spec.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    if st.session_state["pdf_viewer_open"] and st.session_state["selected_row"]:
        with right:
            selected = st.session_state["selected_row"]

            top1, top2 = st.columns([0.72, 0.28])
            top1.subheader("PDF Source Viewer")

            if top2.button("Close viewer"):
                st.session_state["pdf_viewer_open"] = False
                st.session_state["selected_row"] = None
                st.rerun()

            st.write(f"**Selected field:** {selected['Field']}")
            st.write(f"**Source page:** {selected['Page']}")
            st.write("**Highlighted source text:**")
            st.info(", ".join(selected["Sources"]))

            image_bytes, hit_count = render_highlighted_page(
                pdf_bytes,
                int(selected["Page"]),
                selected["Sources"]
            )

            if hit_count == 0:
                st.warning("No exact highlight found. Showing source page only.")

            st.image(image_bytes, use_container_width=True)
