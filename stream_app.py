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
from functools import lru_cache


today = datetime.now().date()
formatted_date = "9/23/25"

stqdm.pandas()
st.header("Geolocate ERAS Applicants")
st.write(
    f"Last update: {formatted_date} [Phillip Kim, MD, MPH](https://www.doximity.com/pub/phillip-kim-md-8dccc4e4)"
)
st.write(
    "Upload raw CSV file from ERAS download to view map and output to HTML file. No data is saved on the server for privacy protection. Any resulting HTML file chosen to be saved locally will be at the program's discretion."
)
st.write(
    "🛠️ Check out other tools-[Extract PDF Board Scores and FAILED attempts](https://extractscores.streamlit.app/)"
)
st.image("sample_geo.jpg")
eras = "https://auth.aamc.org/account/#/login?gotoUrl=http:%2F%2Fpdws.aamc.org%2Feras-pdws-web%2F"

tab1, tab2, tab3 = st.tabs(["🗂️ Step 1", "🗺️ Step 2", "📷 Step 3"])
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

    st.info(
        "Please note: Any MISSING **Permanent Address** in data file will be excluded."
    )

with tab2:
    check_image = st.checkbox(
        "Chere here to insert applicant profile image (MUST Complete Step 3)"
    )

    st.write(
        "Please locate and select downloaded CSV file for processing.  Once completed, please download the html file before moving to Step 3"
    )
    upload_file = st.file_uploader("Upload CSV file")
    expected_headers = [
        "Permanent Address",
        "Applicant Name",
        "AAMC ID",
        "Medical School of Graduation",
        "Medical School Type",
    ]
    optional_headers = [
        "Medical School Country",
        "Medical School Degree Date of Graduation",
        "USMLE Step 1 Status",
        "USMLE Step 1 Score",
        "USMLE Step 2 CK Score",
        "USMLE Step 2 CS Score",
        "USMLE Step 3 Score",
        "USMLE Step 3 Score",
        "COMLEX-USA Level 1 Status",
        "COMLEX-USA Level 1 Score",
        "COMLEX-USA Level 2 CE Score",
        "COMLEX-USA Level 2 PE Score",
        "COMLEX-USA Level 3 Score",
        "Division_Preference",
    ]

    # Simple cache for geocoding results
    geocoding_cache = {}

    # FUNCTION TO GET COORDINATES FROM GOOGLE MAPS
    def extract_lat_long_via_address(address_or_zipcode, applicant_name=None):
        # Check cache first
        cache_key = (
            f"{address_or_zipcode}_{applicant_name}"
            if applicant_name
            else address_or_zipcode
        )
        if cache_key in geocoding_cache:
            return geocoding_cache[cache_key]

        lat, lng = None, None
        verification_info = None

        # Guard missing/empty input
        if not address_or_zipcode:
            return None, None, None

        # Read API key from secrets; if unavailable, skip
        try:
            api_key = st.secrets["GOOGLE_API_KEY"]
        except Exception:
            return None, None, None

        base_url = "https://maps.googleapis.com/maps/api/geocode/json"
        endpoint = f"{base_url}?address={address_or_zipcode}&key={api_key}"
        r = requests.get(endpoint)
        if r.status_code not in range(200, 299):
            return None, None, None

        try:
            results = r.json()["results"][0]
            lat = results["geometry"]["location"]["lat"]
            lng = results["geometry"]["location"]["lng"]

            # Store verification information for address matching
            if applicant_name:
                formatted_address = results.get("formatted_address", "")
                verification_info = {
                    "applicant_name": applicant_name,
                    "input_address": address_or_zipcode,
                    "google_formatted_address": formatted_address,
                    "coordinates": (lat, lng),
                }
        except:
            pass

        # Cache the result
        geocoding_cache[cache_key] = (lat, lng, verification_info)
        return lat, lng, verification_info

    # Create a long and lat column for each row then apply to dataframe
    def enrich_with_geocoding_api(row):
        column_name = "Permanent Address"
        address_value = row[column_name]
        applicant_name = row.get("Applicant Name", "")
        address_lat, address_lng, verification_info = extract_lat_long_via_address(
            address_value, applicant_name
        )
        row["lat"] = address_lat
        row["lng"] = address_lng
        row["verification_info"] = verification_info
        return row

    # Create enhanced HTML with search and filtering functionality
    def create_enhanced_html_with_search(map_obj, geo_df, original_df):
        # Get all data for search and filtering
        search_data = []
        popup_data = []

        # Define headers for filtering and their display names
        filter_headers = {
            "Medical School Type": "School Type",
            "Medical School Country": "Country",
            "Division_Preference": "Division Pref",
            "Visa Sponsorship Needed": "Visa Needed",
            "Program_Signal": "Signal",
        }

        # Prepare filter data
        filter_options = {}
        for header, display_name in filter_headers.items():
            if header in original_df.columns:
                unique_values = original_df[header].dropna().unique().tolist()
                if unique_values:
                    filter_options[display_name] = sorted(unique_values)

        for idx, row in geo_df.iterrows():
            applicant_data = {
                "aamc_id": str(original_df["AAMC ID"].iloc[idx]),
                "name": original_df["Applicant Name"].iloc[idx],
                "lat": row["lat"],
                "lng": row["lng"],
            }
            # Add filterable data
            for header, display_name in filter_headers.items():
                if header in original_df.columns:
                    applicant_data[display_name] = original_df[header].iloc[idx]

            # Add all other data for generic search
            for col in original_df.columns:
                if col not in ["Permanent Address", "lat", "lng", "verification_info"]:
                    applicant_data[col] = str(original_df[col].iloc[idx])

            search_data.append(applicant_data)

            # Generate popup HTML for this applicant
            popup_html_content = popup_html(idx)
            popup_data.append(popup_html_content)

        # Create the enhanced HTML content
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ERAS Applicants Map</title>
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.7.1/dist/leaflet.css" />
    <script src="https://unpkg.com/leaflet@1.7.1/dist/leaflet.js"></script>
    <script src="https://unpkg.com/leaflet.markercluster@1.4.1/dist/leaflet.markercluster.js"></script>
    <link rel="stylesheet" href="https://unpkg.com/leaflet.markercluster@1.4.1/dist/MarkerCluster.css" />
    <link rel="stylesheet" href="https://unpkg.com/leaflet.markercluster@1.4.1/dist/MarkerCluster.Default.css" />
    <style>
        body {{
            margin: 0;
            padding: 0;
            font-family: Arial, sans-serif;
        }}
        #map {{
            height: 100vh;
            width: 100%;
        }}
        .control-container {{
            position: absolute;
            top: 10px;
            right: 10px;
            z-index: 1000;
            background: white;
            padding: 15px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            min-width: 320px;
            max-width: 350px;
            max-height: 95vh;
            overflow-y: auto;
        }}
        .search-input {{
            width: 100%;
            padding: 8px;
            border: 1px solid #ddd;
            border-radius: 4px;
            margin-bottom: 10px;
        }}
        .accordion {{
            margin-top: 10px;
        }}
        .accordion-item {{
            border-bottom: 1px solid #eee;
        }}
        .accordion-header {{
            background-color: #f7f7f7;
            padding: 10px;
            cursor: pointer;
            font-weight: bold;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .accordion-header:hover {{
            background-color: #e9e9e9;
        }}
        .accordion-content {{
            padding: 10px;
            display: none;
            max-height: 150px;
            overflow-y: auto;
        }}
        .accordion-content label {{
            display: block;
            margin-bottom: 5px;
        }}
        .legend {{
            margin-top: 15px;
            padding-top: 10px;
            border-top: 1px solid #eee;
        }}
        .legend-item {{
            display: flex;
            align-items: center;
            margin-bottom: 5px;
        }}
        .legend-color {{
            width: 18px;
            height: 18px;
            margin-right: 8px;
            border: 1px solid #ccc;
        }}
    </style>
</head>
<body>
    <div id="map"></div>
    <div class="control-container">
        <h3 style="margin-top: 0;">🔍 Search & Filter</h3>
        <input type="text" id="searchInput" class="search-input" placeholder="Search applicants..." />
        
        <div class="accordion" id="filterAccordion">
            { "".join([f'''
            <div class="accordion-item">
                <div class="accordion-header" onclick="toggleAccordion(this)">
                    <span>{name}</span>
                    <span>&#9660;</span>
                </div>
                <div class="accordion-content">
                    {"".join([f'<label><input type="checkbox" class="filter-checkbox" data-filter="{name}" value="{option}" onchange="filterMarkers()"> {option}</label>' for option in options])}
                </div>
            </div>
            ''' for name, options in filter_options.items()]) }
        </div>

        <div class="legend">
            <h4>Legend</h4>
            <div class="legend-item"><div class="legend-color" style="background-color: red;"></div> MD-US-Grad</div>
            <div class="legend-item"><div class="legend-color" style="background-color: darkblue;"></div> DO-US-Grad</div>
            <div class="legend-item"><div class="legend-color" style="background-color: gray;"></div> MD-IMG-Grad</div>
        </div>
    </div>

    <script>
        const searchData = {json.dumps(search_data)};
        const popupData = {json.dumps(popup_data)};
        
        var map = L.map('map').setView([{geo_df[["lat", "lng"]].mean().iloc[0]:.6f}, {geo_df[["lat", "lng"]].mean().iloc[1]:.6f}], 2);
        
        L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
            attribution: '© OpenStreetMap contributors'
        }}).addTo(map);
        
        var markers = L.markerClusterGroup();
        var markerData = [];

        searchData.forEach(function(data, index) {{
            let medschool_type = data["School Type"];
            let color = "gray";
            let tooltip = "MD-IMG-Grad";
            if (medschool_type === "US M.D. Private School" || medschool_type === "US M.D. Public School") {{
                color = "red";
                tooltip = "MD-US-Grad";
            }} else if (medschool_type === "US D.O. School") {{
                color = "darkblue";
                tooltip = "DO-US-Grad";
            }}
            
            var marker = L.marker([data.lat, data.lng], {{
                icon: L.icon({{
                    iconUrl: `data:image/svg+xml;charset=UTF-8,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32" class="marker"><path fill-opacity="0.9" stroke="%23000" stroke-width="0.5" fill="${{color}}" d="M16 0 C10.48 0 6 4.48 6 10 C6 16.5 16 32 16 32 C16 32 26 16.5 26 10 C26 4.48 21.52 0 16 0 Z M16 14 A4 4 0 0 1 12 10 A4 4 0 0 1 16 6 A4 4 0 0 1 20 10 A4 4 0 0 1 16 14 Z"/></svg>`,
                    iconSize: [28, 28],
                    iconAnchor: [14, 28],
                    popupAnchor: [0, -28]
                }}),
                title: data.name + ' (AAMC ID: ' + data.aamc_id + ')'
            }});
            
            if (popupData[index]) {{
                marker.bindPopup(popupData[index]);
            }}
            
            markerData.push({{
                marker: marker,
                data: data
            }});
        }});
        
        markerData.forEach(item => {{
            markers.addLayer(item.marker);
        }});

        map.addLayer(markers);
        
        const searchInput = document.getElementById('searchInput');
        searchInput.addEventListener('input', function() {{
            filterMarkers();
        }});

        function toggleAccordion(header) {{
            const content = header.nextElementSibling;
            if (content.style.display === "block") {{
                content.style.display = "none";
                header.querySelector('span:last-child').innerHTML = '&#9660;';
            }} else {{
                content.style.display = "block";
                header.querySelector('span:last-child').innerHTML = '&#9650;';
            }}
        }}

        function filterMarkers() {{
            const searchQuery = searchInput.value.toLowerCase();
            const activeFilters = {{}};
            document.querySelectorAll('.filter-checkbox:checked').forEach(cb => {{
                const filterName = cb.dataset.filter;
                if (!activeFilters[filterName]) {{
                    activeFilters[filterName] = [];
                }}
                activeFilters[filterName].push(cb.value);
            }});

            markers.clearLayers();
            
            markerData.forEach(item => {{
                let isMatch = true;

                for (const filterName in activeFilters) {{
                    if (!activeFilters[filterName].includes(String(item.data[filterName]))) {{
                        isMatch = false;
                        break;
                    }}
                }}
                if (!isMatch) return;

                if (searchQuery.length > 1) {{
                    let found = false;
                    for (const key in item.data) {{
                        if (String(item.data[key]).toLowerCase().includes(searchQuery)) {{
                            found = true;
                            break;
                        }}
                    }}
                    if (!found) {{
                        isMatch = false;
                    }}
                }}
                
                if (isMatch) {{
                    markers.addLayer(item.marker);
                }}
            }});
        }}
    </script>
