import streamlit as st
import pandas as pd
from streamlit_folium import folium_static
import folium
import requests 
import json
from folium.plugins import MarkerCluster
from stqdm import stqdm
import streamlit_ext as ste
from datetime import datetime

from PyPDF2 import PdfReader
from io import BytesIO
from PIL import Image, UnidentifiedImageError
import zipfile


today = datetime.now().date()
formatted_date = '10/2/23'

stqdm.pandas()
st.header("Geolocate ERAS Applicants")
st.write(f"Last update: {formatted_date} [Phillip Kim, MD, MPH](https://www.doximity.com/pub/phillip-kim-md-8dccc4e4)")
st.write("Upload raw CSV file from ERAS download to view map and output to HTML file. No data is saved on the server for privacy protection. Any resulting HTML file chosen to be saved locally will be at the program's discretion.")
st.write("🛠️ Check out other tools-[Extract PDF Board Scores and FAILED attempts](https://extractscores.streamlit.app/)")
st.image("sample_geo.jpg")
eras = "https://auth.aamc.org/account/#/login?gotoUrl=http:%2F%2Fpdws.aamc.org%2Feras-pdws-web%2F"

tab1, tab2, tab3 = st.tabs(['🗂️ Step 1', '🗺️ Step 2', '📷 Step 3'])
with tab1:
    markdown_text = f"""
    # 2023 ERAS Website Updates

    The 2023 ERAS website has undergone significant improvements, including an enhanced user interface and additional changes to data categories. A crucial feature of the web application is its utilization of applicants' permanent addresses to call the Google Earth API, retrieving longitude and latitude values. This functionality is essential for accurately pinning each applicant's location on the map. To ensure the proper functioning of this system, please follow these mandatory instructions:

    1. **Login into PDWS ERAS**
    2. Go to the **Applications** section in the top menu.
    3. Select **Exports**.
    4. Click on **Add Export Template**.
    5. Enter a filename for the CVS Export Name.
    6. **PLEASE DRAG OR SELECT THE FOLLOWING DATA CATEGORIES AND DATA TYPES TO EXPORT:**
    - **Personal**
        - Applicant Name
        - Permanent Address
    - **Education**
        - Medical School of Graduation
        - Medical School Type
        - Medical School Country
        - Medical School Degree Date of Graduation
    - **Exams/Licenses/Certifications**
        - COMLEX-USA Level 1 Status
        - COMLEX-USA Level 1 Score
        - COMLEX-USA Level 2 PE Score
        - COMLEX-USA Level 3 Score
        - USMLE Step 1 Status
        - USMLE Step 1 Score
        - USMLE Step 2 CK Score
        - USMLE Step 3 Score
        - USMLE Step 2 CS Score
    - **Geographic Presence**
        - Division Preference
    7. Back to Applications and select Current Results
    8. Select all from top box (may need to repeat for each page)
    9. Select Actions then choose CSV Export
    10. Select the saved CSV Template to run the data extraction
    11. Select Bulk Print Request to find your recent CSV template  
    12. Save to your local drive then move to Step 2 
    """

    st.markdown(markdown_text)


    st.info("Please note: Any MISSING **Permanent Address** in data file will be excluded.")

