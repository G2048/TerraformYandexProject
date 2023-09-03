#!/usr/bin/env python3
import os
import json
import argparse
import logging.config

import grpc
import yandexcloud

from yandex.cloud.compute.v1.image_service_pb2 import GetImageLatestByFamilyRequest
from yandex.cloud.compute.v1.image_service_pb2_grpc import ImageServiceStub
from yandex.cloud.compute.v1.instance_pb2 import IPV4, Instance
from yandex.cloud.compute.v1.instance_service_pb2 import (
    CreateInstanceRequest,
    ResourcesSpec,
    AttachedDiskSpec,
    NetworkInterfaceSpec,
    PrimaryAddressSpec,
    OneToOneNatSpec,
    DeleteInstanceRequest,
    StopInstanceRequest,
    StartInstanceRequest,
    CreateInstanceMetadata,
    DeleteInstanceMetadata,
)
from yandex.cloud.resourcemanager.v1.cloud_service_pb2 import ListCloudsRequest
from yandex.cloud.compute.v1.instance_service_pb2_grpc import InstanceServiceStub
from dotenv import load_dotenv
from settings import LogConfig


load_dotenv()
env = os.getenv
YC_TOKEN = env('YC_TOKEN')
YC_CLOUD_ID = env('YC_CLOUD_ID')
YC_FOLDER_ID = env('YC_FOLDER_ID')
SSH_KEY = env('SSH_KEY')

logging.config.dictConfig(LogConfig)
logger = logging.getLogger('consolemode')


def collect_metadata():
    with open('metadata_instances\\vm_user_metadata', 'r') as file:
        file_content = file.readlines()

    file_content = ''.join(file_content)
    logging.debug(file_content)
    return file_content


def create_instance(sdk, folder_id, zone, name, subnet_id):
    image_service = sdk.client(ImageServiceStub)
    logger.info(f'{dir(GetImageLatestByFamilyRequest)}')

    source_image = image_service.GetLatestByFamily(
        GetImageLatestByFamilyRequest(
            folder_id='standard-images',
            family='ubuntu-2004-lts',
            # disk_id = 'fd83gfh90hpp3sojs1r3',
        )
    )

    subnet_id = subnet_id or sdk.helpers.get_subnet(folder_id, zone)
    instance_service = sdk.client(InstanceServiceStub)
    operation = instance_service.Create(CreateInstanceRequest(
        folder_id=folder_id,
        name=name,
        resources_spec=ResourcesSpec(
            memory=2 * 2 ** 30,     # 2Gb
            cores=2,
            core_fraction=50,
        ),
        
        zone_id=zone,
        platform_id='standard-v1',
        boot_disk_spec=AttachedDiskSpec(
            auto_delete=True,
            disk_spec=AttachedDiskSpec.DiskSpec(
                type_id='network-hdd',
                size=20 * 2 ** 30,      # 2GB
                image_id=source_image.id,
            )
        ),

        network_interface_specs=[
            NetworkInterfaceSpec(
                subnet_id=subnet_id,
                primary_v4_address_spec=PrimaryAddressSpec(
                    one_to_one_nat_spec=OneToOneNatSpec(
                        ip_version=IPV4,
                    )
                )
            ),
        ],
        metadata={
            'serial-port-enable': '1',
            'metadata-key': SSH_KEY,
            'metadata-value' : '',
            'user-data': collect_metadata(),
        },
    ))

    logger.info('Creating initiated')
    return operation


def delete_instance(sdk, instance_id):
    instance_service = sdk.client(InstanceServiceStub)
    return instance_service.Delete(DeleteInstanceRequest(instance_id=instance_id))

def stop_instance(sdk, instance_id):
    instance_service = sdk.client(InstanceServiceStub)
    return instance_service.Stop(StopInstanceRequest(instance_id=instance_id))

def start_instance(sdk, instance_id):
    instance_service = sdk.client(InstanceServiceStub)
    return instance_service.Start(StartInstanceRequest(instance_id=instance_id))

