# AK2---Automatisering-
Min innlevering for AK2 Automatisering. 

# Arbeidskrav 2 Automatisering av Cisco-utstyr

Dette repoet inneholder løsningen min for grønn side, STUD2, i arbeidskrav 2. Først setter jeg opp SSH med Python over konsollkabel. Deretter bruker jeg Ansible over SSH til administrasjon, VLAN, trunker, ruter-subinterface, EtherChannel og DHCP.

Rosa side, STUD1, inngår som en logisk del av casen. Den bruker VLAN 99 i stedet for VLAN 10 i oppgavetegningen og samme typer utstyr som grønn side. Repoet automatiserer de to ruterne og tre switchene på grønn side. Adresseplanen og forbindelsen mot den logiske rosa siden er beskrevet i [STUD1_NETWORK.md](part2/STUD1_NETWORK.md).

## Utstyr og adresser

| Navn | Modell | Programvare | Adresse i inventory |
|---|---|---|---|
| STUD2-R1 | Cisco 2901 | IOS 15.7(3)M8 | 192.168.20.1 |
| STUD2-SW1 | Catalyst WS-C3650-24PS | IOS XE 16.12.7 | 192.168.20.2 |
| STUD2-R2 | Cisco ISR4221/K9 | IOS XE 17.6.5a | 192.168.20.3 |
| STUD2-SW2 | Catalyst WS-C2960-24TT-L | IOS 15.0(2)SE11 | 192.168.21.4 |
| STUD2-SW3 | Catalyst C1000-24T-4G-L | IOS 15.2(7)E6 | 192.168.21.5 |

Alle nettene under bruker /24, nettverksmaske 255.255.255.0.

| Nett | Bruk | Gateway eller ruteradresser |
|---|---|---|
| 192.168.20.0/24 | PC, øverste switch og ruternes øverste interface | R1 .1, R2 .3, PC .10 |
| 192.168.21.0/24 | Administrasjon under ruterne, VLAN 1 | R1 .1, R2 .2; SW2 og SW3 bruker .1 som gateway |
| 172.16.20.0/24 | Klienter i VLAN 20, grønn side | Gateway .1 på R1, R2 .2 |
| 192.168.99.0/24 | Klienter i VLAN 99, rosa side | Gateway .1 på rosa side; mine rutere bruker .252 og .253 |

VLAN 20 bruker 172.16.20.0/24 fordi 192.168.20.0/24 allerede er brukt til administrasjon. VLAN 1 har statiske administrasjonsadresser og ingen DHCP-pool.

## Kabling

| Fra | Til |
|---|---|
| Lab-PC Ethernet | 3650 Gi1/0/1 |
| 3650 Gi1/0/2 | 2901 Gi0/0 |
| 3650 Gi1/0/3 | 4221 Gi0/0/0 |
| 2901 Gi0/1 | 2960 Fa0/1 |
| 4221 Gi0/0/1 | 2960 Fa0/2 |
| 2960 Fa0/24 | Catalyst 1000 Gi1/0/24 |
| Min Catalyst 1000 Gi1/0/22 og Gi1/0/23 | Rosa Catalyst 1000 Gi1/0/22 og Gi1/0/23, Port-channel1 |
| Klient i VLAN 20 | Min Catalyst 1000 Gi1/0/1 |
| Klient i VLAN 99 | Min Catalyst 1000 Gi1/0/2 |

Klientporter fra begge VLAN er definert på den grønne nederste switchen. I casen har rosa side tilsvarende klientporter. Forbindelsen mellom sidene er en del av topologibeskrivelsen. Gi1/0/24 er intern uplink, og må ikke brukes som EtherChannel-medlem.

Interne trunker under ruterne fører VLAN 1, 20 og 99. Native VLAN er 1. VLAN 1 går untagget til administrasjonsadressen på ruternes fysiske interface; klient-VLAN går tagget til subinterface. EtherChannel mellom sidene fører bare VLAN 20 og 99, med native VLAN 1 på begge ender. VLAN 1 er utelatt fra allowed-listen mellom sidene.

## Filstruktur

