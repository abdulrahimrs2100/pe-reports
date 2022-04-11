"""Script for querying the Shodan API."""

# Standard Python Libraries
import datetime
import logging
import time

# Third-Party Libraries
import pandas as pd
import requests
import shodan

# cisagov Libraries
from pe_source.data.pe_db.db_query import (
    get_data_source_uid,
    get_ips,
    insert_shodan_data,
)


def run_shodan_thread(api, org_chunk, thread_name):
    """Run a Shodan thread."""
    failed = []
    for org in org_chunk:
        org_name = org[2]
        org_uid = org[0]
        logging.info("{} Running IPs for {}".format(thread_name, org_name))
        start, end = get_dates()
        try:
            ips = get_ips(org_uid)
        except Exception as e:
            logging.error(
                "{} Failed fetching IPs for {}.".format(thread_name, org_name)
            )
            logging.error("{} {} - {}".format(thread_name, e, org_name))
            failed.append("{} fetching IPs".format(org_name))
            continue

        if len(ips) == 0:
            logging.error("{} No IPs for {}.".format(thread_name, org_name))
            failed.append("{} has 0 IPs".format(org_name))
            continue

        failed = search_shodan(
            thread_name, ips, api, start, end, org_uid, org_name, failed
        )

    if len(failed) > 0:
        logging.critical("{} Failures: {}".format(thread_name, failed))


def get_dates():
    """Get dates for the query."""
    now = datetime.datetime.now()
    days_back = datetime.timedelta(days=30)
    days_forward = datetime.timedelta(days=1)
    start = now - days_back
    end = now + days_forward
    start_time = time_to_utc(start)
    end_time = time_to_utc(end)
    return start_time, end_time


def time_to_utc(in_time):
    """Convert time to UTC."""
    # If time does not have timezone info, assume it is local
    if in_time.tzinfo is None:
        local_tz = datetime.datetime.now().astimezone().tzinfo
        in_time = in_time.replace(tzinfo=local_tz)
    utc_time = in_time.astimezone(datetime.timezone.utc)
    return utc_time


def search_circl(cve):
    """Fetch CVE info from Circl."""
    re = requests.get(f"https://cve.circl.lu/api/cve/{cve}")
    return re


