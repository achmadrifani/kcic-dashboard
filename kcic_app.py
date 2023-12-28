import streamlit as st
from streamlit_folium import st_folium
import folium
import pandas as pd
import geopandas as gpd
from datetime import datetime, timedelta

st.set_page_config(layout="wide")

def load_forecast_data():
    df = pd.read_csv("kcic_forecast.csv", sep=";", parse_dates=["DATE"])
    return df

def get_nearest_forecast(df):
    holder = []
    dfg = df.groupby("STATION")
    now = datetime.utcnow()

    for key, group_df in dfg:
        # Filter data untuk stasiun tertentu yang waktu prediksinya setelah waktu sekarang
        filtered_df = group_df[group_df["DATE"] > now]

        if not filtered_df.empty:
            # Pilih baris pertama (waktu terdekat)
            nearest_row = filtered_df.iloc[0]
            holder.append(nearest_row)

    # Gabungkan DataFrame yang dihasilkan dari setiap stasiun
    df_new = pd.DataFrame(holder)
    return df_new

def get_all_forecast(station_name,df):
    now = datetime.utcnow()
    df = df[df["DATE"] > now]
    df = df.loc[df["STATION"]==station_name]
    return df

def create_popup(row,df_fct):
    station = row["name_station"]
    df_fct_sta = df_fct[df_fct["STATION"]==station]
    print(wx_icon_dict[df_fct_sta['WEATHER'].iloc[0]])
    popup_content = f"""
            <strong>{df_fct_sta['STATION'].iloc[0]}</strong><br>
            <strong>{(df_fct_sta['DATE'].iloc[0]+timedelta(hours=7)).strftime("%d %b %Y %H:%M WIB")}</strong><br>
            <img src="{wx_icon_dict[df_fct_sta['WEATHER'].iloc[0]]}" alt="Weather Icon" style="width:40px;height:40px;"><br>
            {wx_caption_dict[df_fct_sta['WEATHER'].iloc[0]]}<br>
            Suhu: {df_fct_sta['T'].iloc[0]} °C<br>
            Kelembapan: {df_fct_sta['HU'].iloc[0]}%<br>
            Arah Angin: {wind_caption_dict[df_fct_sta['WD'].iloc[0]]}<br>
            Kecepatan Angin: {df_fct_sta['WS'].iloc[0]} km/h
        """
    return popup_content

wx_icon_dict = {0:"https://www.bmkg.go.id/asset/img/weather_icon/ID/cerah-am.png",
                1:"https://www.bmkg.go.id/asset/img/weather_icon/ID/cerah%20berawan-am.png",
                2:"https://www.bmkg.go.id/asset/img/weather_icon/ID/cerah%20berawan-am.png",
                3:"https://www.bmkg.go.id/asset/img/weather_icon/ID/berawan-am.png",
                4:"https://www.bmkg.go.id/asset/img/weather_icon/ID/berawan tebal-am.png",
                10:"https://www.bmkg.go.id/asset/img/weather_icon/ID/asap-am.png",
                45:"https://www.bmkg.go.id/asset/img/weather_icon/ID/kabut-am.png",
                60:"https://www.bmkg.go.id/asset/img/weather_icon/ID/hujan%20ringan-am.png",
                61:"https://www.bmkg.go.id/asset/img/weather_icon/ID/hujan%20sedang-am.png",
                63:"https://www.bmkg.go.id/asset/img/weather_icon/ID/hujan%20lebat-am.png",
                95:"https://www.bmkg.go.id/asset/img/weather_icon/ID/hujan%20petir-am.png",
                97:"https://www.bmkg.go.id/asset/img/weather_icon/ID/hujan%20petir-am.png"}
wx_caption_dict = {0:"Cerah",
                1:"Cerah Berawan",
                2:"Cerah Berawan",
                3:"Berawan",
                4:"Berawan Tebal",
                10:"Asap",
                45:"Kabut",
                60:"Hujan Ringan",
                61:"Hujan Sedang",
                63:"Hujan Lebat",
                95:"Hujan Petir",
                97:"Hujan Petir"}
wind_caption_dict = {"N":"Utara",
                     "NE":"Timur Laut",
                     "E":"Timur",
                     "SE":"Tenggara",
                     "S":"Selatan",
                     "SW":"Barat Daya",
                     "W":"Barat",
                     "NW":"Barat Laut"}

st.header("KCIC Weather Forecast Dashboard")

df = load_forecast_data()
gdf_track = gpd.read_file('src/kcic.geojson')
df_sta = pd.read_csv("src/stasiun_kcic.csv")
center = gdf_track.dissolve().centroid
center_lon = center.geometry.x
center_lat = center.geometry.y

m = folium.Map(location=[center_lat, center_lon], zoom_start=10)
folium.GeoJson(gdf_track).add_to(m)
df_fct = get_nearest_forecast(df)
for index,row in df_sta.iterrows():
    stat_icon = folium.features.CustomIcon('src/railway-station.png', icon_size=(30, 30))
    popup_content = create_popup(row,df_fct)
    tooltip_content = f"{row['name_station']}"
    folium.Marker([row["lat"],row["lon"]],
                  popup = folium.Popup(popup_content, max_width=300),
                  icon=stat_icon).add_to(m)

st_data = st_folium(m,use_container_width=True)
station_name = st_data['last_object_clicked_popup']

if station_name:
    station_name = station_name.split()
    station_name = f"{station_name[0]} {station_name[1]}"
    st.write(f"## Detailed Forecast for {station_name}")
    df_all_fct = get_all_forecast(station_name,df)
    df_grp = df_all_fct.groupby(by=df["DATE"].dt.date)
    tanggal_list = list(df_grp.groups.keys())
    tanggal_list_string = [x.strftime("%d %b | ") for x in tanggal_list]
    tabs = st.tabs(tanggal_list_string)

    for tab,tanggal in zip(tabs,tanggal_list):
        df_tgl = df_grp.get_group(tanggal)
        cols = tab.columns(df_tgl.shape[0])
        for col,(index,data) in zip(cols,df_tgl.iterrows()):
            markdown_content = f"""
                        <strong>{(data["DATE"] + timedelta(hours=7)).strftime("%H:%M WIB")}</strong><br>
                        <img src="{wx_icon_dict[data['WEATHER']]}" alt="Weather Icon" style="width:50px;height:50px;"><br>
                        {wx_caption_dict[data["WEATHER"]]}<br>
                        Suhu: {data['T']} °C<br>
                        Kelembapan: {data['HU']} %<br>
                        Angin: {wind_caption_dict[data['WD']]} \n{data['WS']}<br>
                    """
            col.markdown(markdown_content,unsafe_allow_html=True)
else:
    st.write("## Click on a station to see its detailed forecast")

