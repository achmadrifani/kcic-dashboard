import xarray as xr
import geopandas as gpd
import pickle

with open(f"src/gdf_track.pkl","rb") as file:
    gdf_tr = pickle.load(file)
gdf_tr

fsteps = [3,6,9]
for step in fsteps:
    ds = xr.open_dataset(f"sample_data/PWRFULL.INDX0100.20231230000000.U.ALL_LEVELS.{step}.grib",engine="cfgrib",backend_kwargs={"filter_by_keys": {'typeOfLevel': 'heightAboveGround'}})
    v10 = ds["v10"].sel(latitude=slice(-8,-5),longitude=slice(105,108))
    u10 = ds["u10"].sel(latitude=slice(-8,-5),longitude=slice(105,108))
    speed = (v10**2 + u10**2)**0.5
    speed_at_height = speed * ((30/10)**0.5)
    speed_holder = []
    for point in gdf_tr["middle_point"]:
        lon = point[0]
        lat = point[1]
        speed_holder.append(speed_at_height.interp(latitude=lat,longitude=lon,method="nearest").values.tolist())
    gdf_tr[str(step)] = speed_holder
with open(f"wind_forecast.pkl","wb") as file:
        pickle.dump(gdf_tr,file)