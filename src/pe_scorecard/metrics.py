"""Calculations for scorecard metrics."""
# Standard Python Libraries
import calendar
import datetime

# Third-Party Libraries
from bs4 import BeautifulSoup
import pandas as pd
import requests

from .data.db_query import (  # query_subs_https_scan,; query_iscore_vs_data_vuln,; query_iscore_pe_data_vuln,; query_iscore_pe_data_cred,; query_iscore_pe_data_breach,; query_iscore_pe_data_darkweb,; query_iscore_pe_data_protocol,; query_iscore_was_data_vuln,; query_pe_stakeholder_list,; query_kev_list,; query_was_summary,; query_cyhy_snapshots,; query_cyhy_vuln_scans,;
    query_certs_counts,
    query_cyhy_port_scans,
    query_domain_counts,
    query_https_scan,
    query_ips_counts,
    query_open_vulns,
    query_sofware_scans,
    query_sslyze_scan,
    query_trusty_mail,
    query_vuln_remediation,
    query_vuln_tickets,
    query_webapp_counts,
)

BOD1801_DMARC_RUA_URI = "mailto:reports@dmarc.cyber.dhs.gov"


class Scorecard:
    """Class to generate scorecard metrics."""

    def __init__(self, month, year, org_data, org_uid_list, cyhy_id_list):
        """Initialize scorecard class."""
        self.org_data = org_data
        self.scorecard_dict = {
            "agency_name": org_data["name"],
            "agency_id": org_data["cyhy_db_name"],
            "sector_name": "FCEB" if org_data["fceb"] is True else "Sector",
            "date": calendar.month_name[int(month)] + " " + year,
            "last_data_sent_date": "NEED TO CALCULATE",
        }
        print(self.scorecard_dict)
        start_date = datetime.date(int(year), int(month), 1)
        end_date = (start_date + datetime.timedelta(days=32)).replace(day=1)
        self.start_date = start_date
        self.end_date = end_date
        self.org_uid_list = org_uid_list
        self.cyhy_id_list = cyhy_id_list

        (self.total_ips_counts, self.discovered_ips_counts) = query_ips_counts(
            org_uid_list
        )
        self.domain_counts = query_domain_counts(org_uid_list)
        # # TODO possibly need to format a date string based on the new column
        self.webapp_counts = query_webapp_counts(start_date, org_uid_list)
        self.cert_counts = query_certs_counts()
        self.ports_data = query_cyhy_port_scans(start_date, end_date, org_uid_list)
        self.software_counts = query_sofware_scans(start_date, end_date, org_uid_list)
        print(self.software_counts)
        self.vs_vuln_counts = query_vuln_tickets(org_uid_list)
        self.vs_remediation = query_vuln_remediation(start_date, end_date, org_uid_list)
        self.vs_open_vulns = query_open_vulns(start_date, end_date, org_uid_list)
        # TODO adjust queries parameters
        self.sslyze_data = query_sslyze_scan(org_uid_list)
        self.https_data = query_https_scan(
            month,
            org_uid_list,
        )
        self.trusty_mail_data = query_trusty_mail(org_uid_list)

    def calculate_discovery_metrics_counts(self):
        """Summarize discovery findings into key metrics."""
        total_ips_df = self.total_ips_counts
        total_ips = total_ips_df["num_ips"].sum()

        discovered_ips_df = self.discovered_ips_counts
        total_identified_ips = discovered_ips_df["identified_ip_count"].sum()

        self.scorecard_dict["ips_monitored"] = total_ips
        self.scorecard_dict["ips_identified"] = total_ips - total_identified_ips

        self.scorecard_dict["domains_monitored"] = (
            self.domain_counts["identified"].sum()
            + self.domain_counts["unidentified"].sum()
        )
        self.scorecard_dict["domains_identified"] = self.domain_counts[
            "unidentified"
        ].sum()

        # TODO add webapps

        # TODO add certs

    def calculate_profiling_metrics(self):
        """Summarize profiling findings into key metrics."""
        ports_df = self.ports_data

        insecure_protocols_list = [
            "rdp",
            "telnet",
            "ftp",
            "rpc",
            "smb",
            "sql",
            "ldap",
            "irc",
            "netbios",
            "kerberos",
        ]
        services_list = ["http", "https", "http-proxy"]

        total_ports = []
        insecure_ports = []
        total_protocols = []
        insecure_protocols = []
        total_services = []

        for index2, portscan in ports_df.iterrows():

            if [portscan["ip"], portscan["port"]] not in total_ports:
                total_ports.append([portscan["ip"], portscan["port"]])
                if (
                    portscan["service_name"] in insecure_protocols_list
                    and portscan["state"] == "open"
                ):
                    insecure_ports.append([portscan["ip"], portscan["port"]])
            if [portscan["service_name"], portscan["port"]] not in total_ports:
                total_protocols.append([portscan["service_name"], portscan["port"]])
                if (
                    portscan["service_name"] in insecure_protocols_list
                    and portscan["state"] == "open"
                ):
                    insecure_protocols.append(
                        [portscan["service_name"], portscan["port"]]
                    )
            if [
                portscan["service_name"],
                portscan["port"],
            ] not in total_services and portscan["service_name"] in services_list:
                total_services.append([portscan["service_name"], portscan["port"]])

        self.scorecard_dict["ports_total_count"] = len(total_ports)
        self.scorecard_dict["ports_risky_count"] = len(insecure_ports)
        self.scorecard_dict["protocol_total_count"] = len(total_protocols)
        self.scorecard_dict["protocol_insecure_count"] = len(insecure_protocols)
        self.scorecard_dict["total_services"] = len(total_services)

        software_df = self.software_counts
        print(software_df["count"].sum())
        self.scorecard_dict["software_unsupported_count"] = software_df["count"].sum()

    def fill_scorecard_dict(self):
        """Fill dictionary with scorecard metrics."""
        self.calculate_discovery_metrics_counts()


