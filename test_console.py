"""Tester konsollrespons uten fysisk Cisco-utstyr eller pySerial."""
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location("setup", Path(__file__).parents[1] / "part1/setup_ssh.py")
setup = importlib.util.module_from_spec(spec)
spec.loader.exec_module(setup)


class FakePort:
    in_waiting = 1

    def __init__(self, responses):
        self.responses = iter(responses)
        self.output = b""
        self.sent = []

    def write(self, data):
        self.sent.append(data.decode().strip())
        self.output = next(self.responses).encode()

    def flush(self):
        pass

    def read(self, size):
        output, self.output = self.output, b""
        return output


class ConsoleTests(unittest.TestCase):
    def test_syslog_after_prompt(self):
        port = FakePort(["show ip ssh\r\nSSH Enabled - version 2.0\r\nR2#*Oct 14: log\r\n"])
        self.assertIn("SSH Enabled", setup.Console(port).command("show ip ssh"))

    def test_domain_fallback_consumes_rejected_prompt(self):
        port = FakePort(["% Invalid input detected\r\nR2(config)#",
                         "R2(config)#"])
        setup.Console(port).configure_command("ip domain-name lab.local")
        self.assertEqual(port.sent, ["ip domain-name lab.local", "ip domain name lab.local"])

    def test_other_errors_do_not_retry(self):
        port = FakePort(["% Error configuring domain\r\nR2(config)#"])
        with self.assertRaises(RuntimeError):
            setup.Console(port).configure_command("ip domain-name lab.local")
        self.assertEqual(len(port.sent), 1)

    def test_timeout_reports_command_without_secret(self):
        port = FakePort([""])
        console = setup.Console(port)
        with patch.object(console, "expect", side_effect=RuntimeError("timeout")):
            with self.assertRaisesRegex(RuntimeError, "enable secret <skjult>") as result:
                console.command("enable secret testpassword")
        self.assertNotIn("testpassword", str(result.exception))

    def test_masking_preserves_username_and_command(self):
        self.assertEqual(setup.safe_command("username admin privilege 15 secret admin"),
                         "username admin privilege 15 secret <skjult>")


if __name__ == "__main__":
    unittest.main()
