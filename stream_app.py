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

today = datetime.now().date()
formatted_date = today.strftime("%m/%d/%Y")

stqdm.pandas()
st.header("Geolocate Applicants")
st.write(f"Last update: {formatted_date} [Phillip Kim, MD](https://www.doximity.com/pub/phillip-kim-md-8dccc4e4)")
st.write("Upload raw CSV file from ERAS download to output view and output HTML file. No data is saved on the server for privacy protection. Any resulting HTML file chosen to be saved locally will be at the program's discretion.")

st.image("sample_geo.jpg")
eras = "https://auth.aamc.org/account/#/login?gotoUrl=http:%2F%2Fpdws.aamc.org%2Feras-pdws-web%2F"

st.markdown(f"### HOW TO INSTRUCTIONS\n1. Login into [PDWS ERAS]({eras})\n2. Select **Active Applicants**\n3. Select All top table column\n4. Action to perform on selected applicants: CSV Export\n5. Edit CSV Export\n6. Add a new export template\n7. Create a **CSV Export Name**\n8. Personal >> Select\n   - **AAMC ID (required)**\n   - **Applicant Name (required)**\n   - **Permanent Address (required)**\n9. Education >> Select\n   - **Medical School of Graduation (required)**\n    - **Medical School Country**\n   - **Medical School Degree Date of Graduation**\n10. Exams/Licsenses/Certifications >> Select\n    - **ALL COMLEX AND STEP SCORES**\n11. Select **Bulk Print Requests** AND save your Print Job Name to your computer")
st.info("Please note: Any MISSING **Permanent Address** in data file will be excluded.")

upload_file = st.file_uploader("Upload CSV file")
expected_headers = ['Permanent Address', 'Applicant Name', 'AAMC ID', 'Medical School of Graduation'] 
optional_headers = ['Medical School Country', 'Medical School Degree Date of Graduation', 'USMLE Step 1 Score', 'USMLE Step 2 CK Score', 'USMLE Step 2 CS Score', 'USMLE Step 3 Score', 'USMLE Step 3 Score', 'COMLEX-USA Level 1 Score', 'COMLEX-USA Level 2 CE Score', 'COMLEX-USA Level 2 PE Score', 'COMLEX-USA Level 3 Score']

