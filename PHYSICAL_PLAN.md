# Kobling og administrasjonsnett for STUD2

| Fra | Til |
|---|---|
| Lab-PC Ethernet | STUD2-SW1 3650 Gi1/0/1 |
| STUD2-SW1 Gi1/0/2 | STUD2-R1 2901 Gi0/0 |
| STUD2-SW1 Gi1/0/3 | STUD2-R2 4221 Gi0/0/0 |
| STUD2-R1 Gi0/1 | STUD2-SW2 2960 Fa0/1 |
| STUD2-R2 Gi0/0/1 | STUD2-SW2 Fa0/2 |
| STUD2-SW2 Fa0/24 | STUD2-SW3 Catalyst 1000 Gi1/0/24 |

Tabellen definerer kablingen for grønn side. Rosa side er en logisk del av casen. Den delte EtherChannel-forbindelsen bruker Catalyst 1000 Gi1/0/22 og Gi1/0/23 i begge ender. Gi1/0/1 på grønn Catalyst 1000 er klientport for VLAN 20, og Gi1/0/2 er klientport for VLAN 99. Se hoved-README for hele adresseplanen.

## Administrasjon under ruterne

Øverste administrasjonsnett er 192.168.20.0/24. Nederste administrasjonsnett er 192.168.21.0/24, med VLAN 1 som administrasjons-VLAN. Klient-VLAN 20 bruker 172.16.20.0/24, og VLAN 99 bruker 192.168.99.0/24. Administrasjon og klientnett bruker separate subnett.

| Enhet | Interface | Adresse | Gateway |
|---|---|---|---|
| STUD2-R1 | Gi0/1 | 192.168.21.1/24 | Direkte tilkoblet nett |
| STUD2-R2 | Gi0/0/1 | 192.168.21.2/24 | Direkte tilkoblet nett |
| STUD2-SW2 | Vlan1 | 192.168.21.4/24 | 192.168.21.1 |
| STUD2-SW3 | Vlan1 | 192.168.21.5/24 | 192.168.21.1 |

Playbooken setup_management_routers.yml konfigurerer ruternes nederste interface og lagrer konfigurasjonen. Verdiene ligger i host_vars. Administrasjonsadressene på switchene settes med konsollscriptet før Ansible brukes. Inventory bruker 192.168.21.4 for SW2 og 192.168.21.5 for SW3.

Kjør i Windows PowerShell som administrator for en rute som varer frem til omstart:

```powershell
route add 192.168.21.0 mask 255.255.255.0 192.168.20.1
```

PC-en beholder 192.168.20.10/24 og Ethernet-kabelen i 3650 Gi1/0/1. Test ping mot 192.168.21.4 og 192.168.21.5 både i Windows og Ubuntu. Kjør deretter check_connection.yml mot hele inventory. Returruten for switchene er gateway 192.168.21.1 på R1, som også er direkte koblet til PC-ens nett.