</body>
</html>
        """

        # Save the enhanced HTML
        with open("geo_applicants_fixed.html", "w", encoding="utf-8") as f:
            f.write(html_content)

        # Also save to the old filename for compatibility with the download button
        with open("geo_applicants.html", "w", encoding="utf-8") as f:
            f.write(html_content)

    # --- Simplified standalone HTML generator (stable popups) ---
    def create_enhanced_html_with_search_simple(geo_df, original_df):
        """Generate an offline HTML file with reliable Leaflet popups and accordion filters."""
        # Build lightweight record list for JS with all filterable data
        records = []

        # Dynamically detect filterable columns (exclude non-filterable ones)
        excluded_columns = {
            "AAMC ID",
            "Applicant Name",
            "Permanent Address",
            "Medical School Type",
            "Medical School Country",
            "lat",
            "lng",
            "verification_info",
        }

        # Create smart abbreviations for column names
        def create_abbreviation(col_name):
            abbreviations = {
                "Division_Preference": "Div Pref",
                "Visa Sponsorship Needed": "Visa",
                "Program_Signal": "Signal",
                "USMLE Step 1 Status": "Step 1",
                "COMLEX-USA Level 1 Status": "COMLEX 1",
                "Selected to Interview": "Interview",
                "Application Status": "App Status",
                "Research Experience": "Research",
                "Publications": "Pubs",
                "Work Experience": "Work Exp",
                "Volunteer Experience": "Volunteer",
                "Leadership Experience": "Leadership",
                "Away Rotations": "Away Rots",
                "Home Institution": "Home Inst",
                "Step 2 CK Status": "Step 2 CK",
                "Step 2 CS Status": "Step 2 CS",
                "Step 3 Status": "Step 3",
                "COMLEX Level 2 Status": "COMLEX 2",
                "COMLEX Level 3 Status": "COMLEX 3",
            }
            return abbreviations.get(col_name, col_name.replace("_", " ")[:12])

        # Only include specific columns for accordion filters
        filter_headers = {
            "Division_Preference": "Div Pref",
            "Visa Sponsorship Needed": "Visa",
            "Program_Signal": "Signal",
        }

        # Collect unique values for accordion filters
        filter_options = {}
        for header, display_name in filter_headers.items():
            if header in original_df.columns:
                unique_vals = original_df[header].dropna().astype(str)
                unique_vals = unique_vals[unique_vals.str.strip() != ""]
                unique_vals = unique_vals[unique_vals.str.lower() != "nan"]
                if len(unique_vals) > 0:
                    filter_options[display_name] = sorted(unique_vals.unique().tolist())

        for idx, row in geo_df.iterrows():
            medtype = original_df.get(
                "Medical School Type", pd.Series(["Unknown"]) * len(original_df)
            ).iloc[idx]

            # Check if applicant has interview data
            interview_status = original_df.get(
                "Selected to Interview", pd.Series([""]) * len(original_df)
            ).iloc[idx]
            has_interview = (
                pd.notna(interview_status)
                and str(interview_status).strip() != ""
                and str(interview_status).lower() != "nan"
            )

            if has_interview:
                cls = "interview"  # Yellow star for interviewed applicants
            elif medtype in ("US M.D. Private School", "US M.D. Public School"):
                cls = "mdus"
            elif medtype == "US D.O. School":
                cls = "dous"
            else:
                cls = "img"

            record = {
                "aamc": str(original_df.get("AAMC ID", pd.Series([""])).iloc[idx]),
                "name": original_df.get("Applicant Name", pd.Series([""])).iloc[idx],
                "lat": float(row["lat"]),
                "lng": float(row["lng"]),
                "cls": cls,
                "popup": popup_html(idx),
            }

            # Add filterable fields to record
            for header, display_name in filter_headers.items():
                if header in original_df.columns:
                    val = original_df[header].iloc[idx]
                    record[display_name] = str(val) if pd.notna(val) else ""

            records.append(record)

        data_json = json.dumps(records, ensure_ascii=False)
        center_lat = float(geo_df["lat"].mean())
        center_lng = float(geo_df["lng"].mean())

        # Build accordion HTML sections
        accordion_html = ""
        for display_name, values in filter_options.items():
            if len(values) > 1:  # Only show if there are multiple options
                checkboxes = ""
                for val in values[:15]:  # Limit to first 15 to avoid too long lists
                    safe_id = val.replace(" ", "_").replace("-", "_").replace(".", "_")
                    checkboxes += f'<label><input type="checkbox" class="acc-filter" data-field="{display_name}" value="{val}" checked/> {val}</label>'

                accordion_html += f"""
                <div class="accordion-item">
                    <div class="accordion-header" onclick="toggleAccordion(this)">
                        <span>{display_name}</span>
                        <span class="accordion-icon">▼</span>
                    </div>
                    <div class="accordion-content">
                        {checkboxes}
                    </div>
                </div>"""

        # Enhanced HTML with person pin icons and accordion filters
        html_template = f"""<!DOCTYPE html>
