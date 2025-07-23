import boto3
import requests

OBJECT_NAME_TO_UPLOAD = 'RT_L1C_T33UVT_A039373_20240919T101018_B04.tif'

s3_client = boto3.client(
    's3',
   region_name='eu-central-1',

)

# Generate the presigned URL for uploading the file
LocalPath = 'orto_ref_host/' + OBJECT_NAME_TO_UPLOAD
ObjectName = OBJECT_NAME_TO_UPLOAD
response = s3_client.generate_presigned_post(
    Bucket = 'viewwms',
    Key = 'cog/' + ObjectName,
    ExpiresIn = 3600,  # URL will be valid for 1 hour
)
print (f"Presigned URL for uploading {OBJECT_NAME_TO_UPLOAD}: {response}")

#Upload the file to S3 using the presigne1d URL
files = {'file': open(LocalPath, 'rb')}
r = requests.post(response['url'], data=response['fields'], files=files)
print(r.status_code)
print(r.text)