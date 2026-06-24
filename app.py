import streamlit as st
import pandas as pd
import fitz  # PyMuPDF
import io

st.set_page_config(page_title="QA Spec Prototype", layout="wide")

st.title("QA Specification Extraction Prototype")
st.caption("Mock AI version: upload PDF, review extracted fields, export Excel.")

uploaded_file = st.file_uploader("Upload a PDF specification", type=["pdf"])

def confidence_style(confidence):
    if confidence == "High":
        return "color: black;"
    if confidence == "Medium":
        return "color: #b8860b; font-weight: bold;"
    if confidence == "Low":
        return "color: red; font-weight: bold;"
    return "color: black;"

def extract_pdf_text(pdf_bytes):
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    pages = []
    for i, page in enumerate(doc):
        pages.append({
            "page": i + 1,
            "text": page.get_text()
        })
    return pages

def mock_extract(filename, pages):
    joined_text = "\n".join(p["text"] for p in pages)

    if "pineapple" in joined_text.lower() or "ananas" in joined_text.lower():
        return [
            ["Product_Name", "Pineapple Paste", "High", 1, "Name: ANANAS PINEAPPLE"],
            ["Product_Description", "Semifinished product in paste for gelato production. Not intended for direct consumption. Made in Italy.", "High", 1, "Semifinished product in paste for Gelato production... Made in Italy."],
            ["Ingredients_Full_Text", "Glucose syrup, Saccharose syrup, Citric acid, Vegetable fibre (Inulin), Flavours, Pectin, E100, E160b", "High", 1, "Composition: Glucose syrup, Saccharose syrup, Citric acid..."],
            ["Allergens_Present", "None declared", "High", 1, "MAY CONTAIN TRACES OF SHELLED NUTS, SOY, MILK"],
            ["Allergens_May_Contain", "Tree Nuts, Soy, Milk", "High", 1, "MAY CONTAIN TRACES OF SHELLED NUTS, SOY, MILK"],
            ["Energy_kcal_100g", "277.36", "High", 1, "ENERGIA 277,36 Kcal"],
            ["Energy_kJ_100g", "1160.11", "High", 1, "1160,11 Kj"],
            ["Protein_g_100g", "0.76", "High", 1, "PROTEINS 0,76 g"],
            ["Carbohydrates_g_100g", "67.79", "High", 1, "CARBOHYDRATES 67,79 g"],
            ["Sugars_g_100g", "67.51", "High", 1, "sugars 67,51 g"],
            ["Fat_g_100g", "0.39", "High", 1, "FATS 0,39 g"],
            ["Saturates_g_100g", "0.04", "High", 1, "saturated 0,04 g"],
            ["Fibre_g_100g", "0.38", "High", 1, "FIBER 0,38 g"],
            ["Salt_g_100g", "0", "High", 1, "SALT 0 g"],
            ["Origin_Summary", "Italy", "High", 1, "Made in Italy"],
            ["Vegan", "Suitable", "Medium", 1, "Ingredients appear vegan; flavours create minor uncertainty"],
            ["Vegetarian", "Suitable", "High", 1, "Ingredients appear vegetarian"],
            ["Coeliac", "Suitable", "High", 1, "No gluten-containing ingredients or gluten may-contain warning identified"],
            ["Lactose_Free", "Review Required", "Medium", 1, "May contain traces of milk"],
            ["Halal", "No", "High", 1, "No halal statement found"],
            ["Kosher", "No", "High", 1, "No kosher statement found"],
            ["Organic", "No", "High", 1, "No organic claim found"],
            ["Palm_Oil_Free", "Review Required", "Medium", 1, "Flavours may require confirmation"],
            ["GMO_Free", "Yes", "High", 1, "It doesn't contain OGM ingredients"],
            ["Review_Required", "Yes", "Medium", 1, "Lactose free and palm oil free require QA review"]
        ]

    if "ground cumin" in joined_text.lower():
        return [
            ["Product_Name", "GROUND CUMIN", "High", 1, "Product Name GROUND CUMIN"],
            ["Product_Description", "Ground to a medium fine powder", "High", 1, "Description of the product Ground to a medium fine powder"],
            ["Ingredients_Full_Text", "Cumin", "High", 1, "Ingredients declaration Cumin."],
            ["Allergens_Present", "None", "High", 4, "Allergens in product None"],
            ["Allergens_May_Contain", "Peanuts (supply chain possible airborne cross-contamination)", "Medium", 4, "Peanuts... Yes (Supplier handle on site, Possible airborne cross contamination...)"],
            ["Energy_kcal_100g", "427", "High", 3, "Nutrition information per 100g kcal 427"],
            ["Energy_kJ_100g", "1783", "High", 3, "kj 1783"],
            ["Protein_g_100g", "17.8", "High", 3, "Protein (g) 17.8"],
            ["Carbohydrates_g_100g", "33.7", "High", 3, "Carbohydrate (g) 33.7"],
            ["Sugars_g_100g", "2.3", "High", 3, "Sugar (g) 2.3"],
            ["Fat_g_100g", "22.3", "High", 3, "Fat (g) 22.3"],
            ["Saturates_g_100g", "1.5", "High", 3, "Saturates (g) 1.5"],
            ["Fibre_g_100g", "Not stated", "High", 3, "Nutrition table does not state fibre"],
            ["Salt_g_100g", "0.42", "High", 3, "Salt (g) 0.42"],
            ["Origin_Summary", "India – processed in UK", "High", 1, "Origin India – Processed in UK."],
            ["Vegan", "Suitable", "High", 3, "Product suitability Vegans YES"],
            ["Vegetarian", "Suitable", "High", 3, "Product suitability Vegetarians YES"],
            ["Coeliac", "Suitable (claimed)", "High", 3, "Product suitability Coeliacs YES"],
            ["Lactose_Free", "Suitable", "Medium", 4, "Milk not present in product; supplier handles milk on site"],
            ["Halal", "Suitable (not certified)", "High", 3, "Halal YES Not Certified"],
            ["Kosher", "Suitable (not certified)", "High", 3, "Kosher YES Not Certified"],
            ["Organic", "No", "High", 5, "No organic claim found"],
            ["Palm_Oil_Free", "Yes", "High", 1, "Ingredients declaration Cumin."],
            ["GMO_Free", "Yes", "High", 5, "Neither the product itself nor any component is produced from GM raw materials"],
            ["Review_Required", "Yes", "Medium", 4, "Customer to risk assess allergen warning from table"]
        ]

    return [
        ["Product_Name", "Not extracted", "Low", 1, "Mock AI does not recognise this sample yet"],
        ["Review_Required", "Yes", "Low", 1, "Unknown document format in mock mode"]
    ]

