import streamlit as st
import pandas as pd
from streamlit_folium import folium_static
import folium
import requests 
import json
from folium.plugins import MarkerCluster
from stqdm import stqdm
import streamlit_ext as ste

stqdm.pandas()
st.header("Geolocate Applicants")
st.write("Upload raw CSV file from ERAS download to output view and output HTML file. Below is an example output.")
st.image("sample_geo.jpg")
eras = "https://auth.aamc.org/account/#/login?gotoUrl=http:%2F%2Fpdws.aamc.org%2Feras-pdws-web%2F"
st.markdown(f"### HOW TO INSTRUCTIONS\n1. Login into [PDWS ERAS]({eras})\n2. Select **Active Applicants**\n3. Select All top table column\n4. Action to perform on selected applicants: CSV Export\n5. Edit CSV Export\n6. Add a new export template\n7. Create a **CSV Export Name**\n8. Personal >> Select\n   - **Applicant Name**\n   - **Permanent Address**\n9. Education >> Select\n   - **Medical School of Graduation**\n    - **Medical School Country**\n   - **Medical School Degree Date of Graduation**\n10. Exams/Licsenses/Certifications >> Select\n    - **ALL COMLEX AND STEP SCORES**\n11. Select **Bulk Print Requests** AND save your Print Job Name to your computer")

upload_file = st.file_uploader("Upload CSV file")
expected_headers = ['Permanent Address']

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
        #df = df.truncate(after=10)
        #clean up the address #
        if all(col in df.columns for col in expected_headers):
            df['Permanent Address'] = df['Permanent Address'].str.replace('#', '')
            #print("All the expected columns are present.")
            if st.button("Analyze"):
                with st.spinner("Performing Analysis and Creating Map Coordinates this may take a while..."):
                    geo_df = df.progress_apply(enrich_with_geocoding_api, axis=1)                
        else:
            st.warning("Not all the expected columns are present.")
    except:
        st.warning("NOT CSV format")

if not geo_df.empty:  
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

    folium_static(m, width=725)
    #use ste package avoid clear recent data analysis upon download 
    with open("geo_applicants.html", "rb") as file:
        btn = ste.download_button(
            label="Download file as HTML file",
            data=file,
            file_name="geo_applicants.html",
            mime='txt/html'
        )