<html><head><meta charset='utf-8'/><title>ERAS Applicants Map</title>
<meta name='viewport' content='width=device-width,initial-scale=1.0'/>
<link rel='stylesheet' href='https://unpkg.com/leaflet@1.9.4/dist/leaflet.css'/>
<script src='https://unpkg.com/leaflet@1.9.4/dist/leaflet.js'></script>
<script src='https://unpkg.com/leaflet.markercluster@1.5.3/dist/leaflet.markercluster.js'></script>
<link rel='stylesheet' href='https://unpkg.com/leaflet.markercluster@1.5.3/dist/MarkerCluster.css'/>
<link rel='stylesheet' href='https://unpkg.com/leaflet.markercluster@1.5.3/dist/MarkerCluster.Default.css'/>
<style>
html,body,#map{{height:100%;margin:0;font-family:Arial,Helvetica,sans-serif;}}
#map{{position:absolute;top:0;left:0;right:0;bottom:0;}}
.panel{{position:absolute;top:10px;left:10px;z-index:1000;background:#fff;padding:10px;border-radius:10px;box-shadow:0 4px 14px rgba(0,0,0,.18);width:280px;max-height:88vh;overflow:auto;}}
.panel h3{{margin:0 0 8px;font-size:15px;}}
.search-box{{width:calc(100% - 16px);padding:6px 8px;border:1px solid #ccc;border-radius:4px;margin-bottom:8px;font-size:13px;box-sizing:border-box;}}
.type-filters{{margin-bottom:10px;}}
.type-filters label{{display:block;font-size:12px;margin:2px 0;cursor:pointer;}}
.accordion-item{{border-bottom:1px solid #eee;}}
.accordion-header{{background:#f8f9fa;padding:8px 10px;cursor:pointer;font-weight:500;display:flex;justify-content:space-between;align-items:center;border-radius:4px;margin:2px 0;}}
.accordion-header:hover{{background:#e9ecef;}}
.accordion-content{{padding:6px 10px;display:none;max-height:120px;overflow-y:auto;}}
.accordion-content label{{display:block;font-size:11px;margin:2px 0;cursor:pointer;}}
.accordion-icon{{font-size:12px;transition:transform 0.2s;}}
.accordion-header.open .accordion-icon{{transform:rotate(180deg);}}
.legend{{margin-top:10px;font-size:12px;border-top:1px solid #eee;padding-top:8px;}}
.leg-row{{display:flex;align-items:center;margin-bottom:4px;}}
.pin-swatch{{width:16px;height:20px;margin-right:6px;}}
.small-note{{font-size:11px;color:#555;margin-top:6px;line-height:1.3;}}
</style></head><body>
<div id='map'></div>
<div class='panel'>
 <h3>🗺️ Applicants</h3>
 <input id='search' class='search-box' placeholder='Search name or AAMC ID...'/>
 <div class='type-filters'>
  <label><input type='checkbox' class='type-filter' value='interview' checked/> ⭐ Interview Scheduled</label>
  <label><input type='checkbox' class='type-filter' value='mdus' checked/> 🔴 MD-US Graduate</label>
  <label><input type='checkbox' class='type-filter' value='dous' checked/> 🟠 DO-US Graduate</label>
  <label><input type='checkbox' class='type-filter' value='img' checked/> ⚫ IMG Graduate</label>
 </div>
 <div class='accordion'>
  {accordion_html}
 </div>
 <div class='legend'>
  <div class='leg-row'>
    <svg width="16" height="20" viewBox="0 0 24 30" style="margin-right:8px;">
      <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z" fill="#ffd700" stroke="#000" stroke-width="1"/>
    </svg>
    Interview Scheduled
  </div>
  <div class='leg-row'>
    <svg width="16" height="20" viewBox="0 0 24 30" style="margin-right:8px;">
      <path d="M12 0C7.6 0 4 3.6 4 8c0 5.4 8 22 8 22s8-16.6 8-22c0-4.4-3.6-8-8-8z" fill="#d33" stroke="#000" stroke-width="1"/>
      <circle cx="12" cy="8" r="3" fill="white"/>
    </svg>
    MD-US Graduate
  </div>
  <div class='leg-row'>
    <svg width="16" height="20" viewBox="0 0 24 30" style="margin-right:8px;">
      <path d="M12 0C7.6 0 4 3.6 4 8c0 5.4 8 22 8 22s8-16.6 8-22c0-4.4-3.6-8-8-8z" fill="#ff8c00" stroke="#000" stroke-width="1"/>
      <circle cx="12" cy="8" r="3" fill="white"/>
    </svg>
    DO-US Graduate
  </div>
  <div class='leg-row'>
    <svg width="16" height="20" viewBox="0 0 24 30" style="margin-right:8px;">
      <path d="M12 0C7.6 0 4 3.6 4 8c0 5.4 8 22 8 22s8-16.6 8-22c0-4.4-3.6-8-8-8z" fill="#555" stroke="#000" stroke-width="1"/>
      <circle cx="12" cy="8" r="3" fill="white"/>
    </svg>
    IMG Graduate
  </div>
 </div>
 <div class='small-note'>Use search + filters. Click pins for details.</div>
</div>
<script>
const DATA = {data_json};
const map = L.map('map').setView([{center_lat:.6f}, {center_lng:.6f}], 2);
L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{attribution:'© OpenStreetMap contributors'}}).addTo(map);
const cluster = L.markerClusterGroup();
const allMarkers = [];

function buildIcon(cls){{
  let color = '#555';
  let iconHtml = '';
  
  if(cls === 'interview') {{
    iconHtml = '<svg width="24" height="30" viewBox="0 0 24 30" xmlns="http://www.w3.org/2000/svg"><path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z" fill="#ffd700" stroke="#000" stroke-width="1"/></svg>';
  }} else {{
    if(cls === 'mdus') color = '#d33';
    else if(cls === 'dous') color = '#ff8c00';
    
    iconHtml = '<svg width="24" height="30" viewBox="0 0 24 30" xmlns="http://www.w3.org/2000/svg"><path d="M12 0C7.6 0 4 3.6 4 8c0 5.4 8 22 8 22s8-16.6 8-22c0-4.4-3.6-8-8-8z" fill="' + color + '" stroke="#000" stroke-width="1"/><circle cx="12" cy="8" r="3" fill="white"/></svg>';
  }}
  
  return L.divIcon({{
    className: cls === 'interview' ? 'star-pin' : 'person-pin',
    html: iconHtml,
    iconSize: [24, 30],
    iconAnchor: [12, 30],
    popupAnchor: [0, -30]
  }});
}}

DATA.forEach(function(d){{
  if(isNaN(d.lat) || isNaN(d.lng)) return;
  const marker = L.marker([d.lat, d.lng], {{icon: buildIcon(d.cls), title: d.name + ' (AAMC ' + d.aamc + ')'}});
  marker.bindPopup(d.popup, {{maxWidth: 280, autoPan: true, closeButton: true}});
  marker._appData = d;
  allMarkers.push(marker);
  cluster.addLayer(marker);
}});
map.addLayer(cluster);

function toggleAccordion(header) {{
  const content = header.nextElementSibling;
  const isOpen = header.classList.contains('open');
  
  // Close all accordions first
  document.querySelectorAll('.accordion-header').forEach(function(h) {{
    h.classList.remove('open');
    h.nextElementSibling.style.display = 'none';
  }});
  
  if (!isOpen) {{
    header.classList.add('open');
    content.style.display = 'block';
  }}
}}

const searchInput = document.getElementById('search');
const typeFilters = Array.from(document.querySelectorAll('.type-filter'));
const accFilters = Array.from(document.querySelectorAll('.acc-filter'));

function applyFilters() {{
  const searchText = searchInput.value.trim().toLowerCase();
  const activeTypes = new Set(typeFilters.filter(function(cb) {{ return cb.checked; }}).map(function(cb) {{ return cb.value; }}));
  
  // Get accordion filter constraints
  const accConstraints = {{}};
  accFilters.forEach(function(cb) {{
    const field = cb.dataset.field;
    if (!accConstraints[field]) accConstraints[field] = [];
    if (cb.checked) accConstraints[field].push(cb.value);
  }});
  
  cluster.clearLayers();
  allMarkers.forEach(function(marker) {{
    const d = marker._appData;
    let show = true;
    
    // Type filter
    if (!activeTypes.has(d.cls)) show = false;
    
    // Search filter
    if (searchText && show) {{
      const matchName = d.name.toLowerCase().includes(searchText);
      const matchAAMC = d.aamc.toLowerCase().includes(searchText);
      if (!matchName && !matchAAMC) show = false;
    }}
    
    // Accordion filters
    if (show) {{
      for (const field in accConstraints) {{
        if (accConstraints[field].length > 0) {{
          const val = d[field] || '';
          // Only filter if the field has a non-empty value
          if (val !== '' && !accConstraints[field].includes(val)) {{
            show = false;
            break;
          }}
        }}
      }}
    }}
    
    if (show) cluster.addLayer(marker);
  }});
}}

searchInput.addEventListener('input', applyFilters);
typeFilters.forEach(function(cb) {{ cb.addEventListener('change', applyFilters); }});
accFilters.forEach(function(cb) {{ cb.addEventListener('change', applyFilters); }});
</script></body></html>"""

        with open("geo_applicants.html", "w", encoding="utf-8") as f:
            f.write(html_template)
        with open("geo_applicants_fixed.html", "w", encoding="utf-8") as f:
            f.write(html_template)

    # Function to format graduation date from "MMM-YY" to "MM/DD/YYYY"
    def format_grad_date(date_str):
        if not date_str or pd.isna(date_str) or str(date_str).strip() == "":
            return date_str

        date_str = str(date_str).strip()

        months = {
            "Jan": "01",
            "Feb": "02",
            "Mar": "03",
            "Apr": "04",
            "May": "05",
            "Jun": "06",
            "Jul": "07",
            "Aug": "08",
            "Sep": "09",
            "Oct": "10",
            "Nov": "11",
            "Dec": "12",
        }

        parts = date_str.split("-")
        if len(parts) == 2:
            month = months.get(parts[0])
            try:
                year = int(parts[1])

                # Assume years 00-30 are 2000s, 31-99 are 1900s
                if year <= 30:
                    year = 2000 + year
                elif year <= 99:
                    year = 1900 + year

                if month:
                    return f"{month}/01/{year}"
            except ValueError:
                pass

        return date_str

    # Format interview dates to mm/dd/yy format
    def format_interview_date(date_value):
        if pd.isna(date_value):
            return date_value

        date_str = str(date_value).strip()
        if date_str == "" or date_str.lower() == "nan":
            return date_value

        # Try to parse various date formats
        import datetime

        try:
            # Try common formats
            for fmt in [
                "%Y-%m-%d",
                "%m/%d/%Y",
                "%m-%d-%Y",
                "%Y/%m/%d",
                "%m/%d/%y",
                "%m-%d-%y",
            ]:
                try:
                    parsed_date = datetime.datetime.strptime(date_str, fmt)
                    return parsed_date.strftime("%m/%d/%y")
                except ValueError:
                    continue

            # If no format works, return original value
            return date_value
        except:
            return date_value

    # Create POPUP HTML FOR EACH APPLICANT
    def popup_html(row):
        # Simplified popup snippet (no full HTML/DOCTYPE) to avoid Leaflet popup rendering issues
        i = row
        applicant_name = df["Applicant Name"].iloc[i]
        aamc_id = df["AAMC ID"].iloc[i]

        if check_image:
            applicant_img = f"{aamc_id}.jpg"
            image_html = f'<div style="text-align:center;margin-bottom:6px;"><img src="{applicant_img}" alt="photo" width="90" height="90" style="border-radius:4px;object-fit:cover;"/></div>'
        else:
            image_html = ""

        medschool_name = df["Medical School of Graduation"].iloc[i]
        medschool_type = df["Medical School Type"].iloc[i]
        medschool_location = df["Medical School Country"].iloc[i]
        graduate_date = df["Medical School Degree Date of Graduation"].iloc[i]

        step1_status = df["USMLE Step 1 Status"].iloc[i]
        step1_score = df["USMLE Step 1 Score"].iloc[i]
        step2ck_score = df["USMLE Step 2 CK Score"].iloc[i]
        step2cs_score = df["USMLE Step 2 CS Score"].iloc[i]
        step3_score = df["USMLE Step 3 Score"].iloc[i]

        comlex1_status = df["COMLEX-USA Level 1 Status"].iloc[i]
        comlex1_score = df["COMLEX-USA Level 1 Score"].iloc[i]
        comlex2ce_score = df["COMLEX-USA Level 2 CE Score"].iloc[i]
        comlex3_score = df["COMLEX-USA Level 3 Score"].iloc[i]

        div_pref = df["Division_Preference"].iloc[i]

        visa_sponsorship = df.get("Visa Sponsorship Needed", pd.NA).iloc[i]
        program_signal = df.get("Program_Signal", pd.NA).iloc[i]
        hometown_city = df.get("Hometown City", pd.NA).iloc[i]
        selected_interview = df.get("Selected to Interview", pd.NA).iloc[i]

        left_col_color = "#3e95b5"
        right_col_color = "#f2f9ff"

        def has_value(val):
            if val is None:
                return False
            s = str(val).strip()
            if s == "" or s.lower() == "nan":
                return False
            return pd.notna(val)

        def emphasize_yes(val):
            text = str(val).strip()
            return f"<b>{text}</b>" if text.lower() == "yes" else text

        rows = []

        def add_row(label, value):
            if has_value(value):
                rows.append(
                    f"<tr><td style='background:{left_col_color};color:#fff;padding:3px 6px;font-size:11px;'>{label}</td>"
                    f"<td style='background:{right_col_color};padding:3px 6px;font-size:11px;'>{value}</td></tr>"
                )

        add_row("AAMC", aamc_id)
        add_row("Med School", medschool_name)
        add_row("Type", medschool_type)
        add_row("Country", medschool_location)
        if has_value(graduate_date):
            add_row("Grad Date", format_grad_date(graduate_date))
        add_row("Step1", step1_status)
        add_row("S1 Score", step1_score)
        add_row("S2 CK", step2ck_score)
        add_row("S2 CS", step2cs_score)
        add_row("S3", step3_score)
        add_row("COMLX1", comlex1_status)
        add_row("C1 Score", comlex1_score)
        add_row("C2 CE", comlex2ce_score)
        add_row("C3", comlex3_score)
        add_row("Div Pref", div_pref)
        add_row("Visa", emphasize_yes(visa_sponsorship))
        add_row("Signal", emphasize_yes(program_signal))
        add_row("HomeTown", hometown_city)
        add_row(
            "Interview",
            (
                format_interview_date(selected_interview)
                if has_value(selected_interview)
                else selected_interview
            ),
        )

        table_html = "".join(rows)
        popup = f"""
        <div style='width:255px;font-family:Arial, sans-serif;'>
            {image_html}
            <div style='text-align:center;font-weight:600;margin-bottom:4px;font-size:13px;'>{applicant_name}</div>
            <table style='width:100%;border-collapse:collapse;'>{table_html}</table>
        </div>
        """.strip().replace(
            "\n", ""
        )
        return popup

    geo_df = pd.DataFrame()
    if upload_file is not None:
        try:
            # Read as strings for consistency and normalize header whitespace
            df = pd.read_csv(upload_file, dtype=str)
            df.columns = [c.strip() for c in df.columns]
            # Remove unnamed columns that might cause issues
            df = df.loc[:, ~df.columns.str.contains("^Unnamed")]
            # Normalize blank-like values to actual NaN and drop rows that are fully empty
            df = df.replace({"": pd.NA, " ": pd.NA}).dropna(how="all")

            # Ensure Applicant Name column exists - required for processing
            if "Applicant Name" not in df.columns:
                st.error(
                    "Required column 'Applicant Name' is missing from the CSV file. Please ensure this column is present in your data export."
                )
                st.stop()

            total_count = df.shape[0]

            # total_count = len(df.index)
            # print out missing permanent address
            if any(df["Permanent Address"].isnull()):
                st.warning(
                    "Following with MISSING Permanent Address will not be processed:"
                )
                st.dataframe(df[df["Permanent Address"].isnull()])
                # df = df.dropna(subset=['Permanent Address'])
            # auto assign NaN to missing optional_headers
            missing_headers = [
                i for i in optional_headers if i not in set(df.columns.tolist())
            ]
            # Create missing optional headers and assign back to df
            if missing_headers:
                df = df.reindex(columns=df.columns.tolist() + list(missing_headers))

            # clean up the address
            # perform data analysis to obtain geo coord
            if all(col in df.columns for col in expected_headers):
                df["Permanent Address"] = df["Permanent Address"].str.replace(
                    "#", "", regex=False
                )
                if st.button("Analyze"):
                    df = df.dropna(subset=["Permanent Address"])
                    with st.spinner(
                        "Performing Analysis and Creating Map Coordinates this may take a while..."
                    ):
                        geo_df = df.progress_apply(enrich_with_geocoding_api, axis=1)
            else:
                # looks if CVS data contains required headers
                set_diff = [
                    x for x in expected_headers if x not in set(df.columns.tolist())
                ]
                st.error(
                    f"Required column header name(s) are missing to process: {list(set_diff)}"
                )
        except Exception as e:
            st.error(f"Error processing CSV file: {str(e)}")
            st.warning(
                "😬 Something went wrong: NOT in CSV file format or has missing data"
            )

    if not geo_df.empty:
        # count empty NaN in coordinates
        nan_count = geo_df["lng"].isna().sum()
        st.subheader(f"Mapped {geo_df.shape[0]-nan_count}/{total_count} Applicants")
        if nan_count:
            st.subheader(
                "😟 Following applicant(s) were unable to get coordinates.  You can try to fix the permanent address format and re-upload CSV"
            )
            st.dataframe(geo_df[geo_df["lng"].isnull()])

        # drop NaN and reset index to avoid indexing errors
        geo_df = geo_df.dropna(subset=["lat"])
        geo_df = geo_df.reset_index(drop=True)

        # Set default map location
        map_center = geo_df[["lat", "lng"]].mean().to_list()
        zoom_level = 2

        m = folium.Map(location=map_center, zoom_start=zoom_level)
        # if the points are too close to each other, cluster them, create a cluster overlay with MarkerCluster, add to m
        marker_cluster = MarkerCluster().add_to(m)
        # draw the markers and assign popup and hover texts
        # add the markers the the cluster layers so that they are automatically clustered
        for i, r in geo_df.iterrows():
            location = (r["lat"], r["lng"])
            # id foreign, US, DO
            medschool_type = df["Medical School Type"].iloc[i]
            if (
                medschool_type == "US M.D. Private School"
                or medschool_type == "US M.D. Public School"
            ):
                color = "red"
                tooltip = "MD-US-Grad"
            elif medschool_type == "US D.O. School":
                color = "darkblue"
                tooltip = "DO-US-Grad"
            else:
                color = "gray"
                tooltip = "MD-IMG-Grad"

            html = popup_html(i)
            folium.Marker(
                location=location,
                popup=html,
                tooltip=tooltip,
                icon=folium.Icon(color=color, icon="user", prefix="fa"),
            ).add_to(marker_cluster)

        # Call the simplified reliable HTML generator instead of complex one
        create_enhanced_html_with_search_simple(geo_df, df)
        folium_static(m, width=725)
        # use ste download button method to avoid clear recent data analysis upon download
        with open("geo_applicants.html", "rb") as file:
            btn = ste.download_button(
                label="Download file as HTML file",
                data=file,
                file_name="geo_applicants.html",
                mime="txt/html",
            )
            st.write(
                "Use a browser to open the downloaded HTML file for offline viewing"
            )

#####PROCESS PDF TO JPEG#####
with tab3:
    # Create a Streamlit app
    st.title("Applicant Photo PDF to Image Converter")
    st.markdown(
        """
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
    14. Move your downloaded **geo_applicants.html** in Step 2 into the processed JPEGs folder
    15. Open the geo_applicants.html file in a web-browser to view and interact applicant data
    """
    )
    st.info(
        "Please do NOT modify any file names upon download as this will impact the profile images in HTML"
    )
    # Upload multiple PDFs
    uploaded_files = st.file_uploader(
        "Upload multiple PDFs", type=["pdf"], accept_multiple_files=True
    )

    if uploaded_files:
        # Add a processing spinner
        with st.spinner("Converting PDFs to images..."):

            image_list = []

            # Create a BytesIO object to store the ZIP file
            zip_buffer = BytesIO()

            # Extract images from PDFs and save as JPGs in memory (BytesIO)
            for pdf_file in uploaded_files:
                # st.write(f"Processing file: {pdf_file.name}")  # Debug log

                pdf_file_name = pdf_file.name.split("_")[
                    1
                ]  # Get the name part from filename
                pdf_reader = PdfReader(pdf_file)
                num_pages = len(pdf_reader.pages)
                # st.write(f"Number of pages in {pdf_file.name}: {num_pages}")  # Debug log

                for page_num in range(num_pages):
                    page = pdf_reader.pages[page_num]
                    # st.write(f"Processing page {page_num + 1} of {pdf_file.name}")  # Debug log

                    try:
                        xObject = page["/Resources"]["/XObject"].get_object()
                        # st.write(f"Found XObject on page {page_num + 1} of {pdf_file.name}")  # Debug log

                        for obj in xObject:
                            if xObject[obj]["/Subtype"] == "/Image":
                                img = xObject[obj]
                                try:
                                    img_data = img.get_data()
                                    img_bytes = BytesIO(img_data)

                                    # Perform a quick validation: Ensure the data is in a supported format.
                                    if img_bytes.getbuffer().nbytes > 0:
                                        try:
                                            # Try to open the image
                                            img_pil = Image.open(img_bytes)
                                            # st.write(f"Image extracted from page {page_num + 1} of {pdf_file.name}")  # Debug log

                                            # Save the image as a BytesIO object
                                            img_io = BytesIO()
                                            img_pil.save(img_io, "JPEG")
                                            image_list.append(
                                                (f"{pdf_file_name}.jpg", img_io)
                                            )
                                        except UnidentifiedImageError:
                                            st.error(
                                                f"Invalid image data from file: {pdf_file.name}, page: {page_num + 1}"
                                            )
                                    else:
                                        st.error(
                                            f"Empty image data in file: {pdf_file.name}, page: {page_num + 1}"
                                        )
                                except (
                                    UnidentifiedImageError,
                                    Exception,
                                ) as e:  # Catch generic errors
                                    st.error(
                                        f"Error processing image from file: {pdf_file.name}, page: {page_num + 1} - {str(e)}"
                                    )
                                    continue  # Skip this image and move to the next
                    except KeyError:
                        # If there are no images in the page, skip it
                        st.warning(
                            f"No images found in file: {pdf_file.name}, page: {page_num + 1}"
                        )
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
                st.download_button(
                    "Click here to download ZIP",
                    data=zip_buffer.getvalue(),
                    file_name="converted_images.zip",
                    key="download_btn",
                )
            else:
                st.warning("No images were found or processed from the uploaded PDFs.")