```text
part1/setup_ssh.py                    SSH-oppsett via konsoll
part2/inventory.yml                  Enheter og tilkoblingsvalg
part2/group_vars/all.yml             VLAN, subnett, gateway og DHCP-intervaller
part2/host_vars/                     Interface, porter og enhetsverdier
part2/playbooks/site.yml             Samlet Ansible-kjøring
part2/playbooks/check_connection.yml Les status uten konfigurasjonsendringer
part2/playbooks/verify_network.yml   Les VLAN, ruting, DHCP og LACP-status
part2/templates/                     Jinja-maler for ruter-VLAN og DHCP
tools/validate_plan.py               Lokal kontroll av adresseplan og porter
tools/render_configs.py              Generer konfigurasjonsutkast uten rack
tests/                              Automatiske lokale tester
```

## Del 1 Python via konsoll

Python må kjøre på PC-en med konsollkabelen. Eksemplet bruker Windows med COM1, 9600 baud, 8 databiter, ingen paritet, 1 stoppbit og ingen flytkontroll. Portnavnet velges ut fra den aktuelle PC-en.

Åpne PowerShell i repoets rotmappe. Installer Python 3.10 eller nyere og kjør:

```powershell
py -m venv .venv-win
.\.venv-win\Scripts\python.exe -m pip install -r requirements.txt
.\.venv-win\Scripts\python.exe part1/setup_ssh.py --list-ports
```

Åpne enheten i PuTTY først. Svar `no` på initial configuration dialog og avslutt eventuell autoinstall-dialog. Logg inn hvis nødvendig, og start ved en vanlig `>`- eller `#`-prompt. Scriptet håndterer enable-modus, men ikke oppstartsveiviser eller konsollinnlogging. Kontroller interface med `show ip interface brief` og VTY-linjer med `show line`.

Lukk PuTTY før Python åpner samme port. Kjør først uten `--apply` for å se kommandoene uten å endre en enhet:

```powershell
.\.venv-win\Scripts\python.exe part1/setup_ssh.py
.\.venv-win\Scripts\python.exe part1/setup_ssh.py --apply
```

Scriptet spør etter hostname, domene, bruker, SSH-passord, enable-passord, adresse, VLAN eller fysisk interface, VTY-område og konsollport. Passord vises skjult og lagres ikke i repoet. Eksemplet bruker `lab.local` og brukeren `admin` med privilege 15.

Bruk følgende verdier ved førstegangsoppsett eller gjenoppretting:

| Enhetstype og hostname | IP med prefiks | Interface eller VLAN | Gateway for switch |
|---|---|---|---|
| router STUD2-R1 | 192.168.20.1/24 | GigabitEthernet0/0 | Ikke aktuelt |
| router STUD2-R2 | 192.168.20.3/24 | GigabitEthernet0/0/0 | Ikke aktuelt |
| switch STUD2-SW1 | 192.168.20.2/24 | VLAN 1 | 192.168.20.1 |
| switch STUD2-SW2 | 192.168.21.4/24 | VLAN 1 | 192.168.21.1 |
| switch STUD2-SW3 | 192.168.21.5/24 | VLAN 1 | 192.168.21.1 |

Velg siste VTY-linje ut fra enheten. 2960 og Catalyst 1000 har 16 linjer, altså 0–15. Sjekk `show line` på de øvrige enhetene, og velg 4 for fem VTY-linjer eller 15 for 16. Kolonnen med absolutte linjenumre er ikke det samme som VTY-nummeret.

Bekreft med `JA` eller `ja`. Scriptet setter opp SSH versjon 2, genererer 2048-bit RSA-nøkler og beholder eksisterende nøkler hvis enheten spør om erstatning. Det prøver `ip domain name` hvis `ip domain-name` avvises. Bekreft lagring når du blir spurt. Manuell lagring kan gjøres med `write memory`.

Ved feil stopper scriptet. Tidligere kommandoer rulles ikke tilbake. Kontroller prompt og konfigurasjon i konsollen før ny kjøring. På Linux kan samme script brukes med pySerial og riktig portnavn, for eksempel /dev/ttyUSB0. COM-numre kan ikke oversettes direkte til Linux-portnavn.

