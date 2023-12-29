import os
import requests
from ftplib import FTP
import pandas as pd

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


def send_ftp(host,username,password,local_file,remote_file):
    ftp = FTP(host)
    ftp.login(user=username, passwd=password)
    with open(local_file, 'rb') as file:
        ftp.storbinary("STOR " + remote_file, file)
    ftp.close()


def main():
    df_sta = pd.read_csv("src/track_ndf.csv")

    ndf_holder = []
    for province in ['jakarta', 'jawabarat']:
        fname = download_ndf_kecamatan(province)
        df = pd.read_csv(fname, sep=";",
                         names=["AREA_ID", "DATE", "TMIN", "TMAX", "HUMIN", "HUMAX", "HU", "T", "WEATHER", "WD", "WS"])
        ndf_holder.append(df)
    df_ndf = pd.concat(ndf_holder, ignore_index=True)

    sub_holder = []
    for ids, name, lon, lat in zip(df_sta['id'], df_sta['name'], df_sta['lon'], df_sta['lat']):
        df = df_ndf.loc[df_ndf['AREA_ID'] == ids]
        df["NAME"] = name
        df["LON"] = lon
        df["LAT"] = lat
        df = df[['NAME', 'LON', 'LAT', 'DATE', 'TMIN', 'TMAX', 'HUMIN', 'HUMAX', 'HU', 'T', 'WEATHER', 'WD', 'WS']]
        sub_holder.append(df)
    df_final = pd.concat(sub_holder, ignore_index=True)
    df_final['DATE'] = df_final['DATE'].astype('datetime64[ns]')

    filename = "kcic_ndf.csv"
    df_final.to_csv(f"{NDF_FOLDER}/{filename}", sep=";", index=False)

    send_ftp("publik.bmkg.go.id", "amandemen", "bmkg2303",
             f"{NDF_FOLDER}/kcic_ndf.csv", "data/kcic/kcic_ndf.csv")

if __name__ == "__main__":
    main()