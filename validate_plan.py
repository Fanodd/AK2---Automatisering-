"""Kontroller YAML, subnett, porter og DHCP uten fysisk nettverksutstyr."""
import ipaddress
from pathlib import Path
import sys

import yaml

ROOT = Path(__file__).resolve().parents[1]
PART2 = ROOT / "part2"


def require(condition, message):
    if not condition:
        raise ValueError(message)


def load(path):
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def validate():
    yaml_files = list(PART2.rglob("*.yml"))
    for path in yaml_files:
        load(path)
    common = load(PART2 / "group_vars/all.yml")
    router_names = ("STUD2-R1", "STUD2-R2")
    routers = {name: load(PART2 / f"host_vars/{name}.yml") for name in router_names}
    management = [ipaddress.ip_network(f"{common[side + '_management_network']}/{common[side + '_management_mask']}")
                  for side in ("upper", "lower")]
    require(not management[0].overlaps(management[1]), "Administrasjonsnettene overlapper")
    networks = []
    ids = []
    for vlan in common["client_vlans"]:
        ids.append(vlan["id"])
        network = ipaddress.ip_network(f"{vlan['network']}/{vlan['prefix']}")
        require(network.version == 4 and network.num_addresses <= 65536,
                "Valideringen forventer IPv4-subnett med minst /16-prefiks")
        require(1 < vlan["id"] <= 4094, "Klient-VLAN maa vaere 2 til 4094")
        require(str(network.netmask) == vlan["mask"], f"Ulik maske og prefiks for VLAN {vlan['id']}")
        require(not any(network.overlaps(other) for other in management + networks),
                f"Overlappende subnett for VLAN {vlan['id']}")
        networks.append(network)
        gateway = ipaddress.ip_address(vlan["gateway"])
        reserved = {gateway}
        addresses = []
        for name in router_names:
            address = ipaddress.ip_address(vlan["router_addresses"][name])
            require(address in network and address not in (network.network_address, network.broadcast_address),
                    f"Ugyldig ruteradresse for {name}, VLAN {vlan['id']}")
            addresses.append(address)
            reserved.add(address)
        require(len(set(addresses)) == len(addresses), "Rutere har samme adresse")
        require(gateway in network and gateway not in (network.network_address, network.broadcast_address),
                "Gateway utenfor brukbart subnett")
        allocated = []
        for name in router_names:
            interval = vlan["dhcp_ranges"][name]
            start, end = map(ipaddress.ip_address, (interval["start"], interval["end"]))
            require(start in network and end in network and start <= end, "Ugyldig DHCP-intervall")
            allowed = set(network.hosts())
            for excluded in routers[name]["dhcp_exclusions"]:
                lo, hi = map(ipaddress.ip_address, (excluded["start"], excluded["end"]))
                require(lo <= hi, "Ugyldig eksklusjon")
                if lo in network or hi in network:
                    require(lo in network and hi in network, "Eksklusjon krysser subnett")
                    allowed -= {ipaddress.ip_address(value) for value in range(int(lo), int(hi) + 1)}
            expected = {ipaddress.ip_address(value) for value in range(int(start), int(end) + 1)}
            require(allowed == expected, f"Eksklusjoner gir feil DHCP-intervall paa {name}, VLAN {vlan['id']}")
            require(not allowed & reserved, "DHCP deler ut en gateway/ruteradresse")
            require(not any(allowed & previous for previous in allocated), "DHCP-intervaller overlapper")
            allocated.append(allowed)
    require(len(set(ids)) == len(ids), "Duplikate VLAN")
    internal_allowed = set(map(int, common["lower_trunk_allowed_vlans"].split(",")))
    require(common["native_management_vlan"] == 1, "Dette oppsettet bruker VLAN 1 til untagget administrasjon")
    require(internal_allowed == {1, *ids}, "Intern trunk maa foere administrasjons-VLAN og alle klient-VLAN")
    for name in ("STUD2-SW2", "STUD2-SW3"):
        host = load(PART2 / f"host_vars/{name}.yml")
        ports = [item["interface"] for item in host["trunk_ports"] + host["client_ports"]]
        if name == "STUD2-SW3":
            ports += host["etherchannel_members"]
            allowed_ids = set(map(int, host["etherchannel_allowed_vlans"].split(",")))
            require(allowed_ids == set(ids), "EtherChannel maa dele klient-VLAN og utelate VLAN 1")
            require(host["etherchannel_native_vlan"] == common["native_management_vlan"],
                    "Ulik native VLAN paa intern trunk og EtherChannel")
        require(len(ports) == len(set(ports)), f"Port brukt flere ganger paa {name}")
        require(all(item["vlan"] in ids for item in host["client_ports"]), "Ukjent klient-VLAN")
    inventory = load(PART2 / "inventory.yml")["all"]["children"]["cisco"]["hosts"]
    for name in ("STUD2-SW1", "STUD2-SW2", "STUD2-SW3"):
        host = load(PART2 / f"host_vars/{name}.yml")
        require(inventory[name]["ansible_host"] == host["management_ip"], "Inventory og switchadresse er ulike")
    for name, host in routers.items():
        require(inventory[name]["ansible_host"] == host["upper_management_ip"],
                "Inventory og ruterens oeverste adresse er ulike")
    print(f"OK: {len(yaml_files)} YAML-filer, adskilte subnett/DHCP-intervaller og unik portbruk.")
    return common, routers


if __name__ == "__main__":
    try:
        validate()
    except (ValueError, KeyError, yaml.YAMLError) as error:
        print(f"Ugyldig plan: {error}", file=sys.stderr)
        raise SystemExit(1)
