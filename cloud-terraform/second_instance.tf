resource "yandex_compute_instance" "vm-2" {
    name = "test-vm2"

    resources {
        cores  = 2
        memory = 2
    }

    boot_disk {
        initialize_params {
            image_id = "fd83gfh90hpp3sojs1r3"
        }
    }

    network_interface {
        subnet_id = yandex_vpc_subnet.subnet-1.id
        nat       = true
    }

    metadata = {
        serial-port-enable = 1
        #ssh-keys = file("id_rsa.pub")
        user-data = file("metadata_instances\\vm_user_metadata")
    }
}



output "internal_ip_address_vm_2" {
    value = yandex_compute_instance.vm-2.network_interface.0.ip_address
}

output "external_ip_address_vm_2" {
    value = yandex_compute_instance.vm-2.network_interface.0.nat_ip_address
}

resource "yandex_dns_recordset" "rs2" {
    zone_id = yandex_dns_zone.zone1.id
    name    = "test-vm2"
    type    = "A"
    ttl     = 200
    data    = [yandex_compute_instance.vm-2.network_interface.0.nat_ip_address]
    #data    = [external_ip_address_vm_2.value]
    #data    = ["10.1.0.1"]
}