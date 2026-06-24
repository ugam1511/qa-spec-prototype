import streamlit as st
import pandas as pd
import fitz
import io
import base64

st.set_page_config(page_title="QA Spec Prototype", layout="wide")

st.title("QA Specification Extraction Prototype")
st.caption("v0.2 — clickable values with PDF source highlighting")

uploaded_file = st.file_uploader("Upload a PDF specification", type=["pdf"])


def confidence_colour(confidence):
    if confidence == "High":
        return "black"
    if confidence == "Medium":
        return "#b8860b"
    if confidence == "Low":
        return "red"
    return "black"


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
            {"Field": "Product_Name", "Value": "GROUND CUMIN", "Confidence": "High", "Page": 1, "Search": "Product Name GROUND CUMIN"},
            {"Field": "Product_Description", "Value": "Ground to a medium fine powder", "Confidence": "High", "Page": 1, "Search": "Ground to a medium fine powder"},
            {"Field": "Ingredients_Full_Text", "Value": "Cumin", "Confidence": "High", "Page": 1, "Search": "Ingredients declaration Cumin"},
            {"Field": "Allergens_Present", "Value": "None", "Confidence": "High", "Page": 4, "Search": "Allergens in product None"},
            {"Field": "Allergens_May_Contain", "Value": "Peanuts (supply chain possible airborne cross-contamination)", "Confidence": "Medium", "Page": 4, "Search": "Possible airborne cross contamination"},
            {"Field": "Energy_kcal_100g", "Value": "427", "Confidence": "High", "Page": 3, "Search": "kcal 427"},
            {"Field": "Energy_kJ_100g", "Value": "1783", "Confidence": "High", "Page": 3, "Search": "kj 1783"},
            {"Field": "Protein_g_100g", "Value": "17.8", "Confidence": "High", "Page": 3, "Search": "Protein (g) 17.8"},
            {"Field": "Carbohydrates_g_100g", "Value": "33.7", "Confidence": "High", "Page": 3, "Search": "Carbohydrate (g) 33.7"},
            {"Field": "Sugars_g_100g", "Value": "2.3", "Confidence": "High", "Page": 3, "Search": "Sugar (g) 2.3"},
            {"Field": "Fat_g_100g", "Value": "22.3", "Confidence": "High", "Page": 3, "Search": "Fat (g) 22.3"},
            {"Field": "Saturates_g_100g", "Value": "1.5", "Confidence": "High", "Page": 3, "Search": "Saturates (g) 1.5"},
            {"Field": "Salt_g_100g", "Value": "0.42", "Confidence": "High", "Page": 3, "Search": "Salt (g) 0.42"},
            {"Field": "Origin_Summary", "Value": "India – processed in UK", "Confidence": "High", "Page": 1, "Search": "Origin India"},
            {"Field": "Halal", "Value": "Suitable (not certified)", "Confidence": "High", "Page": 3, "Search": "Not Certified"},
            {"Field": "Kosher", "Value": "Suitable (not certified)", "Confidence": "High", "Page": 3, "Search": "Not Certified"},
            {"Field": "GMO_Free", "Value": "Yes", "Confidence": "High", "Page": 5, "Search": "genetically modified varieties are known"},
        ]

    if "ananas" in joined or "pineapple" in joined:
        return [
            {"Field": "Product_Name", "Value": "Pineapple Paste", "Confidence": "High", "Page": 1, "Search": "ANANAS PINEAPPLE"},
            {"Field": "Product_Description", "Value": "Semifinished product in paste for gelato production. Not intended for direct consumption. Made in Italy.", "Confidence": "High", "Page": 1, "Search": "Semifinished product in paste for Gelato production"},
            {"Field": "Ingredients_Full_Text", "Value": "Glucose syrup, Saccharose syrup, Citric acid, Vegetable fibre (Inulin), Flavours, Pectin, E100, E160b", "Confidence": "High", "Page": 1, "Search": "GLUCOSE SYRUP"},
            {"Field": "Allergens_Present", "Value": "None declared", "Confidence": "High", "Page": 1, "Search": "MAY CONTAIN TRACES"},
            {"Field": "Allergens_May_Contain", "Value": "Tree Nuts, Soy, Milk", "Confidence": "High", "Page": 1, "Search": "MAY CONTAIN TRACES OF SHELLED NUTS, SOY, MILK"},
            {"Field": "Energy_kcal_100g", "Value": "277.36", "Confidence": "High", "Page": 1, "Search": "277,36 Kcal"},
            {"Field": "Energy_kJ_100g", "Value": "1160.11", "Confidence": "High", "Page": 1, "Search": "1160,11 Kj"},
            {"Field": "Protein_g_100g", "Value": "0.76", "Confidence": "High", "Page": 1, "Search": "PROTEINS 0,76"},
            {"Field": "Carbohydrates_g_100g", "Value": "67.79", "Confidence": "High", "Page": 1, "Search": "CARBOHYDRATES 67,79"},
            {"Field": "Sugars_g_100g", "Value": "67.51", "Confidence": "High", "Page": 1, "Search": "sugars 67,51"},
            {"Field": "Fat_g_100g", "Value": "0.39", "Confidence": "High", "Page": 1, "Search": "FATS 0,39"},
            {"Field": "Saturates_g_100g", "Value": "0.04", "Confidence": "High", "Page": 1, "Search": "saturated 0,04"},
            {"Field": "Fibre_g_100g", "Value": "0.38", "Confidence": "High", "Page": 1, "Search": "FIBER 0,38"},
            {"Field": "Salt_g_100g", "Value": "0", "Confidence": "High", "Page": 1, "Search": "SALT 0 g"},
            {"Field": "Origin_Summary", "Value": "Italy", "Confidence": "High", "Page": 1, "Search": "Made in Italy"},
            {"Field": "Lactose_Free", "Value": "Review Required", "Confidence": "Medium", "Page": 1, "Search": "MILK"},
            {"Field": "Palm_Oil_Free", "Value": "Review Required", "Confidence": "Medium", "Page": 1, "Search": "FLAVOURS"},
            {"Field": "GMO_Free", "Value": "Yes", "Confidence": "High", "Page": 1, "Search": "It doesn't contain OGM ingredients"},
        ]

    return [
        {"Field": "Product_Name", "Value": "Not extracted", "Confidence": "Low", "Page": 1, "Search": ""}
    ]


