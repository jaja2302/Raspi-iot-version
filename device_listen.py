#!/usr/bin/env python3
"""
Device Listener for Raspberry Pi Hotspot
---------------------------------------
Memantau perangkat yang terhubung ke hotspot Wi-Fi Raspberry Pi dan
menuliskannya ke terminal serta berkas log.
"""

import argparse
import datetime
import os
import signal
import subprocess
import sys
import time
from typing import List, Set

LOG_FILE = "logs/device_listener.log"
DEFAULT_INTERFACE = "wlan0"


def ensure_log_path() -> None:
    """Pastikan direktori log tersedia."""
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)


def is_mac_address(candidate: str) -> bool:
    candidate = candidate.lower()
    if len(candidate) != 17:
        return False
    allowed = set("0123456789abcdef:")
    return all(ch in allowed for ch in candidate)


def run_command(command: List[str]) -> subprocess.CompletedProcess:
    """Jalankan perintah shell dengan timeout dan kembalikan hasilnya."""
    try:
        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except FileNotFoundError:
        return subprocess.CompletedProcess(command, returncode=127, stdout="", stderr="")
    except subprocess.TimeoutExpired:
        return subprocess.CompletedProcess(command, returncode=124, stdout="", stderr="timeout")


def clients_via_iw(interface: str) -> Set[str]:
    """Ambil daftar klien menggunakan `iw dev <iface> station dump`."""
    clients: Set[str] = set()
    result = run_command(["iw", "dev", interface, "station", "dump"])
    if result.returncode == 0 and result.stdout:
        for line in result.stdout.splitlines():
            line = line.strip()
            if line.startswith("Station "):
                parts = line.split()
                if len(parts) >= 2 and is_mac_address(parts[1]):
                    clients.add(parts[1].lower())
    return clients


def clients_via_hostapd(interface: str) -> Set[str]:
    """Ambil daftar klien menggunakan `hostapd_cli all_sta`."""
    clients: Set[str] = set()
    result = run_command(["hostapd_cli", "-i", interface, "all_sta"])
    if result.returncode == 0 and result.stdout:
        for line in result.stdout.splitlines():
            line = line.strip()
            if is_mac_address(line):
                clients.add(line.lower())
    return clients


def clients_via_arp(interface: str) -> Set[str]:
    """Ambil daftar klien dari tabel ARP lokal."""
    clients: Set[str] = set()
    result = run_command(["arp", "-a"])
    if result.returncode == 0 and result.stdout:
        for line in result.stdout.splitlines():
            parts = line.split()
            if len(parts) >= 4 and parts[3] != "<incomplete>":
                mac = parts[3].lower()
                if is_mac_address(mac) and interface in line:
                    clients.add(mac)
    return clients


def discover_clients(interface: str) -> List[str]:
    """Gabungkan hasil dari berbagai metode untuk mendeteksi klien."""
    clients = set()
    for collector in (clients_via_iw, clients_via_hostapd, clients_via_arp):
        clients.update(collector(interface))
    return sorted(clients)


def log(message: str) -> None:
    """Tulis pesan ke stdout dan file log."""
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    formatted = f"[{timestamp}] {message}"
    print(formatted)
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as fh:
            fh.write(formatted + "\n")
    except Exception as exc:
        print(f"[WARN] Gagal menulis log: {exc}", file=sys.stderr)


def listen_loop(interface: str, interval: int) -> None:
    """Loop utama untuk memantau perangkat klien."""
    last_clients: List[str] = []
    ensure_log_path()
    log(f"Memulai device listener pada interface '{interface}' (interval {interval}s)")

    try:
        while True:
            clients = discover_clients(interface)
            if clients != last_clients:
                if clients:
                    log("Klien terdeteksi:")
                    for mac in clients:
                        log(f"  - {mac}")
                else:
                    log("Tidak ada klien yang terhubung")
                last_clients = clients
            time.sleep(interval)
    except KeyboardInterrupt:
        log("Device listener dihentikan oleh pengguna")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Pemantau perangkat yang terhubung ke hotspot Raspberry Pi")
    parser.add_argument(
        "-i",
        "--interface",
        default=DEFAULT_INTERFACE,
        help="Interface Wi-Fi hotspot (default: wlan0)",
    )
    parser.add_argument(
        "-t",
        "--interval",
        type=int,
        default=15,
        help="Interval pengecekan dalam detik (default: 15)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    listen_loop(args.interface, max(1, args.interval))


if __name__ == "__main__":
    main()
