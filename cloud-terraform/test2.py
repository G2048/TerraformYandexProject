import json
import grpc
import yandexcloud

from yandex.cloud.resourcemanager.v1.cloud_service_pb2 import ListCloudsRequest, ListCloudsResponse
from yandex.cloud.resourcemanager.v1.cloud_service_pb2_grpc import CloudServiceStub


def handler():
    interceptor = yandexcloud.RetryInterceptor(max_retry_count=5, retriable_codes=[grpc.StatusCode.UNAVAILABLE])

    sa_json_path = '..\\authorized_key.json'
    with open(sa_json_path) as infile:
        sdk = yandexcloud.SDK(service_account_key=json.load(infile))

    cloud_service = sdk.client(CloudServiceStub)
    clouds = {}
    # for c in cloud_service.List(ListCloudsRequest()).clouds:
        # clouds[c.id] = c.name
    # clouds = cloud_service.List(ListCloudsRequest()).clouds
    clouds = cloud_service.List(ListCloudsRequest()).clouds
    # clouds = cloud_service.List(ListCloudsResponse()).clouds
    return clouds

print(handler())