with tab2:
    check_image = st.checkbox ("Chere here to insert applicant profile image (MUST Complete Step 3)")
 
    st.write("Please locate and select downloaded CSV file for processing")
    upload_file = st.file_uploader("Upload CSV file")
    expected_headers = ['Permanent Address', 'Applicant Name', 'AAMC ID', 'Medical School of Graduation', 'Medical School Type'] 
    optional_headers = ['Medical School Country', 'Medical School Degree Date of Graduation', 'USMLE Step 1 Status','USMLE Step 1 Score', 'USMLE Step 2 CK Score', 'USMLE Step 2 CS Score', 'USMLE Step 3 Score', 'USMLE Step 3 Score','COMLEX-USA Level 1 Status', 'COMLEX-USA Level 1 Score', 'COMLEX-USA Level 2 CE Score', 'COMLEX-USA Level 2 PE Score', 'COMLEX-USA Level 3 Score', 'Division_Preference']

    # FUNCTION TO GET COORDINATES FROM GOOGLE MAPS
    st.cache()
    def extract_lat_long_via_address(address_or_zipcode):
        lat, lng = None, None
        api_key = st.secrets['GOOGLE_API_KEY']
        base_url = "https://maps.googleapis.com/maps/api/geocode/json"
        endpoint = f"{base_url}?address={address_or_zipcode}&key={api_key}"
        r = requests.get(endpoint)
        if r.status_code not in range(200, 299):
            return None, None
        try:
            results = r.json()['results'][0]
            lat = results['geometry']['location']['lat']
            lng = results['geometry']['location']['lng']
        except:
            pass
        return lat, lng

    # Create a long and lat column for each row then apply to dataframe
    def enrich_with_geocoding_api(row):
        column_name = 'Permanent Address'
        address_value = row[column_name]
        address_lat, address_lng = extract_lat_long_via_address(address_value)
        row['lat'] = address_lat
        row['lng'] = address_lng
        return row

    # Create POPUP HTML FOR EACH APPLICANT
    def popup_html(row):
        i = row
        applicant_name=df['Applicant Name'].iloc[i]
        aamc_id=df['AAMC ID'].iloc[i]

        if check_image:
            applicant_img = f"{aamc_id}.jpg"
            image_html = f'<center><img src={applicant_img} alt="logo" width=100 height=100 ></center>'
        else:
            image_html = f'<center></center>'

        medschool_name = df['Medical School of Graduation'].iloc[i]
        medschool_type = df['Medical School Type'].iloc[i]
        medschool_location =df['Medical School Country'].iloc[i]
        graduate_date = df['Medical School Degree Date of Graduation'].iloc[i]

        step1_status = df['USMLE Step 1 Status'].iloc[i]
        step1_score = df['USMLE Step 1 Score'].iloc[i]
        step2ck_score = df['USMLE Step 2 CK Score'].iloc[i]
        step2cs_score = df['USMLE Step 2 CS Score'].iloc[i]
        step3_score = df['USMLE Step 3 Score'].iloc[i]
        
        comlex1_status = df['COMLEX-USA Level 1 Status'].iloc[i]
        comlex1_score = df['COMLEX-USA Level 1 Score'].iloc[i]
        comlex2ce_score = df['COMLEX-USA Level 2 CE Score'].iloc[i]
        comlex2pe_score = df['COMLEX-USA Level 2 PE Score'].iloc[i]
        comlex3_score = df['COMLEX-USA Level 3 Score'].iloc[i]

        div_pref = df['Division_Preference'].iloc[i]
        
        left_col_color = "#3e95b5"
        right_col_color = "#f2f9ff"

        html = f"""
            <!DOCTYPE html>
            <html>
            {image_html}
            <center><h4 style="margin-bottom:5"; width="200px">{applicant_name}</h4></center>

            <center> <table style="height: 126px; width: 305px;">
            <tbody>
            <tr>
            <td style="background-color: {left_col_color}; padding: 5px"><span style="color: #ffffff;"> AAMC ID </span></td>
            <td style="width: 150px;background-color: {right_col_color}; padding: 5px">{aamc_id}</td>
            </tr>
            <tr>
            <td style="background-color: {left_col_color}; padding: 5px"><span style="color: #ffffff;"> Med School </span></td>
            <td style="width: 150px;background-color: {right_col_color}; padding: 5px">{medschool_name}</td>
            </tr>
            <tr>
            <td style="background-color: {left_col_color}; padding: 5px"><span style="color: #ffffff;"> Med School Type </span></td>
            <td style="width: 150px;background-color: {right_col_color}; padding: 5px">{medschool_type}</td>
            </tr>
            <tr>
            <td style="background-color: {left_col_color}; padding: 5px"><span style="color: #ffffff;"> Country </span></td>
            <td style="width: 150px;background-color: {right_col_color}; padding: 5px">{medschool_location}</td>
            </tr>
            <tr>
            <td style="background-color: {left_col_color}; padding: 5px"><span style="color: #ffffff;"> Graduation Date </span></td>
            <td style="width: 150px;background-color: {right_col_color}; padding: 5px">{graduate_date}</td>
            </tr>
            <tr>
            <td style="background-color: {left_col_color}; padding: 5px"><span style="color: #ffffff;"> USMLE Step 1 </span></td>
            <td style="width: 150px;background-color: {right_col_color}; padding: 5px">{step1_status}</td>
            </tr>
            <tr>
            <td style="background-color: {left_col_color}; padding: 5px"><span style="color: #ffffff;"> USMLE Step 1 Score </span></td>
            <td style="width: 150px;background-color: {right_col_color}; padding: 5px">{step1_score}</td>
            </tr>
            <tr>
            <td style="background-color: {left_col_color}; padding: 5px"><span style="color: #ffffff;"> USMLE Step 2 CK </span></td>
            <td style="width: 150px;background-color: {right_col_color}; padding: 5px">{step2ck_score}</td>
            </tr>
            <tr>
            <td style="background-color: {left_col_color}; padding: 5px"><span style="color: #ffffff;"> USMLE Step 2 CS </span></td>
            <td style="width: 150px;background-color: {right_col_color}; padding: 5px">{step2cs_score}</td>
            </tr>
            <tr>
            <td style="background-color: {left_col_color}; padding: 5px"><span style="color: #ffffff;"> USMLE Step 3 </span></td>
            <td style="width: 150px;background-color: {right_col_color}; padding: 5px">{step3_score}</td>
            </tr>
            <tr>
            <td style="background-color: {left_col_color}; padding: 5px"><span style="color: #ffffff;"> COMLEX Level 1 </span></td>
            <td style="width: 150px;background-color: {right_col_color}; padding: 5px">{comlex1_status}</td>
            </tr>
            <tr>
            <td style="background-color: {left_col_color}; padding: 5px"><span style="color: #ffffff;"> COMLEX Level 1 Score </span></td>
            <td style="width: 150px;background-color: {right_col_color}; padding: 5px">{comlex1_score}</td>
            </tr>
            <tr>
            <td style="background-color: {left_col_color}; padding: 5px"><span style="color: #ffffff;"> COMLEX Level 2 CE </span></td>
            <td style="width: 150px;background-color: {right_col_color}; padding: 5px">{comlex2ce_score}</td>
            </tr>

            <tr>
            <td style="background-color:{left_col_color}; padding: 5px"><span style="color: #ffffff;"> COMLEX Level 3 </span></td>
            <td style="width: 150px;background-color: {right_col_color}; padding: 5px">{comlex3_score}</td>
            </tr>
            <tr>
            <td style="background-color:{left_col_color}; padding: 5px"><span style="color: #ffffff;"> Division Pref</span></td>
            <td style="width: 150px;background-color: {right_col_color}; padding: 5px">{div_pref}</td>
            </tr>
            </tbody>
            </table></center>
            </html>
            """ 
        return html

    geo_df = pd.DataFrame()
    if upload_file is not None: 
        try:
            df = pd.read_csv(upload_file)
            total_count = df.shape[0]
            
            #total_count = len(df.index)
            #print out missing permanent address
            if any(df['Permanent Address'].isnull()):
                st.warning("Following with MISSING Permanent Address will not be processed:")
                st.dataframe(df[df['Permanent Address'].isnull()])
                #df = df.dropna(subset=['Permanent Address'])
            #auto assign NaN to missing optional_headers
            missing_headers = [i for i in optional_headers if i not in set(df.columns.tolist())]
            #create missing headers first then assign 
            if missing_headers:
                df.reindex(columns=df.columns.tolist() + list(missing_headers))
        
            #clean up the address 
            #perform data analysis to obtain geo coord
            if all(col in df.columns for col in expected_headers):
                df['Permanent Address'] = df['Permanent Address'].str.replace('#', '')
                if st.button("Analyze"):
                    df = df.dropna(subset=['Permanent Address'])
                    with st.spinner("Performing Analysis and Creating Map Coordinates this may take a while..."):
                        geo_df = df.progress_apply(enrich_with_geocoding_api, axis=1)                     
            else:
                #looks if CVS data contains required headers
                set_diff = [x for x in expected_headers if x not in set(df.columns.tolist())]
                st.error(f"Required column header name(s) are missing to process: {list(set_diff)}")
        except:
            st.warning("😬 Something went wrong: NOT in CSV file format or has missing data")

    if not geo_df.empty:
        #count empty NaN in coordinates
        nan_count = geo_df['lng'].isna().sum()
        st.subheader(f"Mapped {geo_df.shape[0]-nan_count}/{total_count} Applicants")
        if nan_count: 
            st.subheader("😟 Following applicant(s) were unable to get coordinates.  You can try to fix the permanent address format and re-upload CSV") 
            st.dataframe(geo_df[geo_df['lng'].isnull()])
        #drop NaN and reset index to avoid indexing errors
        geo_df = geo_df.dropna(subset=["lat"])
        geo_df = geo_df.reset_index(drop=True)

        m = folium.Map(location=geo_df[["lat", "lng"]].mean().to_list(), zoom_start=2)
        # if the points are too close to each other, cluster them, create a cluster overlay with MarkerCluster, add to m
        marker_cluster = MarkerCluster().add_to(m)
        # draw the markers and assign popup and hover texts
        # add the markers the the cluster layers so that they are automatically clustered               
        for i,r in geo_df.iterrows():
            location = (r["lat"], r["lng"])
            #id foreign, US, DO
            medschool_type = df['Medical School Type'].iloc[i]
            if medschool_type == 'US M.D. Private School' or medschool_type == 'US M.D. Public School':
                color = 'red'
                tooltip = 'MD-US-Grad'
            elif medschool_type == 'US D.O. School':
                color = 'darkblue'
                tooltip = 'DO-US-Grad'
            else:
                color = 'gray'
                tooltip = 'MD-IMG-Grad'
        
            html = popup_html(i)
            folium.Marker(location=location, popup=html, tooltip=tooltip, icon=folium.Icon(color=color, icon='user', prefix='fa')).add_to(marker_cluster)

        m.save("geo_applicants.html")
        folium_static(m, width=725)
        #use ste download button method to avoid clear recent data analysis upon download 
        with open("geo_applicants.html", "rb") as file:
            btn = ste.download_button(
                label="Download file as HTML file",
                data=file,
                file_name="geo_applicants.html",
                mime='txt/html'
            )
            st.write("Use a browser to open the downloaded HTML file for offline viewing")

