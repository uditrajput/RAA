---
name: raa-nmap-vulners
description: Automated CVE, CVSS, and Exploit-DB correlation against mobile backend services using Nmap and the vulnersCom/nmap-vulners NSE script.
version: 1.0.0
category: security
tools: [api_list_operations, security_scan_static, tool_manager_download]
---

# Backend CVE & Exploit Correlation (Nmap-Vulners)

Scan authorized mobile backend endpoints and correlate detected service/CPE versions against live CVE, CVSS, and Exploit-DB feeds using **nmap-vulners** (`https://github.com/vulnersCom/nmap-vulners`).

## Upstream Reference
- **Repository:** `https://github.com/vulnersCom/nmap-vulners`
- **Tool ID:** `nmap-vulners` (installable via RAA Tools Manager)

## Workflow
1. Scope authorized backend hosts/ports discovered via `api_list_operations` or passive Smap triage.
2. Execute version detection with the Vulners NSE script (`nmap -sV --script vulners --script-args mincvss=5.0 <target>`).
3. Prioritize high/critical CVSS findings and attach matching CVE IDs and Exploit-DB references to the RAA audit report.