def ocsp_exclusions():
    """Prepare a list of OCSP sites to exclude."""
    URL = (
        "https://github.com/cisagov/dotgov-data/blob/main/dotgov-websites/ocsp-crl.csv"
    )
    r = requests.get(URL)
    soup = BeautifulSoup(r.content, features="lxml")

    table = soup.find_all("table")
    df = pd.read_html(str(table))[0]

    df = df.drop(columns=[0])
    ocsp_crl = df[1].values.tolist()

    return ocsp_crl


def add_weak_crypto_data_to_domain(domain_doc, sslyze_data_all_domains):
    """Calculate weak crypto data for a given domain."""
    # Look for weak crypto data in sslyze_data_all_domains and
    # add hosts with weak crypto to
    # domain_doc['hosts_with_weak_crypto']
    domain_doc["domain_has_weak_crypto"] = False
    domain_doc["hosts_with_weak_crypto"] = []
    domain_doc["domain_has_symantec_cert"] = False

    if sslyze_data_all_domains.get(domain_doc["domain"]):
        for host in sslyze_data_all_domains[domain_doc["domain"]]:
            if host["sslv2"] or host["sslv3"] or host["any_3des"] or host["any_rc4"]:
                domain_doc["domain_has_weak_crypto"] = True
                domain_doc["hosts_with_weak_crypto"].append(host)
            if host["is_symantec_cert"]:
                domain_doc["domain_has_symantec_cert"] = True
    return domain_doc


def calculate_bod18_compliance_https(month, agency):
    """Calculate BOD 18-01 compliance percentage for https."""
    bod_1801_count = 0
    all_eligible_domains_count = 0
    ocsp_exclusion_list = ocsp_exclusions()  # TODO pull list from github

    all_domains = query_https_scan(month, agency)
    sslyze_data_all_domains = dict()
    for host in query_sslyze_scan(month, agency):
        current_host_dict = {
            "scanned_hostname": host["scanned_hostname"],
            "scanned_port": host["scanned_port"],
            "sslv2": host["sslv2"],
            "sslv3": host["sslv3"],
            "any_3des": host["any_3des"],
            "any_rc4": host["any_rc4"],
            "is_symantec_cert": host["is_symantec_cert"],
        }

        if not sslyze_data_all_domains.get(host["domain"]):
            sslyze_data_all_domains[host["domain"]] = [current_host_dict]
        else:
            sslyze_data_all_domains[host["domain"]].append(current_host_dict)

    for domain in all_domains:
        domain = add_weak_crypto_data_to_domain(domain, sslyze_data_all_domains)
        domain["ocsp_domain"] = domain["domain"] in ocsp_exclusion_list

        if domain["live"]:
            if not domain["ocsp_domain"]:
                all_eligible_domains_count += 1

        # BOD 18-01 compliant?
        if (
            (
                domain["domain_supports_https"]
                and domain["domain_enforces_https"]
                and domain["domain_uses_strong_hsts"]
            )
            or (
                domain["live"]
                and (
                    domain["hsts_base_domain_preloaded"]
                    or (
                        not domain["https_full_connection"]
                        and domain["https_client_auth_required"]
                    )
                )
            )
        ) and not domain["domain_has_weak_crypto"]:
            if not domain["ocsp_domain"]:
                bod_1801_count += 1
    bod_1801_percentage = round(bod_1801_count / all_eligible_domains_count * 100.0, 1)

    return bod_1801_percentage