#####PROCESS PDF TO JPEG#####
with tab3:
    # Create a Streamlit app
    st.title("Applicant Photo PDF to Image Converter")
    st.markdown("""
    1. Login into AAMC PDWS
    2. Go to Applications, click Active Applicants
    3. Click all or selected applicants checkbox 
    4. Click ACTIONS (100 APPLICANTS) 
    5. Click View/Print Application
    6. Name Print Job Name e.g. Photos1, Photos2…
    7. Select **Photograph** In Documents 
    8. Check Bulk Print (may be delayed, so check back later for complete status)
    9. Download to your local drive
    10. Unzip the folder 
    11. USE BELOW TO UPLOAD selected PDFs to process into JPEGs
    12. Download the Zip folder 
    13. Unzip the folder to get all processed JPEGs
    14. Move your downloaded geo_applicants.html in Step 2 into the processed JPEGs 
    15. Open the geo_applicants.html file in a web-browser
    """)
    st.error("Please do NOT modify any file names upon download as this will impact the profile images in HTML")
    # Upload multiple PDFs
    uploaded_files = st.file_uploader("Upload multiple PDFs", type=["pdf"], accept_multiple_files=True)
    
    if uploaded_files is not None:
        # Add a processing spinner
        with st.spinner("Converting PDFs to images..."):
    
            image_list = []
    
            # Create a BytesIO object to store the ZIP file
            zip_buffer = BytesIO()
    
            # Extract images from PDFs and save as JPGs in memory (BytesIO)
            for pdf_file in uploaded_files:
                pdf_file_name = pdf_file.name.split("_")[1]  # Get the name part from filename
                pdf_reader = PdfReader(pdf_file)
                num_pages = len(pdf_reader.pages)
    
                for page_num in range(num_pages):
                    page = pdf_reader.pages[page_num]
    
                    try:
                        xObject = page['/Resources']['/XObject'].get_object()
    
                        for obj in xObject:
                            if xObject[obj]['/Subtype'] == '/Image':
                                img = xObject[obj]
                                img_data = img.get_data()
                                img_bytes = BytesIO(img_data)
    
                                # Try to open the image
                                try:
                                    img_pil = Image.open(img_bytes)
                                    
                                    # Save the image as a BytesIO object
                                    img_io = BytesIO()
                                    img_pil.save(img_io, 'JPEG')
                                    image_list.append((f"{pdf_file_name}_page{page_num+1}.jpg", img_io))
    
                                except UnidentifiedImageError:
                                    # Log the filename and the page where the error occurred
                                    st.error(f"Error processing image from file: {pdf_file.name}, page: {page_num + 1}")
                                    continue  # Skip this image and move to the next
                    except KeyError:
                        # If there are no images in the page, skip it
                        st.warning(f"No images found in file: {pdf_file.name}, page: {page_num + 1}")
                        continue
    
            # Create a ZIP file in memory
            if image_list:
                with zipfile.ZipFile(zip_buffer, "w") as zipf:
                    for img_name, img_io in image_list:
                        img_io.seek(0)
                        zipf.writestr(img_name, img_io.read())
    
                st.success("Images converted and zipped successfully!")
    
                # Provide a link to download the ZIP file
                st.markdown("### Download ZIP file")
                st.download_button("Click here to download ZIP", data=zip_buffer.getvalue(), file_name="converted_images.zip", key="download_btn")
            else:
                st.warning("No images were found or processed from the uploaded PDFs.")

