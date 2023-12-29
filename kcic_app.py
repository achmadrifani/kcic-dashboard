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

st.set_page_config(layout="wide")
NDF_FOLDER = "src/ndf"


def download_data():
    ftp_host = 'publik.bmkg.go.id'
    ftp_user = 'amandemen'
    ftp_password = 'bmkg2303'  # Ganti dengan kata sandi yang sesuai
    pwx_ftp_path = f'/data/kcic/kcic_presentwx.csv'
    ndf_ftp_path = f'/data/kcic/kcic_ndf.csv'

    # Lokasi lokal untuk menyimpan file yang diunduh
    pwx_local_path = f'src/ndf/kcic_presentwx.csv'
    ndf_local_path = f'src/ndf/kcic_ndf.csv'

    # Buat koneksi ke FTP server
    ftp = FTP(ftp_host)
    ftp.login(user=ftp_user, passwd=ftp_password)

    # Buka file di mode binary dan unduh ke lokal
    with open(pwx_local_path, 'wb') as local_file:
        ftp.retrbinary(f"RETR {pwx_ftp_path}", local_file.write)

    with open(ndf_local_path, 'wb') as local_file:
        ftp.retrbinary(f"RETR {ndf_ftp_path}", local_file.write)

    # Tutup koneksi FTP
    ftp.quit()
    return pwx_local_path, ndf_local_path


def load_forecast_data(ndf_local_path):
    df = pd.read_csv(ndf_local_path, sep=";", parse_dates=["DATE"])
    return df

def load_presentwx_data(pwx_local_path):
    df = pd.read_csv(pwx_local_path, sep=";", parse_dates=["DATE"])
    return df

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
            </div>
        """
    return popup_content


st.header("KCIC Weather Forecast Dashboard")

pwx_local_path, ndf_local_path = download_data()
df_pwx = load_presentwx_data(pwx_local_path)
df_ndf = load_forecast_data(ndf_local_path)

gdf_track = gpd.read_file('src/kcic.geojson')
df_sta = pd.read_csv("src/track_ndf.csv")

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
    df_pwx = df_pwx.loc[df_pwx["NAME"] == station_name]
    df_combine = pd.concat([df_pwx, df_all_fct])
    df_combine = df_combine.sort_values(by=['DATE'])
    df_combine['DATE'] = df_combine["DATE"] + timedelta(hours=7)
    df_combine.drop_duplicates(subset=['DATE'], inplace=True, keep='last')
    df_grp = df_combine.groupby(by=df_combine["DATE"].dt.date)
    tanggal_list = list(df_grp.groups.keys())
    tanggal_list_string = [x.strftime("%d %b | ") for x in tanggal_list]
    tabs = st.tabs(tanggal_list_string)

    for tab, tanggal in zip(tabs, tanggal_list):
        df_tgl = df_grp.get_group(tanggal)
        cols = tab.columns(8)
        for col, (index, data) in zip(cols, df_tgl.iterrows()):
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
            col.markdown(markdown_content, unsafe_allow_html=True)
else:
    st.write("## Click on a station to see detailed forecast")
