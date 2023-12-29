from azure.storage.blob import BlobServiceClient, BlobClient
import io


def get_application_number_container_details():
    connection_string = 'DefaultEndpointsProtocol=https;AccountName=trademarksearch;AccountKey=19VEc9V7KvqRaokeeqf/mvtt092P8WJXx6Lj5t0zIbu2Uq7ZJErz9cVPRS29kGFUR6fkmVyzNKx5+AStkcYX9w==;EndpointSuffix=core.windows.net'
    container_name = 'application-numbers-for-tm-suite'
    return connection_string, container_name


def list_application_number_blobs():
    connection_string, container_name = get_application_number_container_details()
    blob_service_client = BlobServiceClient.from_connection_string(connection_string)
    container_client = blob_service_client.get_container_client(container_name)
    blob_list = container_client.list_blob_names()
    blob_list = [item for item in blob_list]
    return blob_list


def download_app_num_blob_to_stream(blob_name):
    connection_string, container_name = get_application_number_container_details()
    blob = BlobClient.from_connection_string(connection_string, container_name=container_name, blob_name=blob_name)
    # readinto() downloads the blob contents to a stream and returns the number of bytes read
    stream = io.BytesIO()
    num_bytes = blob.download_blob().readinto(stream)
    return stream
