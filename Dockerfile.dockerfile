# Usa una imagen de Python
FROM python:3.8-slim

# Instala dependencias de sistema para matplotlib y geopandas
RUN apt-get update && \
    apt-get install -y \
    gcc \
    g++ \
    libproj-dev \
    proj-data \
    proj-bin \
    libgeos-dev \
    python3-dev \
    python3-pip \
    libgdal-dev

# Establece el directorio de trabajo
WORKDIR /app

# Copia los archivos de requisitos y los instala
COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt

# Copia el resto de los archivos de la aplicación al contenedor
COPY . .

# Exponer el puerto
EXPOSE 5000

# Ejecuta la aplicación
CMD ["python", "app.py"]