def search_shodan(thread_name, ips, api, start, end, org_uid, org_name, failed):
    """Search IPs in the Shodan API."""
    # Initialize lists to store Shodan results
    data = []
    risk_data = []
    vuln_data = []

    # Build dictionaries for naming conventions and definitions
    risky_ports, name_dict, risk_dict, av_dict, ac_dict, ci_dict = get_shodan_dicts()

    # Break up IPs into chunks of 100
    # Throws flake8 E203 error which is ignored in .flake8
    ip_chunks = [ips[i : i + 100] for i in range(0, len(ips), 100)]
    tot_ips = len(ips)
    tot = len(ip_chunks)
    logging.info(
        "{} Split {} IPs into {} chunks - {}".format(
            thread_name, tot_ips, tot, org_name
        )
    )

    # Loop through chunks and search Shodan
    for i, ip_chunk in enumerate(ip_chunks):
        try_count = 1
        while try_count < 7:
            try:
                results = api.host(ip_chunk, history=True)
                for r in results:
                    for d in r["data"]:
                        # Convert Shodan date string to UTC datetime
                        shodan_datetime = datetime.datetime.strptime(
                            d["timestamp"], "%Y-%m-%dT%H:%M:%S.%f"
                        )
                        shodan_utc = time_to_utc(shodan_datetime)
                        # Only include results in the timeframe
                        if shodan_utc > start and shodan_utc < end:
                            prod = d.get("product", None)
                            serv = d.get("http", {}).get("server")
                            asn = d.get("ASN", None)
                            vulns = d.get("vulns", None)
                            if vulns is not None:
                                cves = list(vulns.keys())
                                unverified = []
                                for cve in cves:
                                    # Check if CVEs are verified
                                    unverified, vuln_data = is_verified(
                                        vulns,
                                        cve,
                                        av_dict,
                                        ac_dict,
                                        ci_dict,
                                        vuln_data,
                                        org_uid,
                                        r,
                                        d,
                                        asn,
                                        unverified,
                                    )
                                if len(unverified) > 0:
                                    ftype = "Pontentially Vulnerable Product"
                                    name = prod
                                    risk = unverified
                                    mitigation = "Verify asset is up to date, supported by the vendor, and configured securely"
                                    risk_data.append(
                                        [
                                            org_uid,
                                            r["org"],
                                            r["ip_str"],
                                            d["port"],
                                            d["_shodan"]["module"],
                                            ftype,
                                            name,
                                            risk,
                                            mitigation,
                                            d["timestamp"],
                                            prod,
                                            serv,
                                            r["tags"],
                                            r["domains"],
                                            r["hostnames"],
                                            r["isp"],
                                            asn,
                                        ]
                                    )
                            elif d["_shodan"]["module"] in risky_ports:
                                ftype = "Insecure Protocol"
                                name = name_dict[d["_shodan"]["module"]]
                                risk = [risk_dict[d["_shodan"]["module"]]]
                                mitigation = "Confirm open port has a required business use for internet exposure and ensure necessary safeguards are in place through TCP wrapping, TLS encryption, or authentication requirements"
                                risk_data.append(
                                    [
                                        org_uid,
                                        r["org"],
                                        r["ip_str"],
                                        d["port"],
                                        d["_shodan"]["module"],
                                        ftype,
                                        name,
                                        risk,
                                        mitigation,
                                        d["timestamp"],
                                        prod,
                                        serv,
                                        r["tags"],
                                        r["domains"],
                                        r["hostnames"],
                                        r["isp"],
                                        asn,
                                    ]
                                )
                            data.append(
                                [
                                    org_uid,
                                    r["org"],
                                    r["ip_str"],
                                    d["port"],
                                    d["_shodan"]["module"],
                                    d["timestamp"],
                                    prod,
                                    serv,
                                    r["tags"],
                                    r["domains"],
                                    r["hostnames"],
                                    r["isp"],
                                    asn,
                                ]
                            )
                time.sleep(1)
                break
            except shodan.APIError as e:
                if try_count == 5:
                    logging.error(
                        "{} Failed 5 times. Continuing to next chunk - {}".format(
                            thread_name, org_name
                        )
                    )
                    failed.append(
                        "{} chunk {} failed 5 times and skipped".format(org_name, i + 1)
                    )
                    break
                logging.error("{} {} - {}".format(thread_name, e, org_name))
                logging.error(
                    "{} Try #{} failed. Calling the API again. - {}".format(
                        thread_name, try_count, org_name
                    )
                )
                try_count += 1
                # Most likely too many API calls per second so sleep
                time.sleep(5)
            except Exception as e:
                logging.error("{} {} - {}".format(thread_name, e, org_name))
                logging.error(
                    "{} Not a shodan API error. Continuing to next chunk - {}".format(
                        thread_name, org_name
                    )
                )
                failed.append("{} chunk {} failed and skipped".format(org_name, i + 1))
                break

        count = i + 1
        logging.info("{} {}/{} complete - {}".format(thread_name, count, tot, org_name))

    df = pd.DataFrame(
        data,
        columns=[
            "organizations_uid",
            "organization",
            "ip",
            "port",
            "protocol",
            "timestamp",
            "product",
            "server",
            "tags",
            "domains",
            "hostnames",
            "isn",
            "asn",
        ],
    )
    risk_df = pd.DataFrame(
        risk_data,
        columns=[
            "organizations_uid",
            "organization",
            "ip",
            "port",
            "protocol",
            "type",
            "name",
            "potential_vulns",
            "mitigation",
            "timestamp",
            "product",
            "server",
            "tags",
            "domains",
            "hostnames",
            "isn",
            "asn",
        ],
    )
    vuln_df = pd.DataFrame(
        vuln_data,
        columns=[
            "organizations_uid",
            "organization",
            "ip",
            "port",
            "protocol",
            "timestamp",
            "cve",
            "severity",
            "cvss",
            "summary",
            "product",
            "attack_vector",
            "av_description",
            "attack_complexity",
            "ac_description",
            "confidentiality_impact",
            "ci_description",
            "integrity_impact",
            "ii_Description",
            "availability_impact",
            "ai_description",
            "tags",
            "domains",
            "hostnames",
            "isn",
            "asn",
        ],
    )

    # Grab the data source uid and add to each dataframe
    source_uid = get_data_source_uid("Shodan")
    df["data_source_uid"] = source_uid
    risk_df["data_source_uid"] = source_uid
    vuln_df["data_source_uid"] = source_uid

    # Insert data into the PE database
    failed = insert_shodan_data(df, "shodan_assets", thread_name, org_name, failed)
    failed = insert_shodan_data(
        risk_df,
        "shodan_insecure_protocols_unverified_vulns",
        thread_name,
        org_name,
        failed,
    )
    failed = insert_shodan_data(
        vuln_df, "shodan_verified_vulns", thread_name, org_name, failed
    )

    return failed