if uploaded_file:
    pdf_bytes = uploaded_file.read()
    pages = extract_pdf_text(pdf_bytes)
    results = mock_extract(uploaded_file.name, pages)

    df = pd.DataFrame(results, columns=["Field", "Value", "Confidence", "Source_Page", "Source_Quote"])

    left, right = st.columns([1.1, 1])

    with left:
        st.subheader("Extracted Output")

        edited_values = []
        for idx, row in df.iterrows():
            style = confidence_style(row["Confidence"])
            st.markdown(
                f"<div style='{style}'><b>{row['Field']}</b> — {row['Confidence']}</div>",
                unsafe_allow_html=True
            )
            new_value = st.text_input(
                label=row["Field"],
                value=str(row["Value"]),
                key=f"value_{idx}",
                label_visibility="collapsed"
            )
            edited_values.append(new_value)

            if st.button(f"View source: {row['Field']}", key=f"source_{idx}"):
                st.session_state["selected_page"] = int(row["Source_Page"])
                st.session_state["selected_quote"] = row["Source_Quote"]
                st.session_state["selected_field"] = row["Field"]

        df["Edited_Value"] = edited_values

        export_df = df[["Field", "Edited_Value", "Confidence", "Source_Page", "Source_Quote"]]

        output = io.BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            export_df.to_excel(writer, index=False, sheet_name="Extracted Spec")

        st.download_button(
            "Download Excel",
            data=output.getvalue(),
            file_name="extracted_spec.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    with right:
        st.subheader("Source Evidence")

        if "selected_field" in st.session_state:
            st.write(f"**Field:** {st.session_state['selected_field']}")
            st.write(f"**Page:** {st.session_state['selected_page']}")
            st.info(st.session_state["selected_quote"])
        else:
            st.write("Click a field source button to see evidence.")

        st.subheader("PDF Text Preview")
        page_numbers = [p["page"] for p in pages]
        selected = st.selectbox("Select page", page_numbers)

        selected_text = next(p["text"] for p in pages if p["page"] == selected)
        st.text_area("Page text", selected_text, height=400)
