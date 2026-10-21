# Ansible-oppsett for STUD2

Denne mappen inneholder inventory, variabler, playbooks og maler for grønn side. [Hoved-README](../README.md) beskriver kabling, adresser, installasjon og bruk. Før Ansible kan konfigurere enhetene må del 1 kjøres og administrasjonsnettet gjøres tilgjengelig.

## Adresseplan og eierskap

VLAN 20 bruker 172.16.20.0/24 med gateway 172.16.20.1 på R1. VLAN 99 bruker 192.168.99.0/24 med gateway 192.168.99.1 på den logiske rosa siden. De grønne ruteradressene i VLAN 99 er .252 og .253. DHCP for begge klient-VLAN leveres fra de to grønne ruterne, med adskilte intervaller. Dette er adresseplanen som løsningen bygger på.

Interne trunker fører 1,20,99, med VLAN 1 som untagget administrasjon. EtherChannel mellom sidene fører bare 20,99. Ingen administrasjonsadresser byttes av klient-playbookene. SW2 bruker 192.168.21.4 og SW3 192.168.21.5; de gamle 192.168.20.4/.5 skal ikke ligge i inventory.

## Kjøring

Åpne Ubuntu i denne mappen og aktiver miljøet som ble installert fra repoets rotmappe:

```bash
source ../.venv/bin/activate
ansible-inventory -i inventory.yml --graph
python ../tools/validate_plan.py
ansible-playbook -i inventory.yml playbooks/site.yml --syntax-check
```

Ved førstegangsoppsett kjøres setup_management_routers.yml før de nederste switchene kan nås. PC-en trenger ruten 192.168.21.0/24 via 192.168.20.1. Godta hver enhets SSH-vertsnøkkel fra Ubuntu med kommandoene i [SSH_COMMANDS.md](SSH_COMMANDS.md). Ansible bruker Paramiko 4.0.0 og passord fra `--ask-pass`.

| Playbook | Funksjon |
|---|---|
| validate_plan.yml | Lokal kontroll uten SSH |
| check_connection.yml | Les hostname, versjon og interface-status |
| setup_management_routers.yml | Konfigurer R1 Gi0/1 og R2 Gi0/0/1 for 192.168.21.0/24 |
| setup_vlans_trunks.yml | VLAN, interne trunker og klientporter; øverste switch beholder VLAN 1 |
| setup_router_vlans.yml | Taggede subinterface for VLAN 20 og 99 på begge rutere |
| setup_etherchannel.yml | LACP Port-channel1 på Catalyst 1000 Gi1/0/22–23 |
| setup_dhcp.yml | DHCP-pooler og eksklusjoner på begge rutere |
| verify_network.yml | Les VLAN, trunker, ruting, DHCP og LACP-status |
| site.yml | Kjør lokal kontroll og konfigurasjonsplaybookene i riktig rekkefølge |

Konfigurer hele grønn side:

```bash
ansible-playbook -i inventory.yml playbooks/site.yml --ask-pass
```

Les status etterpå:

```bash
ansible-playbook -i inventory.yml playbooks/verify_network.yml --ask-pass
```

Enkeltplaybooks kjøres på samme måte ved å bytte filnavn. `--limit STUD2-R1` begrenser en kjøring til én enhet, men hopper også over localhost-valideringen i site.yml. Kjør derfor `python ../tools/validate_plan.py` separat før bruk av `--limit` eller en enkelt konfigurasjonsplaybook.

DHCP-eksklusjonene i ruternes host_vars må stemme med intervallene i group_vars. Den lokale kontrollen sammenligner dette. Poolnavnene inneholder ruternavn og VLAN. Oppsettet rydder ikke automatisk gamle pooler eller eksklusjoner ved senere endring av adresseplanen.

## Rosa side i casen

[STUD1_NETWORK.md](STUD1_NETWORK.md) definerer VLAN, gateway, rute og DHCP-eierskap for den logiske rosa siden. [STUD1_ETHERCHANNEL.txt](STUD1_ETHERCHANNEL.txt) viser eksempelkonfigurasjonen for den rosa Catalyst 1000-en. Repoets inventory omfatter bare grønn side.

## Kontroller oppsettet

`validate_plan.py` kontrollerer adresseplanen, portbruken og DHCP-intervallene. `render_configs.py` genererer ruterkonfigurasjonen fra malene. `--syntax-check` kontrollerer playbook-syntaks med installert Ansible og collectioner. Disse kommandoene kan kjøres uten rack. `verify_network.yml` leser konfigurasjonsstatus fra enhetene når de er tilgjengelige over SSH.
