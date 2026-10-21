# Rosa side i casen

Rosa side er en logisk del av oppgavetopologien. Dette dokumentet definerer oppsettet der, mens repoets playbooks automatiserer grønn side. Begge sider bruker samme typer utstyr. Følgende verdier gjelder for den rosa delen av casen:

- VLAN 99 er rosa klientnett, 192.168.99.0/24, med gateway 192.168.99.1 på rosa ruter.
- 192.168.99.252 og .253 er ruteradressene på grønn side og brukes ikke av andre enheter.
- Bare de to grønne ruterne leverer DHCP for VLAN 20 og 99. Rosa side har ingen konkurrerende DHCP-pooler i disse nettene.
- VLAN 20 og 99 er opprettet på de rosa switchene som fører klienttrafikken. Klientporter settes til access i riktig VLAN. Begge VLAN føres på de nødvendige trunkene frem til EtherChannel.
- Port-channel1 bruker LACP active og Gi1/0/22–23 på rosa Catalyst 1000. Allowed-listen er 20,99 og native VLAN er 1, lik grønn side. VLAN 1 skal ikke deles mellom sidene.

På ruteren som eier 192.168.99.1 trengs denne ruten for trafikk fra VLAN 99 til VLAN 20:

```text
configure terminal
ip route 172.16.20.0 255.255.255.0 192.168.99.252
end
write memory
```

Forutsetningen er at ruteren allerede har VLAN 99-interfacet med 192.168.99.1/24 og at den kan nå 192.168.99.252 gjennom trunkene. Kommandoene over oppretter ikke dette interfacet. De er dokumentasjon for rosa side og kjøres ikke av våre playbooks.

DHCP-broadcast for VLAN 99 går over EtherChannel til de grønne ruterne, som har egne interface i VLAN 99. Derfor trengs ingen DHCP-relay for klienter i de to delte VLAN-ene. Klienter i VLAN 20 bruker 172.16.20.1 på grønn side som gateway, også når klienten er fysisk koblet til rosa side.

Gatewayene i modellen er statiske. Ruten til VLAN 20 peker på grønn R1. Automatisk gateway-failover, dynamisk ruting og internettilgang inngår ikke i oppsettet.
