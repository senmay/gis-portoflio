import boto3
import os
import json
from rio_cogeo.cogeo import cog_translate
from rio_cogeo.profiles import cog_profiles
from rasterio.enums import Resampling
import rasterio
from rasterio.warp import transform_bounds
import numpy as np
import requests

METADATA_FILE = os.path.join('orto_ref_host')

def convert_data_to_cog(input_path, output_path):
    with rasterio.open(input_path) as src:
        count = src.count
        profile = src.profile.copy()

        if count == 1:
            photometric = "minisblack"
        elif count == 3:
            photometric = "ycbcr"
        else:
            raise ValueError(f"Nieobsługiwana liczba kanałów ({count}). Oczekiwano 1 (grayscale) lub 3 (RGB).")

        profile.update({
            "driver": "GTiff",
            "dtype": "uint8",
            "nodata": None,
            "count": count,
            "compress": "jpeg",
            "photometric": photometric,
            "tiled": True,
            "blockxsize": 512,
            "blockysize": 512,
            "interleave": "pixel"
        })

        with rasterio.open(output_path, 'w', **profile) as dst:
            for i in range(1, count + 1):
                band = src.read(i, resampling=Resampling.nearest).astype("float32")
                band_min = band.min()
                band_max = band.max()

                if band_max - band_min == 0:
                    scaled = np.zeros_like(band, dtype="uint8")
                else:
                    scaled = ((band - band_min) / (band_max - band_min) * 255).astype("uint8")

                dst.write(scaled, i)

    print(f"✅ JPEG raster zapisany: {output_path}")
    return output_path

def get_presigned_post(bucket_name, object_name, expiration=3600):
    s3_client = boto3.client(
        's3',
        region_name=os.environ.get('AWS_REGION'),
        aws_access_key_id=os.environ.get('AWS_ACCESS_KEY_ID'),
        aws_secret_access_key=os.environ.get('AWS_SECRET_ACCESS_KEY')
    )

    response = s3_client.generate_presigned_post(
        Bucket=bucket_name,
        Key=object_name,
        ExpiresIn=expiration
    )
    return response

def upload_cog_to_s3(file_storage):
    bucket_name = os.environ.get('AWS_BUCKET_NAME')
    object_name = 'cog/' + file_storage.filename
    
    # Save the uploaded file to a temporary location
    temp_path = os.path.join('orto_ref_host', file_storage.filename)
    file_storage.save(temp_path)

    presigned_url = get_presigned_post(bucket_name, object_name)
    with open(temp_path, 'rb') as f:
        files = {'file': f}
        r = requests.post(presigned_url['url'], data=presigned_url['fields'], files=files)
    
    # Clean up the temporary file
    os.remove(temp_path)
    
    return r.status_code

def list_cogs_in_bucket():
    s3_client = boto3.client(
        's3',
        region_name=os.environ.get('AWS_REGION'),
        aws_access_key_id=os.environ.get('AWS_ACCESS_KEY_ID'),
        aws_secret_access_key=os.environ.get('AWS_SECRET_ACCESS_KEY')
    )
    bucket_name = os.environ.get('AWS_BUCKET_NAME')
    cogs = []
    metadata = _read_metadata() # Load all metadata once
    try:
        response = s3_client.list_objects_v2(Bucket=bucket_name, Prefix='cog/')
        if 'Contents' in response:
            for obj in response['Contents']:
                filename = os.path.basename(obj['Key'])
                cog_url = f"https://{bucket_name}.s3.{os.environ.get('AWS_REGION')}.amazonaws.com/{obj['Key']}"
                bbox = metadata.get(filename, {}).get('bbox_epsg3857')
                print(f"DEBUG: In list_cogs_in_bucket - Filename: {filename}, Bbox from metadata: {bbox}")
                cogs.append({'url': cog_url, 'bbox': bbox})
    except Exception as e:
        print(f"Error listing files in S3: {e}")
    return cogs

def get_cog_bbox(filename):
    metadata = _read_metadata()
    return metadata.get(filename, {}).get('bbox_epsg3857')

def requires_byte_conversion(path):
    with rasterio.open(path) as src:
        dtype = src.dtypes[0]
        return dtype != "uint8"