#FUNCTION TO GET COORDINATES FROM GOOGLE MAPS
st.cache()
def extract_lat_long_via_address(address_or_zipcode):
    lat, lng = None, None
    api_key = st.secrets['GOOGLE_API_KEY']
    base_url = "https://maps.googleapis.com/maps/api/geocode/json"
    endpoint = f"{base_url}?address={address_or_zipcode}&key={api_key}"
    # see how our endpoint includes our API key? Yes this is yet another reason to restrict the key
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
    medschool_name = df['Medical School of Graduation'].iloc[i]
    medschool_location =df['Medical School Country'].iloc[i]
    graduate_date = df['Medical School Degree Date of Graduation'].iloc[i]
    step1_score = df['USMLE Step 1 Score'].iloc[i]
    step2ck_score = df['USMLE Step 2 CK Score'].iloc[i]
    step2cs_score = df['USMLE Step 2 CS Score'].iloc[i]
    step3_score = df['USMLE Step 3 Score'].iloc[i]
    
    comlex1_score = df['COMLEX-USA Level 1 Score'].iloc[i]
    comlex2ce_score = df['COMLEX-USA Level 2 CE Score'].iloc[i]
    comlex2pe_score = df['COMLEX-USA Level 2 PE Score'].iloc[i]
    comlex3_score = df['COMLEX-USA Level 3 Score'].iloc[i]
    
    left_col_color = "#3e95b5"
    right_col_color = "#f2f9ff"

    html = """
        <!DOCTYPE html>
        <html>

        <center><h4 style="margin-bottom:5"; width="200px">{}</h4>""".format(applicant_name) + """</center>
        <center> <table style="height: 126px; width: 305px">
        <tbody>
        <tr>
        <td style="background-color: """+ left_col_color +"""; padding: 5px"><span style="color: #ffffff;"> AAMC ID </span></td>
        <td style="width: 150px;background-color: """+ right_col_color +"""; padding: 5px">{}</td>""".format(aamc_id) + """
        </tr>
        <tr>
        <td style="background-color: """+ left_col_color +"""; padding: 5px"><span style="color: #ffffff;"> Med School </span></td>
        <td style="width: 150px;background-color: """+ right_col_color +"""; padding: 5px">{}</td>""".format(medschool_name) + """
        </tr>
        <tr>
        <td style="background-color: """+ left_col_color +"""; padding: 5px"><span style="color: #ffffff;"> Country </span></td>
        <td style="width: 150px;background-color: """+ right_col_color +"""; padding: 5px">{}</td>""".format(medschool_location) + """
        </tr>
        <tr>
        <td style="background-color: """+ left_col_color +"""; padding: 5px"><span style="color: #ffffff;"> Graduation Date </span></td>
        <td style="width: 150px;background-color: """+ right_col_color +"""; padding: 5px">{}</td>""".format(graduate_date) + """
        </tr>
        <tr>
        <td style="background-color: """+ left_col_color +"""; padding: 5px"><span style="color: #ffffff;"> USMLE Step 1 </span></td>
        <td style="width: 150px;background-color: """+ right_col_color +"""; padding: 5px">{}</td>""".format(step1_score) + """
        </tr>
        <tr>
        <td style="background-color: """+ left_col_color +"""; padding: 5px"><span style="color: #ffffff;"> USMLE Step 2 CK </span></td>
        <td style="width: 150px;background-color: """+ right_col_color +"""; padding: 5px">{}</td>""".format(step2ck_score) + """
        </tr>
        <tr>
        <td style="background-color: """+ left_col_color +"""; padding: 5px"><span style="color: #ffffff;"> USMLE Step 2 CS </span></td>
        <td style="width: 150px;background-color: """+ right_col_color +"""; padding: 5px">{}</td>""".format(step2cs_score) + """
        </tr>
        <tr>
        <td style="background-color: """+ left_col_color +"""; padding: 5px"><span style="color: #ffffff;"> USMLE Step 3 </span></td>
        <td style="width: 150px;background-color: """+ right_col_color +"""; padding: 5px">{}</td>""".format(step3_score) + """
        </tr>
        <tr>
        <td style="background-color: """+ left_col_color +"""; padding: 5px"><span style="color: #ffffff;"> COMLEX Level 1 </span></td>
        <td style="width: 150px;background-color: """+ right_col_color +"""; padding: 5px">{}</td>""".format(comlex1_score) + """
        </tr>
        <tr>
        <td style="background-color: """+ left_col_color +"""; padding: 5px"><span style="color: #ffffff;"> COMLEX Level 2 CE </span></td>
        <td style="width: 150px;background-color: """+ right_col_color +"""; padding: 5px">{}</td>""".format(comlex2ce_score) + """
        </tr>
        <tr>
        <td style="background-color: """+ left_col_color +"""; padding: 5px"><span style="color: #ffffff;"> COMLEX Level 2 PE </span></td>
        <td style="width: 150px;background-color: """+ right_col_color +"""; padding: 5px">{}</td>""".format(comlex2pe_score) + """
        </tr>
        <tr>
        <td style="background-color: """+ left_col_color +"""; padding: 5px"><span style="color: #ffffff;"> COMLEX Level 3 </span></td>
        <td style="width: 150px;background-color: """+ right_col_color +"""; padding: 5px">{}</td>""".format(comlex3_score) + """
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
    mask = geo_df['lng'].isna()

    count_missing = mask.sum()
    st.subheader(f"Mapped {df.shape[0]-count_missing}/{df.shape[0]} Applicants")
    if count_missing: 
        st.subheader("😟 Following applicant(s) were unable to get coordinates.  You can try to fix the permanent address format and re-upload CSV") 
        st.dataframe(geo_df[geo_df['lng'].isnull()])
  
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
        medschool_type = df['Medical School Country'].iloc[i]
        do_schools = df['COMLEX-USA Level 1 Score'].iloc[i]
        us_schools = df['USMLE Step 1 Score'].iloc[i]
        if medschool_type == 'USA' and us_schools >= 100:
            color = 'red'
            tooltip = 'MD-US-Grad'
        elif medschool_type == 'USA' and do_schools >= 100:
            color = 'darkblue'
            tooltip = 'DO-US-Grad'
        else:
            color = 'gray'
            tooltip = 'MD-IMG-Grad'
    
        html = popup_html(i)
        folium.Marker(location=location, popup=html, tooltip=tooltip, icon=folium.Icon(color=color, icon='user', prefix='fa')).add_to(marker_cluster)


    m.save("geo_applicants.html")
    folium_static(m, width=725)
    #use ste package avoid clear recent data analysis upon download 
    with open("geo_applicants.html", "rb") as file:
        btn = ste.download_button(
            label="Download file as HTML file",
            data=file,
            file_name="geo_applicants.html",
            mime='txt/html'
        )


