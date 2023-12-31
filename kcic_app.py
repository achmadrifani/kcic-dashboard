import streamlit as st
from streamlit_folium import st_folium
import folium
import pandas as pd
import geopandas as gpd
from datetime import datetime, timedelta
import os
import requests
from ftplib import FTP
from helper_dict import wx_caption_dict, wind_caption_dict, wx_icon_dict
import pickle

st.set_page_config(layout="wide")
NDF_FOLDER = "src/ndf"


def download_data():
    ftp_host = 'publik.bmkg.go.id'
    ftp_user = 'amandemen'
    ftp_password = 'bmkg2303'  # Ganti dengan kata sandi yang sesuai
    pwx_ftp_path = f'/data/kcic/kcic_presentwx.csv'
    stp_ftp_path = f'/data/kcic/kcic_steps.csv'
    ndf_ftp_path = f'/data/kcic/kcic_ndf.csv'

    # Lokasi lokal untuk menyimpan file yang diunduh
    pwx_local_path = f'src/ndf/kcic_presentwx.csv'
    stp_local_path = f'src/ndf/kcic_steps.csv'
    ndf_local_path = f'src/ndf/kcic_ndf.csv'

    # Buat koneksi ke FTP server
    ftp = FTP(ftp_host)
    ftp.login(user=ftp_user, passwd=ftp_password)

    # Buka file di mode binary dan unduh ke lokal
    with open(pwx_local_path, 'wb') as local_file:
        ftp.retrbinary(f"RETR {pwx_ftp_path}", local_file.write)

    with open(stp_local_path, 'wb') as local_file:
        ftp.retrbinary(f"RETR {stp_ftp_path}", local_file.write)

    with open(ndf_local_path, 'wb') as local_file:
        ftp.retrbinary(f"RETR {ndf_ftp_path}", local_file.write)

    # Tutup koneksi FTP
    ftp.quit()
    return pwx_local_path, stp_local_path, ndf_local_path

def get_all_forecast(station_name, df):
    now = datetime.utcnow()
    df = df[df["DATE"] > now]
    df = df.loc[df["NAME"] == station_name]
    return df


def create_popup(row, df_fct):
    station = row["NAME"]
    df_fct_sta = df_fct[df_fct["NAME"] == station]
    popup_content = f"""<div style="text-align: center;">
            <strong>{df_fct_sta['NAME'].iloc[0]}</strong><br>
            <strong>{(df_fct_sta['DATE'].iloc[0] + timedelta(hours=7)).strftime("%d %b %Y %H:%M WIB")}</strong><br>
            <img src="{wx_icon_dict[df_fct_sta['WEATHER'].iloc[0]]}" alt="Weather Icon" style="width:40px;height:40px;"><br>
            {wx_caption_dict[df_fct_sta['WEATHER'].iloc[0]]}<br>
            Suhu: {df_fct_sta['T'].iloc[0]} °C<br>
            Kelembapan: {df_fct_sta['HU'].iloc[0]}%<br>
            Arah Angin: {wind_caption_dict[df_fct_sta['WD'].iloc[0]]}<br>
            Kecepatan Angin: {df_fct_sta['WS'].iloc[0]} km/h
            </div>"""
    return popup_content

def keep_first(series):
    return series.iloc[0]

def make_warning(df_stp):
    rain = df_stp.loc[df_stp["WEATHER"] > 4]
    if rain.empty:
        warning_text = "⚠️ No rain expected"
    else:
        rain_start = rain["DATE"].iloc[0]
        rain_end = rain["DATE"].iloc[-1]
        rain_duration = rain_end - rain_start
        wx_max = rain["WEATHER"].max()
        warning_text = f"""⚠️ Expect {wx_caption_dict[wx_max]} in {rain_start.strftime("%H:%M WIB")}"""
    return warning_text

st.header("KCIC Weather Forecast Dashboard")

pwx_local_path, stp_local_path, ndf_local_path = download_data()
df_pwx = pd.read_csv(pwx_local_path, sep=";", parse_dates=["DATE"])
df_ndf = pd.read_csv(ndf_local_path, sep=";", parse_dates=["DATE"])
df_stp = pd.read_csv(stp_local_path, sep=";", parse_dates=["DATE"])
gdf_track = gpd.read_file('src/kcic.geojson')
df_sta = pd.read_csv("src/point_kcic.csv")
gdf_wind = pickle.load(open("wind_forecast.pkl", "rb"))

m = folium.Map(location=[-6.579044952293415, 107.33359554188215], zoom_start=10, max_zoom=12, min_zoom=10,
               max_bounds=True, min_lat=-7.05, max_lat=-5.95, min_lon=106.5, max_lon=108.5)
folium.GeoJson(gdf_track).add_to(m)

