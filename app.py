import streamlit as st

st.set_page_config(page_title="WAVE PDF Extractor", page_icon="📊", layout="wide")

st.title("DuPont WAVE PDF Data Extractor")
st.write("Upload a DuPont WAVE engineering PDF report to extract structured data.")

uploaded_file = st.file_uploader("Choose a PDF file", type="pdf")

if uploaded_file is not None:
    import pandas as pd
    import tempfile
    import os
    from wave_extractor import extract_wave_data
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
        tmp_file.write(uploaded_file.getvalue())
        tmp_path = tmp_file.name
    
    try:
        with st.spinner("Extracting data from PDF..."):
            df = extract_wave_data(tmp_path, output_path=None)
        
        if len(df) > 0:
            st.success(f"Extracted {len(df)} rows of data")
            
            sections = df['Section'].unique()
            for section in sections:
                st.subheader(section)
                section_df = df[df['Section'] == section][['Parameter', 'Value', 'Unit']]
                st.dataframe(section_df, use_container_width=True, hide_index=True)
            
            st.subheader("Download Results")
            output = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx")
            df.to_excel(output.name, index=False, sheet_name='WAVE Data')
            
            with open(output.name, "rb") as f:
                st.download_button(
                    label="Download Excel File",
                    data=f,
                    file_name="wave_extracted_data.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            os.unlink(output.name)
        else:
            st.warning("No data could be extracted. The PDF may not contain the expected sections.")
    
    except Exception as e:
        st.error(f"Error processing PDF: {str(e)}")
    
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)

else:
    st.info("Please upload a WAVE PDF report to begin extraction.")
    
    st.subheader("Supported Sections")
    st.write("""
    - **RO System Overview**: Raw Feed, Total Concentrate, Net Product flows
    - **CCRO Overview**: Elements per PV, Recovery rates, Flow rates, Cycle durations
    - **RO Flow Table (Stage Level)**: Per-stage data for PF, CC1, CC Final
    """)
