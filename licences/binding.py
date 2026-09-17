"""
licences/binding.py
===================
Collecte d'empreinte machine multi-attributs pour binding licence.

Utilisé pour générer automatiquement les attributs :
- MAC address
- hostname
- CPU ID
- disk serial
- system UUID
- OS info
- platform data
"""

import hashlib
import platform
import socket
import uuid
from typing import Dict, Optional


def get_mac_address() -> str:
    """Récupère l'adresse MAC principale."""
    try:
        mac = uuid.getnode()
        # uuid.getnode() peut retourner un random si pas de MAC trouvée
        # On formate en XX:XX:XX:XX:XX:XX
        mac_str = ':'.join(('%012X' % mac)[i:i+2] for i in range(0, 12, 2))
        return mac_str
    except Exception:
        return ''


def get_hostname() -> str:
    try:
        return socket.gethostname()
    except Exception:
        return ''


def get_cpu_id() -> str:
    """Tente de récupérer un ID CPU (best effort)."""
    try:
        # Sur Linux, lire /proc/cpuinfo
        import os
        if os.path.exists('/proc/cpuinfo'):
            with open('/proc/cpuinfo', 'r') as f:
                for line in f:
                    if 'serial' in line.lower() or 'cpu id' in line.lower() or 'model name' in line.lower():
                        # Prendre la première ligne pertinente
                        parts = line.split(':')
                        if len(parts) > 1:
                            return parts[1].strip()[:255]
        # Fallback : platform.processor()
        return platform.processor()[:255]
    except Exception:
        return ''


def get_disk_serial() -> str:
    """Tente de récupérer le serial disque système (best effort)."""
    try:
        import os
        # Linux : /sys/block/sda/device/serial ou via lsblk
        # On tente plusieurs chemins
        possible_paths = [
            '/sys/block/sda/device/serial',
            '/sys/block/vda/device/serial',
            '/sys/block/nvme0n1/device/serial',
        ]
        for path in possible_paths:
            if os.path.exists(path):
                with open(path, 'r') as f:
                    return f.read().strip()[:255]
        # Fallback : utiliser l'ID de la partition racine via blkid (si dispo)
        return ''
    except Exception:
        return ''


def get_system_uuid() -> str:
    """Tente de récupérer le System UUID (SMBIOS)."""
    try:
        import os
        # Linux : /sys/class/dmi/id/product_uuid
        path = '/sys/class/dmi/id/product_uuid'
        if os.path.exists(path):
            with open(path, 'r') as f:
                return f.read().strip()[:255]
        # Fallback : machine-id
        for p in ['/etc/machine-id', '/var/lib/dbus/machine-id']:
            if os.path.exists(p):
                with open(p, 'r') as f:
                    return f.read().strip()[:255]
        return ''
    except Exception:
        return ''


def get_os_info() -> str:
    try:
        return f"{platform.system()} {platform.release()} {platform.version()}"[:500]
    except Exception:
        return ''


def get_platform_data() -> Dict:
    try:
        return {
            'system': platform.system(),
            'release': platform.release(),
            'version': platform.version()[:200],
            'machine': platform.machine(),
            'processor': platform.processor()[:200],
            'architecture': str(platform.architecture()[0]) if platform.architecture() else '',
            'python_version': platform.python_version(),
        }
    except Exception:
        return {}


def collect_machine_fingerprint() -> Dict[str, str]:
    """
    Collecte tous les attributs machine pour binding.

    Returns:
        dict avec mac_address, hostname, cpu_id, disk_serial, system_uuid, os_info, platform_data
    """
    return {
        'mac_address': get_mac_address(),
        'hostname': get_hostname(),
        'cpu_id': get_cpu_id(),
        'disk_serial': get_disk_serial(),
        'system_uuid': get_system_uuid(),
        'os_info': get_os_info(),
        'platform_data': get_platform_data(),
        'ip_address': '',  # rempli à l'activation via request
    }


def create_activation_for_licence(licence, request=None, mode='ONLINE') -> 'LicenceActivation':
    """
    Crée une activation avec empreinte machine collectée.

    Args:
        licence: instance Licence
        request: HttpRequest optionnel pour IP et user_agent
        mode: ONLINE ou OFFLINE
    """
    from .models import LicenceActivation

    attrs = collect_machine_fingerprint()

    ip_address = None
    user_agent = ''
    if request:
        # IP
        x_forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded:
            ip_address = x_forwarded.split(',')[0].strip()
        else:
            ip_address = request.META.get('REMOTE_ADDR')
        user_agent = request.META.get('HTTP_USER_AGENT', '')[:500]

    activation = LicenceActivation(
        licence=licence,
        mac_address=attrs['mac_address'][:17] if len(attrs['mac_address']) > 17 else attrs['mac_address'],
        hostname=attrs['hostname'][:255],
        cpu_id=attrs['cpu_id'][:255],
        disk_serial=attrs['disk_serial'][:255],
        system_uuid=attrs['system_uuid'][:255],
        os_info=attrs['os_info'][:500],
        platform_data=attrs['platform_data'],
        ip_address=ip_address,
        mode_activation=mode,
        user_agent=user_agent,
        est_active=True,
    )
    activation.compute_and_sign_fingerprint()
    activation.save()
    return activation