def list_instance(sdk, folder_id):
    instance_service = sdk.client(InstanceServiceStub)
    return instance_service.List(ListCloudsRequest(organization_id=folder_id))


def main(arguments):
    interceptor = yandexcloud.RetryInterceptor(max_retry_count=5, retriable_codes=[grpc.StatusCode.UNAVAILABLE])

    if arguments.token:
        sdk = yandexcloud.SDK(interceptor=interceptor, token=arguments.token)
    else:
        with open(arguments.sa_json_path) as infile:
            sdk = yandexcloud.SDK(interceptor=interceptor, service_account_key=json.load(infile))


    fill_missing_arguments(sdk, arguments)
    logger.info(f'{dir(sdk.helpers)}')


    if arguments.delete:
        instance_id = arguments.instance_id
        logger.info(f'Try to delete instance {instance_id}')
        operation = delete_instance(sdk, instance_id)
        sdk.wait_operation_and_get_result(
            operation,
            meta_type=DeleteInstanceMetadata,
        )
        logger.info(f'Deleted instance {instance_id}')
        return 0

    if arguments.stop:
        instance_id = arguments.instance_id
        logger.info(f'Try to stop instance {instance_id}')
        operation = stop_instance(sdk, instance_id)
        sdk.wait_operation_and_get_result(
            operation
        )
        logger.info(f'Stop instance {instance_id}')
        return 0

    if arguments.start:
        instance_id = arguments.instance_id
        logger.info(f'Try to start instance {instance_id}')
        operation = start_instance(sdk, instance_id)
        sdk.wait_operation_and_get_result(
            operation
        )
        logger.info(f'Start instance {instance_id}')
        return 0

    if arguments.list_instances:
        logger.info(f'Folder id: {arguments.folder_id=}')
        operation = list_instance(sdk, arguments.folder_id)
        responce = sdk.wait_operation_and_get_result(operation)
        logger.info(f'List instances {responce=}')
        return 0


    instance_id = None
    try:
        operation = create_instance(sdk, arguments.folder_id, arguments.zone, arguments.name, arguments.subnet_id)
        operation_result = sdk.wait_operation_and_get_result(
            operation,
            response_type=Instance,
            meta_type=CreateInstanceMetadata,
        )

        instance_id = operation_result.response.id
        logger.info(f'{instance_id=}')

    except Exception as e:
        logger.error(e)


def fill_missing_arguments(sdk, arguments):
    if not arguments.subnet_id:
        network_id = sdk.helpers.find_network_id(folder_id=arguments.folder_id)

        arguments.subnet_id = sdk.helpers.find_subnet_id(
            folder_id=arguments.folder_id,
            zone_id=arguments.zone,
            network_id=network_id,
        )


def parse_args():
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawTextHelpFormatter)

    auth = parser.add_mutually_exclusive_group(required=True)
    auth.add_argument(
        '--sa-json-path', '-js',
        help='Path to the service account key JSON file.\nThis file can be created using YC CLI:\n'
             'yc iam key create --output sa.json --service-account-id <id>',
    )
    auth.add_argument('--token', help='OAuth token')
    parser.add_argument('--folder-id', '-f', default=YC_FOLDER_ID, type=str, help='Your Yandex.Cloud folder id')
    parser.add_argument('--zone', default='ru-central1-a', help='Compute Engine zone to deploy to.')
    parser.add_argument('--name', default='demo-instance', help='New instance name.')
    parser.add_argument('--subnet-id', help='Subnet of the instance')
    parser.add_argument('--delete', '-d', action='store_true', default=False, help='Delete instance')
    parser.add_argument('--stop', '-s', action='store_true', default=False, help='Stop instance')
    parser.add_argument('--start', '-st', action='store_true', default=False, help='Start instance')
    parser.add_argument('--instance-id', '-id', help='Specify instance')
    parser.add_argument('--list-instances', '-l', action='store_true', default=False, help='List instances')

    return parser.parse_args()


if __name__ == '__main__':
    arguments = parse_args()
    logger.debug(f'{arguments=}')
    
    main(arguments)