def calculate_bod18_compliance_email(month, agency):
    """Calculate BOD 18-01 trusty mail compliance."""
    bod_1801_compliant_count = 0
    base_domain_plus_smtp_subdomain_count = 0

    sslyze_data_all_domains = dict()
    for host in query_sslyze_scan(month, agency):
        current_host_dict = {
            "scanned_hostname": host["scanned_hostname"],
            "scanned_port": host["scanned_port"],
            "sslv2": host["sslv2"],
            "sslv3": host["sslv3"],
            "any_3des": host["any_3des"],
            "any_rc4": host["any_rc4"],
            "is_symantec_cert": host["is_symantec_cert"],
        }

        if not sslyze_data_all_domains.get(host["domain"]):
            sslyze_data_all_domains[host["domain"]] = [current_host_dict]
        else:
            sslyze_data_all_domains[host["domain"]].append(current_host_dict)

    for domain in query_trusty_mail(month, agency):
        # domain  = add_weak_crypto_data_to_domain(domain, sslyze_data_all_domains)

        if domain["live"]:

            if domain["is_base_domain"] or (
                not domain["is_base_domain"] and domain["domain_supports_smtp"]
            ):
                base_domain_plus_smtp_subdomain_count += 1

            domain["valid_dmarc2"] = (
                domain["valid_dmarc"] or domain["valid_dmarc_base_domain"]
            )
            domain["valid_dmarc_subdomain_policy_reject"] = False
            # According to RFC7489, "'sp' will be ignored for DMARC
            # records published on subdomains of Organizational
            # Domains due to the effect of the DMARC policy discovery
            # mechanism."  Therefore we have chosen not to penalize
            # for sp!=reject when considering subdomains.
            #
            # See here for more details:
            # https://tools.ietf.org/html/rfc7489#section-6.3
            if domain["valid_dmarc2"] and (
                not domain["is_base_domain"]
                or domain["dmarc_subdomain_policy"] == "reject"
            ):
                domain["valid_dmarc_subdomain_policy_reject"] = True

            domain["valid_dmarc_policy_reject"] = False
            if domain["valid_dmarc2"] and domain["dmarc_policy"] == "reject":
                domain["valid_dmarc_policy_reject"] = True

            domain["valid_dmarc_policy_pct"] = False
            if domain["valid_dmarc2"] and domain["dmarc_policy_percentage"] == 100:
                domain["valid_dmarc_policy_pct"] = True

            domain["valid_dmarc_policy_of_reject"] = False
            if (
                domain["valid_dmarc_policy_reject"]
                and domain["valid_dmarc_subdomain_policy_reject"]
                and domain["valid_dmarc_policy_pct"]
            ):
                domain["valid_dmarc_policy_of_reject"] = True

            if domain["is_base_domain"]:
                domain["spf_covered"] = domain["valid_spf"]
            else:
                domain["spf_covered"] = domain["valid_spf"] or (
                    domain["spf_record"] is False
                    and domain["valid_dmarc_policy_of_reject"]
                )

            domain["valid_dmarc_bod1801_rua_uri"] = False
            if domain["valid_dmarc2"]:
                for uri_dict in domain["aggregate_report_uris"]:
                    if uri_dict["uri"].lower() == BOD1801_DMARC_RUA_URI.lower():
                        domain["valid_dmarc_bod1801_rua_uri"] = True
                        break

            if (
                domain["spf_covered"]
                and not domain["domain_has_weak_crypto"]
                and domain["valid_dmarc_policy_reject"]
                and domain["valid_dmarc_subdomain_policy_reject"]
                and domain["valid_dmarc_policy_pct"]
                and domain["valid_dmarc_bod1801_rua_uri"]
            ):
                bod_1801_compliant_count += 1

    bod_1801_compliant_percentage = round(
        bod_1801_compliant_count / base_domain_plus_smtp_subdomain_count * 100.0,
        1,
    )
    return bod_1801_compliant_percentage
