"""Sett opp SSH på Cisco IOS/IOS XE via konsoll. Kjør uten argumenter for forhåndsvisning."""

import argparse
import getpass
import ipaddress
import re
import time

# IOS kan skrive syslog rett etter prompten, uten et nytt linjeskift.
PRIVILEGED_PROMPT = r"(?:^|[\r\n])[\w.-]+(?:\([^\r\n]*\))?#[ \t]*(?=$|[\r\n]|\*)"


def ask(label, default=None, pattern=None):
    while True:
        value = input(f"{label}" + (f" [{default}]" if default else "") + ": ").strip()
        value = value or default
        if value and (pattern is None or re.fullmatch(pattern, value)):
            return value
        print("Ugyldig verdi. Prøv igjen.")


def secret(label):
    while True:
        value = getpass.getpass(label + ": ")
        if value and all(33 <= ord(c) <= 126 for c in value) and "?" not in value:
            if value == getpass.getpass("Gjenta: "):
                return value
        print("Bruk synlige ASCII-tegn uten mellomrom eller ?, og gjenta likt.")


def collect():
    kind = ask("Enhetstype (switch/router)", pattern=r"switch|router")
    hostname = ask("Hostname", pattern=r"[A-Za-z][A-Za-z0-9-]{0,62}")
    domain = ask("Domenenavn for SSH", "lab.local", r"[A-Za-z0-9][A-Za-z0-9.-]*")
    username = ask("Nytt SSH-brukernavn", pattern=r"[A-Za-z][A-Za-z0-9_-]*")
    password = secret("Nytt SSH-passord")
    enable = secret("Nytt enable-passord")
    while True:
        try:
            address = ipaddress.IPv4Interface(ask("Administrasjonsadresse med prefiks, f.eks. 192.168.10.2/24"))
            break
        except ValueError:
            print("Oppgi en gyldig IPv4-adresse med /prefiks.")
    commands = ["configure terminal", f"hostname {hostname}", f"ip domain-name {domain}",
                f"username {username} privilege 15 secret {password}", f"enable secret {enable}"]
    if kind == "switch":
        vlan = int(ask("Administrasjons-VLAN", "1", r"[0-9]+"))
        if not 1 <= vlan <= 4094:
            raise ValueError("VLAN må være mellom 1 og 4094.")
        if vlan != 1:
            commands += [f"vlan {vlan}", "exit"]
        commands += [f"interface vlan {vlan}"]
    else:
        interface = ask("Interface mot administrasjonsnettet, f.eks. GigabitEthernet0/0/0",
                        pattern=r"[A-Za-z][A-Za-z0-9/.-]*")
        commands += [f"interface {interface}"]
    commands += [f"ip address {address.ip} {address.netmask}", "no shutdown", "exit"]
    if kind == "switch":
        gateway = str(ipaddress.IPv4Address(ask("Gateway i administrasjonsnettet")))
        if ipaddress.IPv4Address(gateway) not in address.network:
            raise ValueError("Gateway må ligge i samme subnett.")
        commands += [f"ip default-gateway {gateway}"]
    vty = ask("Siste VTY-linje (sjekk enheten med show line)", "4", r"4|15")
    commands += ["crypto key generate rsa general-keys modulus 2048", "ip ssh version 2",
                 f"line vty 0 {vty}", "login local", "transport input ssh", "exit", "end"]
    return commands


def safe_command(command):
    """Skjul bare secret-argumentet, ikke tilfeldige treff i kommandoteksten."""
    return re.sub(r"(\bsecret\s+).*", r"\1<skjult>", command)


class CommandRejected(RuntimeError):
    def __init__(self, syntax_error):
        super().__init__("Enheten avviste en kommando.")
        self.syntax_error = syntax_error


