import warnings
from datetime import datetime
from ftplib import FTP

import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio
import requests
import rioxarray as rxr
from shapely.geometry import Point

warnings.filterwarnings("ignore")


def get_latest_steps():
    """Mengambil data steps terkini"""

    apiAmandemen = 'https://radar.bmkg.go.id:8060'
    token = '19387e71e78522ae4172ec0fda640983b8438c9cfa0ca571623cb69d8327'
    propinsi = 'Jabodetabek'
    radar = 'JAK'
    product = 'STEPS'
    ptype = 'latest'
    urlAPIRadarGeotif = f'{apiAmandemen}/getRadarGeotif?token={token}&radar={radar}&product={product}&type={ptype}'
    responseAPIRadarGeotif = requests.get(urlAPIRadarGeotif, verify=False).json()

    data_holder = []
    valid_holder = []
    for file in responseAPIRadarGeotif['file']:
        # Parsing nama file untuk mendapatkan nilai "base_time" dan "valid_time"
        start_base_time = file.find('Base') + len('Base')
        end_base_time = file.find('_', start_base_time)
        base_time = datetime.strptime(file[start_base_time:end_base_time], "%Y%m%d%H%M")

        start_valid_time = file.find('Valid') + len('Valid')
        end_valid_time = file.find('.', start_valid_time)
        valid_time = datetime.strptime(file[start_valid_time:end_valid_time], "%Y%m%d%H%M")

        with rasterio.open(file) as src:
            data_array = rxr.open_rasterio(src)
            data_array = data_array.where(~np.isnan(data_array), 0)
            data_array = data_array.sel(band=1)
        data_holder.append(data_array)
        valid_holder.append(valid_time)
    return data_holder, valid_holder

def calc_wx(cmax, lightning):
    conditions = [
        (np.logical_and(cmax >= 0, cmax <= 5) & (lightning != 0)),
        (np.logical_and(cmax >= 0, cmax <= 5) & (lightning == 0)),
        (np.logical_and(cmax > 5, cmax <= 20) & (lightning != 0)),
        (np.logical_and(cmax > 5, cmax <= 20) & (lightning == 0)),
        (np.logical_and(cmax > 20, cmax <= 35) & (lightning == 0)),
        (np.logical_and(cmax > 20, cmax <= 35) & (lightning != 0)),
        (np.logical_and(cmax > 35, cmax <= 45) & (lightning == 0)),
        (np.logical_and(cmax > 35, cmax <= 45) & (lightning != 0)),
        (cmax > 45) & (lightning == 0),
        (cmax > 45) & (lightning != 0)
    ]

    choices = [
        np.random.choice([0, 1, 2]),
        np.random.choice([0, 1, 2]),
        np.random.choice([3, 4]),
        np.random.choice([3, 4]),
        60,
        95,
        61,
        95,
        63,
        95
    ]

    wx = np.select(conditions, choices)
    return wx

def generate_wx_df(steps_file, steps_time, poi, radius):
    rdr_holder = []
    wx_holder = []

    for lon, lat in zip(poi["lon"], poi["lat"]):
        center_point = Point(lon, lat)
        rdr_gdf = gpd.GeoDataFrame({'id': ['center'], 'geometry': [center_point]})
        buffer_geometry = rdr_gdf.buffer(radius)
        clipped_data = steps_file.rio.clip(buffer_geometry)
        max_value = clipped_data.max()
        wx = calc_wx(int(max_value),int(0))
        rdr_holder.append(int(max_value))
        wx_holder.append(wx)

    poi['valid_time'] = steps_time
    poi['cmax'] = rdr_holder
    poi['weather'] = wx_holder
    return poi

def send_ftp(host,username,password,local_file,remote_file):
    ftp = FTP(host)
    ftp.login(user=username, passwd=password)
    with open(local_file, 'rb') as file:
        ftp.storbinary("STOR " + remote_file, file)
    ftp.close()


def main(points, steps_files, steps_times):
    # load points df
    poi = pd.read_csv(points, sep=",")

    ndf_header = ["AREA_ID", "DATE", "TMIN", "TMAX", "HUMIN", "HUMAX", "HU", "T", "WEATHER", "WD", "WS"]
    radius = 0.05

    # generate wx_df for STEPS
    df_final = pd.DataFrame()  # Initialize an empty DataFrame

    for steps_file, steps_time in zip(steps_files, steps_times):
        df_wx = generate_wx_df(steps_file, steps_time, poi, radius)

        # Concatenate new data to df_final
        df_final = pd.concat([df_final, df_wx], ignore_index=True)

    fname_local = f"kcic_steps.csv"
    fname_remote = f"kcic_steps.csv"

    # converting to NDF CSV Fomat
    df_final[['TMAX','TMIN', 'HUMAX', 'HUMIN', 'HU', 'T', 'WD','WS']] = None
    df_final.rename(columns={'name': 'NAME', 'lon': 'LON', 'lat': 'LAT', 'valid_time': 'DATE', 'weather':'WEATHER'}, inplace=True)
    df_final = df_final[['NAME', 'LON', 'LAT', 'DATE', 'TMIN', 'TMAX', 'HUMIN', 'HUMAX', 'HU', 'T', 'WEATHER', 'WD', 'WS']]

    df_final.to_csv(f"{OUT_FOLDER}/{fname_local}", sep=";", index=False)

    send_ftp("publik.bmkg.go.id", "amandemen", "bmkg2303",
             f"{OUT_FOLDER}/kcic_steps.csv", "data/kcic/kcic_steps.csv")


if __name__ == "__main__":
    steps_files, steps_times = get_latest_steps()
    points = "/home/metpublic/TASK_RELEASE/EFAN/kcic/src/track_ndf.csv"
    main(points, steps_files, steps_times)

