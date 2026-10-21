"""Tester adresseplan og konfigurasjonsmaler uten SSH eller fysisk rack."""
import copy
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch

from jinja2 import Environment, FileSystemLoader, StrictUndefined

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("validate_plan", ROOT / "tools/validate_plan.py")
plan = importlib.util.module_from_spec(spec)
spec.loader.exec_module(plan)


class PlanTests(unittest.TestCase):
    def setUp(self):
        self.common = plan.load(plan.PART2 / "group_vars/all.yml")
        self.original_load = plan.load

    def validate_changed(self, path_suffix, transform):
        def altered(path):
            result = copy.deepcopy(self.original_load(path))
            if path.as_posix().endswith(path_suffix):
                transform(result)
            return result
        with patch.object(plan, "load", side_effect=altered):
            return plan.validate()

    def test_real_plan_is_consistent(self):
        plan.validate()

    def test_rejects_client_network_overlapping_management(self):
        def change(data):
            data["client_vlans"][0]["network"] = "192.168.20.0"
        with self.assertRaisesRegex(ValueError, "Overlappende subnett"):
            self.validate_changed("group_vars/all.yml", change)

    def test_rejects_gateway_in_dhcp_range(self):
        def change(data):
            data["client_vlans"][0]["gateway"] = "172.16.20.100"
        with self.assertRaisesRegex(ValueError, "gateway/ruteradresse"):
            self.validate_changed("group_vars/all.yml", change)

    def test_rejects_missing_exclusions(self):
        def change(data):
            data["dhcp_exclusions"] = []
        with self.assertRaisesRegex(ValueError, "Eksklusjoner gir feil"):
            self.validate_changed("host_vars/STUD2-R1.yml", change)

    def test_rejects_client_port_used_by_etherchannel(self):
        def change(data):
            data["client_ports"][0]["interface"] = "GigabitEthernet1/0/22"
        with self.assertRaisesRegex(ValueError, "Port brukt flere ganger"):
            self.validate_changed("host_vars/STUD2-SW3.yml", change)

    def test_rejects_management_vlan_shared_with_peer(self):
        def change(data):
            data["etherchannel_allowed_vlans"] = "1,20,99"
        with self.assertRaisesRegex(ValueError, "utelate VLAN 1"):
            self.validate_changed("host_vars/STUD2-SW3.yml", change)

    def test_templates_render_both_routers_and_both_vlans(self):
        common, routers = plan.validate()
        env = Environment(loader=FileSystemLoader(plan.PART2 / "templates"),
                          undefined=StrictUndefined)
        for name, host in routers.items():
            context = {**common, **host, "inventory_hostname": name}
            router_text = env.get_template("router_vlans.j2").render(**context)
            dhcp_text = env.get_template("dhcp.j2").render(**context)
            for vlan in common["client_vlans"]:
                self.assertIn(f"encapsulation dot1Q {vlan['id']}", router_text)
                self.assertIn(f"ip address {vlan['router_addresses'][name]} {vlan['mask']}", router_text)
                self.assertIn(f"default-router {vlan['gateway']}", dhcp_text)
                self.assertIn(f"network {vlan['network']} {vlan['mask']}", dhcp_text)
            self.assertNotIn("no ip address", router_text)
            self.assertNotIn("dns-server", dhcp_text)

    def test_all_imported_playbooks_exist(self):
        site = plan.load(plan.PART2 / "playbooks/site.yml")
        for entry in site:
            self.assertTrue((plan.PART2 / "playbooks" / entry["import_playbook"]).is_file())


if __name__ == "__main__":
    unittest.main()