class Console:
    def __init__(self, port):
        self.port = port

    def send(self, command):
        self.port.write((command + "\r").encode("ascii"))
        self.port.flush()

    def expect(self, pattern, timeout=15, check_errors=True):
        output = ""
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            output += self.port.read(self.port.in_waiting or 1).decode("ascii", errors="replace")
            if check_errors and re.search(r"% (?:Invalid input|Incomplete command|Ambiguous command|Error)", output, re.I):
                raise RuntimeError("Enheten avviste en kommando. Kontroller IOS og syntaks i konsollen.")
            if re.search(pattern, output):
                return output
        raise RuntimeError("Ingen forventet respons. Kontroller konsoll, baudrate og enhetens prompt.")

    def command(self, command, timeout=15):
        print("Sender: " + safe_command(command))
        self.send(command)
        # Les helt frem til prompten før eventuell ny syntaks prøves.
        try:
            output = self.expect(PRIVILEGED_PROMPT, timeout, check_errors=False)
        except RuntimeError:
            raise RuntimeError("Ingen forventet respons etter: " + safe_command(command)
                               + ". Kontroller prompten i PuTTY før ny kjøring.") from None
        syntax_error = bool(re.search(r"% (?:Invalid input|Incomplete command|Ambiguous command)", output, re.I))
        if syntax_error or re.search(r"% Error", output, re.I):
            raise CommandRejected(syntax_error)
        return output

    def configure_command(self, command):
        try:
            return self.command(command)
        except CommandRejected as error:
            if command.startswith("ip domain-name ") and error.syntax_error:
                alternative = command.replace("ip domain-name ", "ip domain name ", 1)
                print("Enheten krever alternativ syntaks: " + alternative)
                try:
                    return self.command(alternative)
                except CommandRejected:
                    raise RuntimeError("Enheten avviste: " + safe_command(alternative)) from None
            raise RuntimeError("Enheten avviste: " + safe_command(command)) from None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="Send kommandoene til en fysisk enhet")
    parser.add_argument("--list-ports", action="store_true", help="Vis tilgjengelige konsollporter")
    parser.add_argument("--baud", type=int, default=9600)
    args = parser.parse_args()
    if args.list_ports:
        from serial.tools import list_ports
        for port in list_ports.comports():
            print(f"{port.device}: {port.description}")
        return
    commands = collect()
    print("\nPlanlagte kommandoer (passord skjult):")
    for command in commands:
        print(safe_command(command))
    if not args.apply:
        print("\nForhåndsvisning ferdig. Ingen enhet er endret. Bruk --apply i labben.")
        return
    import serial
    port = ask("Konsollport, f.eks. COM3 eller /dev/ttyUSB0")
    print("Lukk PuTTY/andre konsollprogrammer. Enheten må være ferdig startet og innlogget.")
    if input("Skriv JA for å konfigurere denne enheten: ").strip().upper() != "JA":
        print("Avbrutt før konfigurering.")
        return
    with serial.Serial(port, args.baud, timeout=0.2, write_timeout=5,
                       xonxoff=False, rtscts=False, dsrdtr=False) as connection:
        console = Console(connection)
        console.send("")
        response = console.expect(r"(?:^|\n)[\w.-]+[>#]\s*$")
        if response.rstrip().endswith(">"):
            console.send("enable")
            response = console.expect(r"Password:\s*$|(?:^|\n)[\w.-]+#\s*$")
            if re.search(r"Password:\s*$", response):
                console.send(getpass.getpass("Eksisterende enable-passord: "))
                console.expect(r"(?:^|\n)[\w.-]+#\s*$")
        console.command("terminal length 0")
        for command in commands:
            if command.startswith("crypto key generate"):
                print("Sender: " + safe_command(command))
                console.send(command)
                try:
                    response = console.expect(r"replace them\?[^\r\n]*$|" + PRIVILEGED_PROMPT, 120)
                except RuntimeError:
                    raise RuntimeError("RSA-nøkkelgenerering feilet eller fikk ingen forventet respons. "
                                       "Kontroller konsoll og eksisterende nøkler før ny kjøring.") from None
                if re.search(r"replace them\?", response):
                    console.send("no")
                    console.expect(PRIVILEGED_PROMPT)
                    print("Eksisterende RSA-nøkler beholdes.")
            else:
                console.configure_command(command)
        print(console.command("show ip ssh"))
        print(console.command("show ip interface brief"))
        if input("Skriv JA for å lagre running-config til startup-config: ").strip().upper() == "JA":
            console.command("write memory", 30)
            print("Konfigurasjonen er lagret.")
        else:
            print("Konfigurasjonen er aktiv, men er ikke lagret til neste omstart.")


if __name__ == "__main__":
    try:
        main()
    except (ValueError, RuntimeError, OSError) as error:
        print(f"Stoppet: {error}")
        print("Endringer som allerede ble sendt, kan være aktive. Kontroller enheten i konsollen.")
        raise SystemExit(1)
    except KeyboardInterrupt:
        print("\nAvbrutt. Kontroller eventuelle utførte endringer i konsollen.")
        raise SystemExit(130)
