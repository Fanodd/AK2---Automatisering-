"""Forhåndsvis ruternes VLAN/DHCP-konfigurasjon uten SSH eller rack."""
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined

from validate_plan import PART2, validate


def main():
    common, routers = validate()
    env = Environment(loader=FileSystemLoader(PART2 / "templates"),
                      undefined=StrictUndefined, keep_trailing_newline=True)
    output = PART2 / "rendered"
    output.mkdir(exist_ok=True)
    for name, host in routers.items():
        variables = {**common, **host, "inventory_hostname": name}
        for template_name in ("router_vlans", "dhcp"):
            rendered = env.get_template(template_name + ".j2").render(**variables)
            path = output / f"{name}_{template_name}.cfg"
            path.write_text(rendered, encoding="utf-8")
            print(path)


if __name__ == "__main__":
    main()
