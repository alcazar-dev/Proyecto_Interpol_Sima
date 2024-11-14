import pandas as pd
import geopandas as gpd
import contextily as ctx
import matplotlib.pyplot as plt
import numpy as np
from scipy.interpolate import griddata
from pyproj import Transformer
import io
import base64

def process_interpolation_viento(fecha, hora, contaminante='PM10'):
    # Cargar datos
    import os
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    df_Completo_Imputado = pd.read_csv(os.path.join(BASE_DIR, 'data', 'df_interpolar.csv'))
    df_UBI = pd.read_csv(os.path.join(BASE_DIR, 'data', 'UBI.csv'))



    # Filtrar los datos por fecha y hora
    df_filtrado = df_Completo_Imputado[
        (df_Completo_Imputado['date'].astype(str) == fecha) & 
        (df_Completo_Imputado['time'].astype(str) == hora)
    ]

    # Agrupar por zona y calcular promedios
    coords_zonas = df_filtrado.groupby('zona_encoded').agg({
        'latitud': 'mean',
        'longitud': 'mean',
        contaminante: 'mean',
        'WSR': 'mean',
        'WDR': 'mean'
    }).reset_index()

    # Crear GeoDataFrame para graficar las zonas
    gdf_zonas = gpd.GeoDataFrame(
        coords_zonas,
        geometry=gpd.points_from_xy(coords_zonas['longitud'], coords_zonas['latitud']),
        crs="EPSG:4326"
    ).to_crs(epsg=3857)

    # Crear malla para interpolación
    lon_grid, lat_grid = np.mgrid[
        coords_zonas['longitud'].min():coords_zonas['longitud'].max():100j,
        coords_zonas['latitud'].min():coords_zonas['latitud'].max():100j
    ]

    # Interpolación de los valores del contaminante
    interpolated_values = griddata(
        (coords_zonas['longitud'], coords_zonas['latitud']),
        coords_zonas[contaminante],
        (lon_grid, lat_grid),
        method='cubic'
    )

    # Ajustar la interpolación por velocidad del viento
    interpolated_values_adjusted = interpolated_values * (1 + coords_zonas['WSR'].mean() / max(coords_zonas['WSR']))

    # Proyección de la malla a EPSG:3857
    transformer = Transformer.from_crs("epsg:4326", "epsg:3857", always_xy=True)
    lon_grid_proj, lat_grid_proj = transformer.transform(lon_grid, lat_grid)

    # Crear el gráfico
    fig, ax = plt.subplots(figsize=(10, 8))
    gdf_zonas.plot(ax=ax, color='black', markersize=100, label='Estaciones')
    ctx.add_basemap(ax, crs=gdf_zonas.crs, source=ctx.providers.OpenStreetMap.Mapnik)
    contour = ax.contourf(lon_grid_proj, lat_grid_proj, interpolated_values_adjusted, cmap='coolwarm', alpha=0.6)
    fig.colorbar(contour, ax=ax, label=f'Concentración {contaminante} ajustada')
    plt.title(f'Distribución de {contaminante} ajustada por viento en {fecha} {hora}', fontsize=15)
    plt.legend()

    # Guardar imagen en base64
    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    image_base64 = base64.b64encode(buf.read()).decode('utf-8')
    buf.close()
    plt.close(fig)
    
    return image_base64