for index, row in df_pwx.iterrows():
    popup_content = create_popup(row, df_pwx)
    tooltip_content = f"""
                    <div style="text-align: center;">
                    <strong>{row['NAME']}</strong><br>
                    <strong>{(row['DATE'] + timedelta(hours=7)).strftime("%d %b %Y %H:%M WIB")}</strong><br>
                    <img src="{wx_icon_dict[row['WEATHER']]}" alt="Weather Icon" style="width:40px;height:40px;"><br>
                    {wx_caption_dict[row['WEATHER']]}<br></div>"""
    if row["NAME"].startswith("Stasiun"):
        tr_icon = folium.features.CustomIcon('src/railway-station.png', icon_size=(30, 30))
    else:
        tr_icon = folium.CustomIcon(icon_image=f"{wx_icon_dict[row['WEATHER']]}", icon_size=(30, 30))
    folium.Marker([row['LAT'], row['LON']],
                  popup=folium.Popup(popup_content, max_width=300),
                  tooltip=tooltip_content,
                  icon=tr_icon).add_to(m)

st_data = st_folium(m, use_container_width=True)
station_name = st_data['last_object_clicked_popup']


if station_name:
    station_name = station_name.split('\n')
    station_name = f"{station_name[0]}"
    st.write(f"## Detailed Forecast for {station_name}")
    df_all_fct = get_all_forecast(station_name, df_ndf)
    df_all_fct['DATE'] = df_all_fct["DATE"] + timedelta(hours=7)
    fct_time = df_all_fct["DATE"].iloc[0]

    df_pwx = df_pwx.loc[df_pwx["NAME"] == station_name]
    pwx_time = df_pwx["DATE"].iloc[0] +timedelta(hours=7)
    df_stp = df_stp.loc[df_stp["NAME"] == station_name]
    df_stp['DATE'] = df_stp["DATE"] + timedelta(hours=7)
    warning_text = make_warning(df_stp.loc[df_stp["DATE"]>= datetime.utcnow()+timedelta(hours=7))
    df_now = df_stp.resample('30T', on='DATE').agg({'NAME':keep_first,
                                                    'LON':keep_first,
                                                    'LAT':keep_first,
                                                    'WEATHER' : 'max'})
    df_now.reset_index(col_level="DATE", inplace=True)
    df_now = df_now.loc[(df_now["DATE"] >= datetime.utcnow()+timedelta(hours=7)) & (df_now["DATE"] < fct_time)]
    df_pwx = df_pwx[['DATE','NAME', 'LON', 'LAT', 'WEATHER']]
    df_now = pd.concat([df_pwx, df_now], ignore_index=True)
    df_now.drop_duplicates(subset=['DATE'], inplace=True, keep='last')
    st.write("### Current Weather")

    warning_content = f"""
        <div style="background-color: #faee46; padding: 10px; border-radius: 10px; margin-bottom:10px;">
        <strong>{warning_text}</strong><br>
        </div>
        """
    st.markdown(warning_content, unsafe_allow_html=True)

    now_cols = st.columns(len(df_now))

    for col, (index, data) in zip(now_cols, df_now.iterrows()):
        if index == 0:
            time_indicator = "Now"
        else:
            time_indicator = (data["DATE"]).strftime("%H:%M WIB")

        markdown_content = f"""
                            <div style="background-color: #f0f0f0; padding: 10px; border-radius: 10px;">
                            <strong>{time_indicator}</strong><br>
                            <img src="{wx_icon_dict[data['WEATHER']]}" alt="Weather Icon" style="width:50px;height:50px;"><br>
                            {wx_caption_dict[data["WEATHER"]]}<br>
                            </div>
                            """
        col.markdown(markdown_content, unsafe_allow_html=True)

    st.write("### Forecast")
    df_grp = df_all_fct.groupby(by=df_all_fct["DATE"].dt.date)
    tanggal_list = list(df_grp.groups.keys())
    tanggal_list_string = [x.strftime("%d %b | ") for x in tanggal_list]
    tabs = st.tabs(tanggal_list_string)

    for tab, tanggal in zip(tabs, tanggal_list):
        df_tgl = df_grp.get_group(tanggal)
        cols = tab.columns(8)
        for col, (index, data) in zip(cols, df_tgl.iterrows()):
            try:
                markdown_content = f"""
                            <div style="background-color: lightblue; padding: 10px; border-radius: 10px;">
                            <strong>{(data["DATE"]).strftime("%H:%M WIB")}</strong><br>
                            <img src="{wx_icon_dict[data['WEATHER']]}" alt="Weather Icon" style="width:50px;height:50px;"><br>
                            {wx_caption_dict[data["WEATHER"]]}<br>
                            Suhu: {data['T']} °C<br>
                            Kelembapan: {data['HU']} %<br>
                            Angin: {wind_caption_dict[data['WD']]} \n{data['WS']} km/jam<br>
                            </div>
                        """
            except:
                markdown_content = f"""
                                    <div style="background-color: lightblue; padding: 10px; border-radius: 10px;">
                                    <strong>{(data["DATE"]).strftime("%H:%M WIB")}</strong><br>
                                    <img src="{wx_icon_dict[data['WEATHER']]}" alt="Weather Icon" style="width:50px;height:50px;"><br>
                                    {wx_caption_dict[data["WEATHER"]]}<br>
                                    </div>
                                    """
            col.markdown(markdown_content, unsafe_allow_html=True)
else:
    st.write("## Click on a station to see detailed forecast")
