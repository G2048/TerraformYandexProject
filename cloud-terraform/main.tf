terraform {
    required_providers {
        yandex = {
        source = "yandex-cloud/yandex"
        }
    }
    required_version = ">= 0.13"
}

provider "yandex" {
    zone = "ru-central1-a"
}


resource "yandex_vpc_network" "network-1" {
    name = "network1"
}

resource "yandex_vpc_subnet" "subnet-1" {
    name           = "subnet1"
    zone           = "ru-central1-a"
    network_id     = yandex_vpc_network.network-1.id
    v4_cidr_blocks = ["192.168.10.0/24"]
}

resource "yandex_dns_zone" "zone1" {
    name        = "dns-private-zone"
    description = "Test private zone"

    labels = {
        label1 = "test-private"
    }

    public           = true
    zone    = "test.example-public1342.com."
    #private_networks = [yandex_vpc_network.network-1.id]
}