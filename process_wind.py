import pandas as pd
import geopandas as gpd
import contextily as ctx
import matplotlib
matplotlib.use('Agg')

import matplotlib.pyplot as plt
import numpy as np
from scipy.interpolate import griddata
from pyproj import Transformer
import io
import base64
import imageio
import os
import requests

def download_csv_from_drive(url):
    response = requests.get(url)
    response.raise_for_status()  # Verifica si hubo un error en la descarga
    data = response.content.decode('utf-8')
    return pd.read_csv(io.StringIO(data))


def process_interpolation(fecha, hora, contaminante='PM10'):
    try:
        # ------ ------ Local ----- ----- #

        # Cargar datos
        #df_Completo_Imputado = pd.read_csv('./data/df_interpolar.csv')
        #df_UBI = pd.read_csv('./data/UBI.csv')

        # ------ ------ Local ----- ----- #

        # ------ ------ Desde Drive ----- ----- #
        
        url_df_imputado = 'https://drive.google.com/uc?id=1WrC7WLRqBxihLafJap5BaM5p1mn8lTXZ'
        url_df_UBI = 'https://drive.google.com/uc?id=1_klxFhSMpv_d4GDP3qFtX03RRH9QWk_W'


        df_Completo_Imputado = download_csv_from_drive(url_df_imputado)
        df_UBI = download_csv_from_drive(url_df_UBI)

        # ------ ------ Desde Drive ----- ----- #

        # Asegurarse de que las columnas de fecha y hora estén bien formateadas
        hora = f"{hora}:00"  # Asegura que la hora coincida con el formato del CSV


        # Filtrar los datos por fecha y hora
        df_filtrado = df_Completo_Imputado[
            (df_Completo_Imputado['date'].astype(str) == fecha) &
            (df_Completo_Imputado['time'].astype(str) == hora)
        ]


        if df_filtrado.empty:
            return {"error": "No hay datos para la fecha y hora especificadas"}


        # Agrupar por zona y calcular promedios
        coords_zonas = df_filtrado.groupby('zona_encoded').agg({
            'latitud': 'mean',
            'longitud': 'mean',
            contaminante: 'mean',
            'WSR': 'mean',
            'WDR': 'mean'
        }).reset_index()


        if coords_zonas[contaminante].isnull().all():
            return {"error": f"No hay datos válidos para el contaminante {contaminante}."}


        # Crear GeoDataFrame
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


        # Realizar la interpolación
        interpolated_values = griddata(
            (coords_zonas['longitud'], coords_zonas['latitud']),
            coords_zonas[contaminante],
            (lon_grid, lat_grid),
            method='cubic'
        )


        # Ajustar la interpolación por velocidad del viento
        interpolated_values_adjusted = interpolated_values * (
            1 + coords_zonas['WSR'].mean() / max(coords_zonas['WSR'])
        )


        # Proyección de la malla
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


        return {"image_base64": image_base64}


    except Exception as e:
        return {"error": str(e)}

import os
import imageio
import base64

import glob

def generate_daily_gif(fecha, contaminante='PM10'):
    # Crear una carpeta temporal para guardar las imágenes
    temp_folder = './temp_images'
    os.makedirs(temp_folder, exist_ok=True)
    images = []
    error = None
    gif_path = f"./static/mapas/{fecha}_{contaminante}.gif"  # Definir gif_path

    # Eliminar GIFs antiguos con la misma fecha o contaminante
    existing_gifs = glob.glob(f"./static/mapas/{fecha}_*.gif")
    for gif in existing_gifs:
        try:
            os.remove(gif)
        except OSError as e:
            print(f"Error al intentar eliminar {gif}: {e}")

    try:
        # Generar una imagen por cada hora del día
        for hour in range(24):
            hora = f"{hour:02d}:00"
            result = process_interpolation(fecha, hora, contaminante)

            if "error" in result:
                error = result["error"]
                break

            # Decodificar la imagen base64 y guardarla como archivo PNG temporal
            image_data = base64.b64decode(result["image_base64"])
            image_path = os.path.join(temp_folder, f"map_{hour:02d}.png")
            with open(image_path, 'wb') as img_file:
                img_file.write(image_data)
            images.append(image_path)  # Guardar la ruta del archivo en lugar de la imagen leída

        # Generar el GIF si no hubo errores
        if not error and images:
            # Cargar las imágenes desde las rutas almacenadas y crear el GIF
            img_data = [imageio.imread(img_path) for img_path in images]
            imageio.mimsave(gif_path, img_data, fps=5, loop=0)  # Duración aumentada y bucle infinito

    except Exception as e:
        error = str(e)

    finally:
        # Limpiar imágenes temporales
        for img_path in images:
            os.remove(img_path)

        # Remover la carpeta temporal
        os.rmdir(temp_folder)

    # Retornar la ruta del GIF o el error
    return gif_path if not error else None, error