## Del 2 Ansible fra Ubuntu

Eksemplet bruker Ubuntu i WSL på lab-PC-en. Ansible kjøres fra Linux-miljøet; Windows brukes til konsollscriptet. Installer avhengighetene mens PC-en har internett. Åpne Ubuntu i repoets rotmappe:

```bash
sudo apt update
sudo apt install -y python3-venv git openssh-client
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r part2/requirements.txt
ansible-galaxy collection install -r part2/collections/requirements.yml
```

Kravfilene låser ansible-core til 2.21.5, cisco.ios til 11.6.0 og ansible.netcommon til 8.7.1. Python må tilfredsstille ansible-core-versjonens krav. Paramiko er låst til 4.0.0 fordi versjon 5 fjernet SHA-1-nøkkelutvekslingen som eldre IOS i labben krever.

Hvert nytt Ubuntu-vindu må aktivere `.venv` igjen. Ikke bruk en Windows-venv i Ubuntu. Dersom filene ligger på Windows-disken, må du bruke en annen venv-mappe enn Windows-miljøet; eksemplene bruker `.venv-win` for Windows og `.venv` for Ubuntu.

Sett Windows sin fysiske Ethernet-adapter til 192.168.20.10/24 uten gateway og DNS. Koble den til 3650 Gi1/0/1. Etter konsolloppsettet konfigureres ruternes nederste administrasjonsinterface først. Fra repoets rotmappe:

```bash
cd part2
ansible-playbook -i inventory.yml playbooks/setup_management_routers.yml --ask-pass
```

Deretter legges ruten til switchene inn i Windows PowerShell som administrator:

```powershell
route add 192.168.21.0 mask 255.255.255.0 192.168.20.1
```

Ruten forsvinner ved omstart. PC-en har ikke internett gjennom laboppsettet; når kabelen flyttes tilbake til skolens nett må IP og DNS normalt settes til automatisk, og labinnstillingene gjenopprettes før neste labøkt.

Kontroller ping og godta SSH-vertsnøkkelen fra Ubuntu for hver enhet før Ansible kobler til. Ubuntu har egen known_hosts-fil. [SSH_COMMANDS.md](part2/SSH_COMMANDS.md) viser kommandoene, inkludert eldre algoritmer. Ikke slå av vertsnøkkelkontroll globalt.

Kjør lokal kontroll og syntakskontroll før konfigurering. Disse trenger ikke fysisk rack:

```bash
python ../tools/validate_plan.py
python ../tools/render_configs.py
ansible-playbook -i inventory.yml playbooks/site.yml --syntax-check
```

Deretter kan status leses eller hele oppsettet sendes:

```bash
ansible-playbook -i inventory.yml playbooks/check_connection.yml --ask-pass
ansible-playbook -i inventory.yml playbooks/site.yml --ask-pass
ansible-playbook -i inventory.yml playbooks/verify_network.yml --ask-pass
```

`--ask-pass` bruker samme SSH-passord for enhetene i kjøringen. Ved forskjellige passord kjøres enhetene med `--limit`, eller passord organiseres med Ansible Vault. Ingen passord skal skrives i inventory eller lastes opp til GitHub.

`site.yml` kontrollerer adresseplanen, konfigurerer administrasjon, VLAN og trunker, ruter-subinterface, EtherChannel og DHCP, og leser til slutt status. Konfigurasjonen lagres til startup-config. Enkeltplaybookene kan kjøres separat, som forklart i [part2/README.md](part2/README.md).

Playbookene legger til eller oppdaterer den beskrevne konfigurasjonen. De sletter ikke ukjente gamle DHCP-pooler, eksklusjoner, VLAN eller interface. De forutsetter enheter som er tilbakestilt, eller det dokumenterte laboppsettet. Endres adresseplanen senere, må gammel konfigurasjon som ikke lenger skal brukes også fjernes.

## DHCP og ruting

Begge mine rutere får DHCP-pool for VLAN 20 og 99. De deler ut adskilte intervaller:

| VLAN | DHCP fra R1 | DHCP fra R2 | Gateway som klientene mottar |
|---|---|---|---|
| 20 | 172.16.20.50–149 | 172.16.20.150–239 | 172.16.20.1 |
| 99 | 192.168.99.50–149 | 192.168.99.150–239 | 192.168.99.1 |

Alle andre brukbare adresser er ekskludert fra DHCP. Poolene deler ikke leiedatabase. Dette er adskilte DHCP-intervaller, ikke DHCP-failover eller automatisk gateway-reserve. VLAN 20 er avhengig av R1 som gateway; VLAN 99 er avhengig av gatewayen på rosa side. Ingen internett- eller NAT-konfigurasjon er med.

VLAN 99-gatewayen på rosa side trenger en rute til 172.16.20.0/24 via 192.168.99.252 for kommunikasjon fra VLAN 99 til VLAN 20. Mine rutere er direkte koblet til begge klientnettene. Rosa side må føre VLAN 99 og 20 frem til EtherChannel, og skal ikke ha en konkurrerende DHCP-server. Dette er forutsetninger for oppsettet, ikke konfigurasjon som repoet sender til rosa side.

DNS-serverlisten er tom som standard fordi det ikke er etablert en DNS-tjeneste. Legg eventuelt inn en server som faktisk kan nås i `dhcp_dns_servers`.

## Endre og vedlikeholde oppsettet

- Endre adresser, VLAN, gateway, DHCP-intervaller og DNS i `part2/group_vars/all.yml`.
- Endre porter, interface-navn, administrasjonsadresser og DHCP-eksklusjoner i `part2/host_vars/`.
- Oppdater `inventory.yml` når en administrasjonsadresse endres. Konsollscriptet endrer ikke inventory automatisk.
- Ved nye VLAN må også DHCP-eksklusjoner, trunklister og EtherChannel-variablene oppdateres. Den lokale kontrollen stopper ved flere typer avvik.
- Kjør kontrollene på nytt etter endringer. Konfigurasjonsoppgavene sammenligner ønskede linjer med running-config før de sender endringer.

## Lokale kontroller

Fra repoets rotmappe med Python-miljøet aktivert:

```bash
python -m pip install -r tools/requirements.txt
python -m unittest discover -s tests -v
python tools/validate_plan.py
python tools/render_configs.py
```

Tester med simulert konsoll dekker domenesyntaks, kommandofeil, syslog ved prompt, timeout og skjuling av passord. Plan-testene kontrollerer blant annet subnettoverlapp, gateway i DHCP-pool, eksklusjoner og portkonflikter. Genererte ruterkonfigurasjoner legges i `part2/rendered/` og er utelatt fra Git.

## Feilsøking

Hvis 4221 avviser `ip domain-name`, prøver scriptet automatisk varianten `ip domain name`. For eldre SSH-algoritmer brukes kommandoene i SSH_COMMANDS.md og Paramiko-versjonen i kravfilen.

Ved tilkoblingsfeil kontrolleres først riktig enhet, kabel, adresse og maske. Bruk `show ip interface brief`, `ipconfig`, ping og rutetabellen. `up/up` på en port beskriver portens tilstand; både IP-oppsettet og ruten til målet må også være riktige. PC-adressen er 192.168.20.10, og de nederste switchene ligger i 192.168.21.0/24.

## Kilder

- [pySerial](https://pyserial.readthedocs.io/en/latest/shortintro.html)
- [Cisco SSH](https://www.cisco.com/c/en/us/support/docs/security-vpn/secure-shell-ssh/4145-ssh.html)
- [Cisco IOS Ansible-collection](https://docs.ansible.com/projects/ansible/latest/collections/cisco/ios/index.html)
- [Cisco DHCP-server](https://www.cisco.com/c/en/us/td/docs/ios-xml/ios/ipaddr_dhcp/configuration/12-4/dhcp-12-4-book/config-dhcp-server.html)
- [Paramiko endringslogg](https://www.paramiko.org/changelog.html)
- [OpenSSH eldre algoritmer](https://www.openssh.org/legacy.html)
