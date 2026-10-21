# SSH fra Ubuntu eller Windows

Kommandoene bruker de endelige administrasjonsadressene. Før Ansible kjøres godtas vertsnøkkelen for hver enhet fra Ubuntu, som har en annen known_hosts-fil enn Windows.

```bash
# Cisco 2901
ssh -o KexAlgorithms=+diffie-hellman-group14-sha1 -o HostKeyAlgorithms=+ssh-rsa admin@192.168.20.1

# Catalyst 3650
ssh admin@192.168.20.2

# Cisco 4221
ssh admin@192.168.20.3

# Catalyst 2960
ssh -o KexAlgorithms=+diffie-hellman-group14-sha1 -o HostKeyAlgorithms=+ssh-rsa -o Ciphers=+aes128-cbc -o MACs=+hmac-sha1 admin@192.168.21.4

# Catalyst 1000
ssh -o KexAlgorithms=+diffie-hellman-group14-sha1 -o HostKeyAlgorithms=+ssh-rsa admin@192.168.21.5
```

De ekstra algoritmene tillates bare for disse labtilkoblingene. Ansible bruker Paramiko og arver ikke automatisk algoritmevalgene fra OpenSSH-kommandoene. Paramiko 4.0.0 er derfor låst i kravfilen.

Etter at labutstyr er resatt og nøklene er generert på nytt kan klienten varsle om endret vertsnøkkel. Kontroller at du har riktig enhet før den gamle nøkkelen eventuelt fjernes, for eksempel `ssh-keygen -R 192.168.21.5` for SW3. Koble deretter til igjen.