def is_verified(
    vulns, cve, av_dict, ac_dict, ci_dict, vuln_data, org_uid, r, d, asn, unverified
):
    """Check if a CVE is verified."""
    v = vulns[cve]
    if v["verified"]:
        re = search_circl(cve)
        r_json = re.json()
        if r_json is not None:
            summary = r_json.get("summary", None)
            product = r_json.get("vulnerable_product", None)
            attack_vector = r_json.get("access", {}).get("vector")
            av = av_dict.get(attack_vector, None)
            attack_complexity = r_json.get("access", {}).get("complexity")
            ac = ac_dict.get(attack_complexity, None)
            conf_imp = r_json.get("impact", {}).get("confidentiality")
            ci = ci_dict.get(conf_imp, None)
            int_imp = r_json.get("impact", {}).get("integrity")
            ii = ci_dict.get(int_imp, None)
            avail_imp = r_json.get("impact", {}).get("availability")
            ai = ci_dict.get(avail_imp, None)
            cvss = r_json.get("cvss", None)
            if cvss == 10:
                severity = "Critical"
            elif cvss >= 7:
                severity = "High"
            elif cvss >= 4:
                severity = "Medium"
            elif cvss > 0:
                severity = "Low"
            else:
                severity = None
        else:
            # Set cve info to null if Circl has no results
            summary = ""
            product = ""
            attack_vector = ""
            av = ""
            attack_complexity = ""
            ac = ""
            conf_imp = ""
            ci = ""
            int_imp = ""
            ii = ""
            avail_imp = ""
            ai = ""
            severity = ""
            cvss = None
        vuln_data.append(
            [
                org_uid,
                r["org"],
                r["ip_str"],
                d["port"],
                d["_shodan"]["module"],
                d["timestamp"],
                cve,
                severity,
                cvss,
                summary,
                product,
                attack_vector,
                av,
                attack_complexity,
                ac,
                conf_imp,
                ci,
                int_imp,
                ii,
                avail_imp,
                ai,
                r["tags"],
                r["domains"],
                r["hostnames"],
                r["isp"],
                asn,
            ]
        )
    else:
        unverified.append(cve)

    return unverified, vuln_data


