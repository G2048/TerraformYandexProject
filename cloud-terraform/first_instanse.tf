resource "yandex_compute_instance" "vm-1" {
    name = "test-vm1"

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
        ssh-keys = file("ssh-keys\\id_rsa.pub")
        user-data = file("metadata_instances\\vm_user_metadata")
        #dns_name    = "${yandex_dns_recordset.rs1.name}"
    }
}

output "internal_ip_address_vm_1" {
    value = yandex_compute_instance.vm-1.network_interface.0.ip_address
}

output "external_ip_address_vm_1" {
    value = yandex_compute_instance.vm-1.network_interface.0.nat_ip_address
}

# yc dns zone list-records <имя зоны DNS>
resource "yandex_dns_recordset" "rs1" {
    zone_id = yandex_dns_zone.zone1.id
    name    = "test-vm1"
    type    = "A"
    ttl     = 200
    #data    = [yandex_compute_instance.vm-1.network_interface.0.nat_ip_address]
    data    = [yandex_compute_instance.vm-1.network_interface.0.nat_ip_address]
}