def render_highlighted_page(pdf_bytes, page_number, search_text):
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    page = doc[page_number - 1]

    rects = []
    if search_text:
        rects = page.search_for(search_text)

    if not rects and search_text:
        words = search_text.split()
        for word in words[:5]:
            found = page.search_for(word)
            if found:
                rects.extend(found[:2])

    for rect in rects:
        highlight = page.add_highlight_annot(rect)
        highlight.update()

    pix = page.get_pixmap(matrix=fitz.Matrix(1.6, 1.6), alpha=False)
    return pix.tobytes("png"), len(rects)


if uploaded_file:
    pdf_bytes = uploaded_file.read()
    pages = extract_pdf_text(pdf_bytes)
    rows = mock_extract(pages)

    if "selected_row" not in st.session_state:
        st.session_state["selected_row"] = rows[0]

    left, right = st.columns([1.25, 1])

    with left:
        st.subheader("Extracted Results")

        header = st.columns([0.32, 0.38, 0.15, 0.15])
        header[0].markdown("**Field**")
        header[1].markdown("**Value**")
        header[2].markdown("**Confidence**")
        header[3].markdown("**Page**")

        edited_rows = []

        for i, row in enumerate(rows):
            cols = st.columns([0.32, 0.38, 0.15, 0.15])

            cols[0].write(row["Field"])

            colour = confidence_colour(row["Confidence"])

            if cols[1].button(str(row["Value"]), key=f"click_{i}", use_container_width=True):
                st.session_state["selected_row"] = row

            cols[1].markdown(
                f"<div style='color:{colour}; font-size:12px;'>Click value to view source</div>",
                unsafe_allow_html=True
            )

            cols[2].markdown(
                f"<span style='color:{colour}; font-weight:bold;'>{row['Confidence']}</span>",
                unsafe_allow_html=True
            )

            cols[3].write(row["Page"])

            edited_value = st.text_input(
                f"Edit {row['Field']}",
                value=row["Value"],
                key=f"edit_{i}"
            )

            edited_rows.append({
                "Field": row["Field"],
                "Edited_Value": edited_value,
                "Confidence": row["Confidence"],
                "Source_Page": row["Page"],
                "Source_Search": row["Search"]
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

    with right:
        st.subheader("PDF Source Viewer")

        selected = st.session_state["selected_row"]

        st.write(f"**Selected field:** {selected['Field']}")
        st.write(f"**Source page:** {selected['Page']}")
        st.write(f"**Search/highlight text:** {selected['Search']}")

        image_bytes, hit_count = render_highlighted_page(
            pdf_bytes,
            int(selected["Page"]),
            selected["Search"]
        )

        if hit_count == 0:
            st.warning("Exact highlight not found. Showing source page only.")

        st.image(image_bytes, use_container_width=True)
