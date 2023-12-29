import os
import requests
from ftplib import FTP
import pandas as pd

NDF_FOLDER = "src/ndf"

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

def send_ftp(host,username,password,local_file,remote_file):
    ftp = FTP(host)
    ftp.login(user=username, passwd=password)
    with open(local_file, 'rb') as file:
        ftp.storbinary("STOR " + remote_file, file)
    ftp.close()

def main():
    df_sta = pd.read_csv("src/track_ndf.csv")
    df_holder = []
    for province in ['jakarta', 'jawabarat']:
        fname = download_presentwx(province)
        df = pd.read_csv(fname, sep=";",
                         names=["AREA_ID", "DATE", "TMIN", "TMAX", "HUMIN", "HUMAX", "HU", "T", "WEATHER", "WD", "WS"])
        df_holder.append(df)
    df_pwx = pd.concat(df_holder, ignore_index=True)

    dfs = []
    for id, name, lon, lat in zip(df_sta['id'], df_sta['name'], df_sta['lon'], df_sta['lat']):
        df = df_pwx.loc[df_pwx['AREA_ID'] == id]
        df["NAME"] = name
        df["LON"] = lon
        df["LAT"] = lat
        df = df[['NAME', 'LON', 'LAT', 'DATE', 'TMIN', 'TMAX', 'HUMIN', 'HUMAX', 'HU', 'T', 'WEATHER', 'WD', 'WS']]
        dfs.append(df)
    df_final = pd.concat(dfs, ignore_index=True)
    df_final['DATE'] = df_final['DATE'].astype('datetime64[ns]')
    df_final.to_csv(f"{NDF_FOLDER}/kcic_presentwx.csv", sep=";", index=False)

    send_ftp("publik.bmkg.go.id","amandemen","bmkg2303",
             f"{NDF_FOLDER}/kcic_presentwx.csv", "data/kcic/kcic_presentwx.csv")

if __name__ == "__main__":
    main()
