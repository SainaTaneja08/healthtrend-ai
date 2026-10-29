# IDCCN: Packet Tracer Practical

## Topology (two LANs joined by one router)
```
PC1 ─┐
PC2 ─┼─ Switch0 ── G0/0 [Router0] G0/1 ── Switch1 ── Server0 (HealthTrend host)
PC3 ─┘
```
Devices: 3 PCs, 2 switches (2960), 1 router (2911), 1 server, straight-through cables.

## IP plan
| Device | Interface | IP | Mask | Gateway |
|---|---|---|---|---|
| Router0 | G0/0 | 192.168.10.1 | 255.255.255.0 | - |
| Router0 | G0/1 | 192.168.20.1 | 255.255.255.0 | - |
| PC1 | NIC | 192.168.10.10 | 255.255.255.0 | 192.168.10.1 |
| PC2 | NIC | 192.168.10.11 | 255.255.255.0 | 192.168.10.1 |
| PC3 | NIC | 192.168.10.12 | 255.255.255.0 | 192.168.10.1 |
| Server0 | NIC | 192.168.20.10 | 255.255.255.0 | 192.168.20.1 |

## Router config (CLI)
```
enable
configure terminal
hostname R0
interface g0/0
 ip address 192.168.10.1 255.255.255.0
 no shutdown
interface g0/1
 ip address 192.168.20.1 255.255.255.0
 no shutdown
end
write memory
```
Both networks are directly connected, so no static routes are needed.

## Tests to screenshot
1. `ping 192.168.10.1` from PC1 (gateway).
2. `ping 192.168.20.10` from PC1 (across the router to the server).
3. Server0 > Services > HTTP ON; edit index.html to say "HealthTrend AI"; open `http://192.168.20.10` in PC1 Web Browser.
4. `show ip route` and `show ip interface brief` on the router.
5. Optional: Simulation mode capture of an HTTP request (shows TCP/IP, ARP, DNS-free path).

## Link to the Flask app
Packet Tracer cannot run Flask. Show that the server role is the same: the real app listens on port 5000 (`0.0.0.0`), clients send HTTP GET/POST, and `tests/test_api.py` proves valid, missing, invalid input and availability.
