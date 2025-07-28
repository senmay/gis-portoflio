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
from rasterio.warp import reproject, Resampling as WarpResampling, calculate_default_transform

METADATA_FILE = os.path.join('orto_ref_host')

def convert_data_to_cog(input_path, output_path):
    with rasterio.open(input_path) as src:
        count = src.count
        dst_crs = 'EPSG:3857'
        transform, width, height = get_reproject_params(src, dst_crs)

        if count == 1:
            photometric = "minisblack"
        elif count == 3:
            photometric = "ycbcr"
        else:
            raise ValueError(f"Nieobsługiwana liczba kanałów ({count}).")

        profile = build_output_profile(src, count, width, height, transform, dst_crs, photometric)

        with rasterio.open(output_path, 'w', **profile) as dst:
            for i in range(1, count + 1):
                band = src.read(i, resampling=Resampling.nearest).astype("float32")
                scaled = scale_to_uint8(band)
                reprojected = reproject_band(scaled, src, (height, width), transform, dst_crs)
                dst.write(reprojected, i)

    print(f"✅ JPEG+COG zapisany z CRS=EPSG:3857: {output_path}")
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
    original_filename = file_storage.filename

    # Define temporary paths
    temp_dir = 'orto_ref_host'
    input_path = os.path.join(temp_dir, f"input_{original_filename}")
    output_path = os.path.join(temp_dir, f"cog_{original_filename}")

    # Ensure the temporary directory exists
    os.makedirs(temp_dir, exist_ok=True)

    try:
        # 1. Save the uploaded file to a temporary input location
        file_storage.save(input_path)

        # 2. Convert the input file to a COG
        convert_data_to_cog(input_path, output_path)

        # 3. Prepare to upload the COG to S3
        # The object name in S3 should be the original filename
        object_name = 'cog/' + original_filename
        presigned_url = get_presigned_post(bucket_name, object_name)

        # 4. Upload the converted COG file
        with open(output_path, 'rb') as f:
            files = {'file': (original_filename, f)}
            response = requests.post(presigned_url['url'], data=presigned_url['fields'], files=files)
        
        return response.status_code

    finally:
        # 5. Clean up the temporary files
        if os.path.exists(input_path):
            os.remove(input_path)
        if os.path.exists(output_path):
            os.remove(output_path)

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
    
def scale_to_uint8(band: np.ndarray) -> np.ndarray:
    bmin, bmax = band.min(), band.max()
    if bmax - bmin == 0:
        return np.zeros_like(band, dtype="uint8")
    return ((band - bmin) / (bmax - bmin) * 255).astype("uint8")

def get_reproject_params(src, dst_crs='EPSG:3857'):
    if src.crs == dst_crs:
        return src.transform, src.width, src.height
    return calculate_default_transform(
        src.crs, dst_crs, src.width, src.height, *src.bounds)

def reproject_band(scaled_band, src, dst_shape, dst_transform, dst_crs):
    dest = np.zeros(dst_shape, dtype="uint8")
    reproject(
        source=scaled_band,
        destination=dest,
        src_transform=src.transform,
        src_crs=src.crs,
        dst_transform=dst_transform,
        dst_crs=dst_crs,
        resampling=WarpResampling.nearest
    )
    return dest

def build_output_profile(src, count, width, height, transform, dst_crs, photometric):
    profile = src.profile.copy()
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
        "interleave": "pixel",
        "crs": dst_crs,
        "transform": transform,
        "width": width,
        "height": height
    })
    return profile

