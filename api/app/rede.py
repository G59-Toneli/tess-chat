"""Barreira de SSRF comum: URL que o servidor busca só vai para endereço público (MCP e web_fetch)."""

import asyncio
import ipaddress

IP = ipaddress.IPv4Address | ipaddress.IPv6Address


async def resolver_ips(host: str, porta: int) -> list[str]:
    """IPs do host pelo DNS. Os testes trocam para não depender de rede."""
    infos = await asyncio.get_running_loop().getaddrinfo(host, porta)
    return [i[4][0].split("%")[0] for i in infos]


# REVISAR(human): todo IP que o host resolve precisa ser público (`is_global` recusa privado,
# loopback, link-local 169.254 da metadata, reservado). Checa TODOS os IPs: um host com um IP
# público e um interno passaria se olhasse só o primeiro. IPv6 com IPv4 embutido vale pelo IPv4.
async def ip_interno(host: str, porta: int) -> IP | None:
    """Primeiro IP não público do host, ou None. Levanta OSError se o host não resolve."""
    try:
        ips = [ipaddress.ip_address(host)]
    except ValueError:
        ips = [ipaddress.ip_address(i) for i in await resolver_ips(host, porta)]
    for ip in ips:
        real = ip.ipv4_mapped if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped else ip
        if not real.is_global:
            return real
    return None
