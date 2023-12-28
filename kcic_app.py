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


def download_ndf_kecamatan(province):
    """Mengambil data ndf dan menyimpan kedalam local untuk efisiensi request ke server"""
    url = f"http://202.90.198.220/MEWS/CSV/kecamatanforecast-{province}.csv"

    if not os.path.exists(NDF_FOLDER):
        os.makedirs(NDF_FOLDER)

    file_name = os.path.join(NDF_FOLDER, f"kecamatanforecast-{province}.csv")

    response = requests.get(url)
    if response.status_code == 200:
        with open(file_name, 'wb') as file:
            file.write(response.content)
        print(f"Data for {province} downloaded to {file_name}")
    else:
        print(f"Failed downloading data {province}. Status code: {response.status_code}")
    return file_name

def download_presentwx(province):
    ftp_host = 'publik.bmkg.go.id'
    ftp_user = 'amandemen'
    ftp_password = 'bmkg2303'  # Ganti dengan kata sandi yang sesuai
    ftp_file_path = f'/data/presentweather-{province}.csv'

    # Lokasi lokal untuk menyimpan file yang diunduh
    local_file_path = f'src/ndf/presentweather-{province}.csv'

    # Buat koneksi ke FTP server
    ftp = FTP(ftp_host)
    ftp.login(user=ftp_user, passwd=ftp_password)

    # Buka file di mode binary dan unduh ke lokal
    with open(local_file_path, 'wb') as local_file:
        ftp.retrbinary(f"RETR {ftp_file_path}", local_file.write)

    # Tutup koneksi FTP
    ftp.quit()
    return local_file_path

def merge_ndf_kecamatan():
    dfs = []
    for province in ['jakarta', 'jawabarat']:
        fname = download_ndf_kecamatan(province)
        df = pd.read_csv(fname, sep=";",
                         names=["AREA_ID", "DATE", "TMIN", "TMAX", "HUMIN", "HUMAX", "HU", "T", "WEATHER", "WD", "WS"])
        dfs.append(df)
    df_ndf = pd.concat(dfs, ignore_index=True)
    df_sta = pd.read_csv("src/track_ndf.csv")

    dfs = []
    for id, name, lon, lat in zip(df_sta['id'], df_sta['name'], df_sta['lon'], df_sta['lat']):
        df = df_ndf.loc[df_ndf['AREA_ID'] == id]
        df["NAME"] = name
        df["LON"] = lon
        df["LAT"] = lat
        df = df[['NAME', 'LON', 'LAT', 'DATE', 'TMIN', 'TMAX', 'HUMIN', 'HUMAX', 'HU', 'T', 'WEATHER', 'WD', 'WS']]
        dfs.append(df)
    df_final = pd.concat(dfs, ignore_index=True)
    df_final.to_csv("kcic_forecast.csv", sep=";", index=False)
    return df_final

def merge_presentwx():
    dfs = []
    for province in ['jakarta', 'jawabarat']:
        fname = download_presentwx(province)
        df = pd.read_csv(fname, sep=";",
                         names=["AREA_ID", "DATE", "TMIN", "TMAX", "HUMIN", "HUMAX", "HU", "T", "WEATHER", "WD", "WS"])
        dfs.append(df)
    df_ndf = pd.concat(dfs, ignore_index=True)
    df_sta = pd.read_csv("src/track_ndf.csv")

    dfs = []
    for id, name, lon, lat in zip(df_sta['id'], df_sta['name'], df_sta['lon'], df_sta['lat']):
        df = df_ndf.loc[df_ndf['AREA_ID'] == id]
        df["NAME"] = name
        df["LON"] = lon
        df["LAT"] = lat
        df = df[['NAME', 'LON', 'LAT', 'DATE', 'TMIN', 'TMAX', 'HUMIN', 'HUMAX', 'HU', 'T', 'WEATHER', 'WD', 'WS']]
        dfs.append(df)
    df_final = pd.concat(dfs, ignore_index=True)
    df_final.to_csv("kcic_presentwx.csv", sep=";", index=False)
    return df_final


def load_forecast_data():
    df = pd.read_csv("kcic_forecast.csv", sep=";", parse_dates=["DATE"])
    return df

def load_presentwx_data():
    df = pd.read_csv("kcic_presentwx.csv", sep=";", parse_dates=["DATE"])
    return df

def get_nearest_forecast(df):
    holder = []
    dfg = df.groupby("NAME")
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
merge_ndf_kecamatan()
merge_presentwx()

df_pwx = load_presentwx_data()
df = load_forecast_data()
gdf_track = gpd.read_file('src/kcic.geojson')
df_sta = pd.read_csv("src/track_ndf.csv")

m = folium.Map(location=[-6.579044952293415, 107.33359554188215], zoom_start=10)
folium.GeoJson(gdf_track).add_to(m)
df_fct = get_nearest_forecast(df)

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
    df_all_fct = get_all_forecast(station_name, df)
    df_pwx = df_pwx.loc[df_pwx["NAME"] == station_name]
    df_all_fct = pd.concat([df_pwx, df_all_fct], ignore_index=True)
    df_all_fct = df_all_fct.sort_values(by=['DATE'])
    df_all_fct['DATE'] = df_all_fct["DATE"] + timedelta(hours=7)
    df_grp = df_all_fct.groupby(by=df_all_fct["DATE"].dt.date)
    tanggal_list = list(df_grp.groups.keys())
    tanggal_list_string = [x.strftime("%d %b | ") for x in tanggal_list]
    tabs = st.tabs(tanggal_list_string)

    for tab, tanggal in zip(tabs, tanggal_list):
        df_tgl = df_grp.get_group(tanggal)
        cols = tab.columns(df_tgl.shape[0])
        for col, (index, data) in zip(cols, df_tgl.iterrows()):
            markdown_content = f"""
                        <strong>{(data["DATE"]).strftime("%H:%M WIB")}</strong><br>
                        <img src="{wx_icon_dict[data['WEATHER']]}" alt="Weather Icon" style="width:50px;height:50px;"><br>
                        {wx_caption_dict[data["WEATHER"]]}<br>
                        Suhu: {data['T']} °C<br>
                        Kelembapan: {data['HU']} %<br>
                        Angin: {wind_caption_dict[data['WD']]} \n{data['WS']}<br>
                    """
            col.markdown(markdown_content, unsafe_allow_html=True)
else:
    st.write("## Click on a station to see its detailed forecast")