def get_shodan_dicts():
    """Build Shodan dictionaries that hold definitions and naming conventions."""
    risky_ports = [
        "ftp",
        "telnet",
        "http",
        "smtp",
        "pop3",
        "imap",
        "netbios",
        "snmp",
        "ldap",
        "smb",
        "sip",
        "rdp",
        "vnc",
        "kerberos",
    ]
    name_dict = {
        "ftp": "File Transfer Protocol",
        "telnet": "Telnet",
        "http": "Hypertext Transfer Protocol",
        "smtp": "Simple Mail Transfer Protocol",
        "pop3": "Post Office Protocol 3",
        "imap": "Internet Message Access Protocol",
        "netbios": "Network Basic Input/Output System",
        "snmp": "Simple Network Management Protocol",
        "ldap": "Lightweight Directory Access Protocol",
        "smb": "Server Message Block",
        "sip": "Session Initiation Protocol",
        "rdp": "Remote Desktop Protocol",
        "kerberos": "Kerberos",
    }
    risk_dict = {
        "ftp": "FTP",
        "telnet": "Telnet",
        "http": "HTTP",
        "smtp": "SMTP",
        "pop3": "POP3",
        "imap": "IMAP",
        "netbios": "NetBIOS",
        "snmp": "SNMP",
        "ldap": "LDAP",
        "smb": "SMB",
        "sip": "SIP",
        "rdp": "RDP",
        "vnc": "VNC",
        "kerberos": "Kerberos",
    }
    # Create dictionaries for CVSSv2 vector definitions using https://nvd.nist.gov/vuln-metrics/cvss/v3-calculator
    av_dict = {
        "NETWORK": "A vulnerability exploitable with network access means the vulnerable software is bound to the network stack and the attacker does not require local network access or local access. Such a vulnerability is often termed “remotely exploitable”. An example of a network attack is an RPC buffer overflow.",
        "ADJACENT_NETWORK": "A vulnerability exploitable with adjacent network access requires the attacker to have access to either the broadcast or collision domain of the vulnerable software. Examples of local networks include local IP subnet, Bluetooth, IEEE 802.11, and local Ethernet segment.",
        "LOCAL": "A vulnerability exploitable with only local access requires the attacker to have either physical access to the vulnerable system or a local (shell) account. Examples of locally exploitable vulnerabilities are peripheral attacks such as Firewire/USB DMA attacks, and local privilege escalations (e.g., sudo).",
    }
    ac_dict = {
        "LOW": "Specialized access conditions or extenuating circumstances do not exist. The following are examples: The affected product typically requires access to a wide range of systems and users, possibly anonymous and untrusted (e.g., Internet-facing web or mail server). The affected configuration is default or ubiquitous. The attack can be performed manually and requires little skill or additional information gathering. The 'race condition' is a lazy one (i.e., it is technically a race but easily winnable).",
        "MEDIUM": "The access conditions are somewhat specialized; the following are examples: The attacking party is limited to a group of systems or users at some level of authorization, possibly untrusted. Some information must be gathered before a successful attack can be launched. The affected configuration is non-default, and is not commonly configured (e.g., a vulnerability present when a server performs user account authentication via a specific scheme, but not present for another authentication scheme). The attack requires a small amount of social engineering that might occasionally fool cautious users (e.g., phishing attacks that modify a web browser’s status bar to show a false link, having to be on someone’s “buddy” list before sending an IM exploit).",
        "HIGH": "Specialized access conditions exist. For example, in most configurations, the attacking party must already have elevated privileges or spoof additional systems in addition to the attacking system (e.g., DNS hijacking). The attack depends on social engineering methods that would be easily detected by knowledgeable people. For example, the victim must perform several suspicious or atypical actions. The vulnerable configuration is seen very rarely in practice. If a race condition exists, the window is very narrow.",
    }
    ci_dict = {
        "NONE": "There is no impact to the confidentiality of the system",
        "PARTIAL": "There is considerable informational disclosure. Access to some system files is possible, but the attacker does not have control over what is obtained, or the scope of the loss is constrained. An example is a vulnerability that divulges only certain tables in a database.",
        "COMPLETE": "There is total information disclosure, resulting in all system files being revealed. The attacker is able to read all of the system's data (memory, files, etc.).",
    }
    return risky_ports, name_dict, risk_dict, av_dict, ac_dict, ci_dict
