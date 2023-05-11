# Third-Party Libraries
import numpy as np
import pandas as pd
import psycopg2
from psycopg2 import OperationalError
from psycopg2.extensions import AsIs
import psycopg2.extras as extras
from sshtunnel import SSHTunnelForwarder
import logging
from datetime import datetime
from datetime import timezone

# from .config import config, staging_config
# cisagov Libraries
from pe_reports.data.db_query import (
    connect,
    close
)

LOGGER = logging.getLogger(__name__)

def get_tracking_score(report_period_year, report_period_month):
    last_month = get_last_month(report_period_year, report_period_month)
    this_month = datetime(report_period_year, report_period_month, 1)
    next_month = get_next_month(report_period_year, report_period_month)
    df_orgs = get_stakeholders()
    conditions = [df_orgs['total_ips'] <= 100, (df_orgs['total_ips'] > 100) & (df_orgs['total_ips'] <= 1000), (df_orgs['total_ips'] > 1000) & (df_orgs['total_ips'] <= 10000), (df_orgs['total_ips'] > 10000) & (df_orgs['total_ips'] <= 100000), df_orgs['total_ips'] > 100000]
    groups = ["XS", "S", "M", "L", "XL"]
    df_orgs["group"] = np.select(conditions, groups)

    df_bod_18 = summarize_bod_18(df_orgs)
    df_bod_19_22 = get_bod_19_22(df_orgs)
    df_was_bod_19 = summarize_was_bod_19(df_orgs, this_month, next_month)
    df_vs_attr = summarize_vs_attr(df_orgs, this_month, next_month)
    df_was_atr = summarize_was_attr(df_orgs, this_month, next_month)
    
    #Data before Normalization
    df_pe_vulns = summarize_pe_vuln_counts(df_orgs, last_month, this_month, next_month)
    df_vs_vulns = summarize_vs_vuln_counts(df_orgs, this_month)
    df_was_vulns = summarize_was_vuln_counts(df_orgs, last_month, this_month, next_month)
    df_ports_prot= summarize_port_scans(df_orgs, last_month, this_month, next_month)

    #Data after Normalization
    df_norm_vs_vulns = normalize_vulns(df_vs_vulns, "VS")
    df_norm_was_vulns = normalize_vulns(df_was_vulns, "WAS")
    df_norm_pe_vulns = normalize_vulns(df_pe_vulns, "PE")
    df_norm_ports_prot = normalize_port_scans(df_ports_prot)

    tracking_score_list = []
    for index, org in df_orgs.iterrows():
        org_id = org['organizations_uid']

        df_bod_18_org = df_bod_18.loc[df_bod_18['organizations_uid'] == org_id]
        bod_18_email = (100 - df_bod_18_org['email_bod_compliance']) * .125
        bod_18_web = (100 - df_bod_18_org['web_bod_compliance']) * .125

        vs_df_bod_19_22_org = df_bod_19_22.loc[df_bod_19_22['organizations_uid'] == org_id]
        vs_bod_22_kevs = (100 - vs_df_bod_19_22_org['percent_compliance_kevs']) * .25
        vs_bod_19_crits = (100 - vs_df_bod_19_22_org['percent_compliance_crits']) * .2
        vs_bod_19_highs = (100 - vs_df_bod_19_22_org['percent_compliance_highs']) * .15
        vs_bod_19_meds = (100 - vs_df_bod_19_22_org['percent_compliance_meds']) * .1
        vs_bod_19_lows = (100 - vs_df_bod_19_22_org['percent_compliance_lows']) * .05

        vs_overdue_vuln_section = (float(bod_18_email) + float(bod_18_web) + float(vs_bod_22_kevs) + float(vs_bod_19_crits) + float(vs_bod_19_highs) + float(vs_bod_19_meds) + float(vs_bod_19_lows)) * .5

        df_vs_attr_org = df_vs_attr.loc[df_vs_attr['organizations_uid'] == org_id]
        vs_attr_kevs = (100 - df_vs_attr_org['attr_kevs']) * .4
        vs_attr_crits = (100 - df_vs_attr_org['attr_crits']) * .35
        vs_attr_highs = (100 - df_vs_attr_org['attr_highs']) * .25

        vs_attr_section = (vs_attr_kevs + vs_attr_crits + vs_attr_highs) * .25

        df_vs_vulns_org = df_norm_vs_vulns.loc[df_norm_vs_vulns['organizations_uid'] == org_id]
        vs_kevs = (100 - df_vs_vulns_org['norm_kevs']) * .2
        vs_crits = (100 - df_vs_vulns_org['norm_crits']) * .15
        vs_highs = (100 - df_vs_vulns_org['norm_highs']) * .1
        vs_meds = (100 - df_vs_vulns_org['norm_meds']) * .08
        vs_lows = (100 - df_vs_vulns_org['norm_lows']) * .05

        df_vs_ports_org = df_norm_ports_prot.loc[df_norm_ports_prot['organizations_uid'] == org_id]
        vs_ports = (100 - df_vs_ports_org['norm_ports']) * .14
        vs_protocols = (100 - df_vs_ports_org['norm_protocols']) * .14
        vs_services = (100 - df_vs_ports_org['norm_services']) * .14

        vs_historical_trend_section = (vs_kevs + vs_crits + vs_highs + vs_meds + vs_lows + vs_ports + vs_protocols + vs_services) * .25
        
        df_pe_vulns_org = df_norm_pe_vulns.loc[df_norm_pe_vulns['organizations_uid'] == org_id]
        pe_kevs = (100 - df_pe_vulns_org['norm_kevs']) * .2
        pe_crits = (100 - df_pe_vulns_org['norm_crits']) * .15
        pe_highs = (100 - df_pe_vulns_org['norm_highs']) * .1
        pe_meds = (100 - df_pe_vulns_org['norm_meds']) * .08
        pe_lows = (100 - df_pe_vulns_org['norm_lows']) * .05

        pe_historical_trend_section = (pe_kevs + pe_crits + pe_highs + pe_meds + pe_lows)

        df_was_vulns_org = df_norm_was_vulns.loc[df_norm_was_vulns['organizations_uid'] == org_id]
        was_crits = (100 - df_was_vulns_org['norm_crits']) * .4
        was_highs = (100 - df_was_vulns_org['norm_highs']) * .3
        was_meds = (100 - df_was_vulns_org['norm_meds']) * .2
        was_lows = (100 - df_was_vulns_org['norm_lows']) * .1

        was_historical_trend_section = (was_crits + was_highs + was_meds + was_lows) * .25

        df_was_bod_19_org = df_was_bod_19.loc[df_was_bod_19['organizations_uid'] == org_id]
        was_bod_19_crits = (100 - df_was_bod_19_org['percent_compliance_crits']) * .4
        was_bod_19_highs = (100 - df_was_bod_19_org['percent_compliance_highs']) * .3
        was_bod_19_meds = (100 - df_was_bod_19_org['percent_compliance_meds']) * .2
        was_bod_19_lows = (100 - df_was_bod_19_org['percent_compliance_lows']) * .1
        
        was_overdue_vuln_section = (was_bod_19_crits + was_bod_19_highs + was_bod_19_meds + was_bod_19_lows) * .5

        df_was_attr_org = df_was_atr.loc[df_was_atr['organizations_uid'] == org_id]
        was_attr_crits = (100 - df_was_attr_org['attr_compl_crits']) * .55
        was_attr_highs = (100 - df_was_attr_org['attr_compl_highs']) * .45

        was_attr_section = (was_attr_crits + was_attr_highs) * .25

        vs_section = (vs_attr_section + vs_overdue_vuln_section + vs_historical_trend_section) * .5
        pe_section = pe_historical_trend_section * .2
        was_section = (was_attr_section + was_overdue_vuln_section + was_historical_trend_section) * .3
        metrics_aggregation = float(pe_section) + float(was_section) + float(vs_section)
        tracking_score = 100.0 - metrics_aggregation
        rescaled_tracking_score = round((tracking_score * .4) + 60.0, 2)
        tracking_score_list.append([org['organizations_uid'], org['cyhy_db_name'], rescaled_tracking_score, get_letter_grade(rescaled_tracking_score)])
    df_tracking_score = pd.DataFrame(tracking_score_list, columns= ["organizations_uid", "cyhy_db_name", "tracking_score", "letter_grade"])   

    return df_tracking_score

def get_stakeholders():
    conn = connect()
    try:
        sql = """select mvfti.organizations_uid, mvfti.cyhy_db_name, mvfti.total_ips, o.fceb, o.report_on 
        from mat_vw_fceb_total_ips mvfti 
        inner join organizations o on 
        o.organizations_uid = mvfti.organizations_uid 
        where o.fceb = true"""
        fceb_orgs_df = pd.read_sql(sql, conn)
        return fceb_orgs_df
    except (Exception, psycopg2.DatabaseError) as error:
        LOGGER.error("There was a problem with your database query %s", error)
    finally:
        if conn is not None:
            close(conn)

def get_was_stakeholders():
    conn = connect()
    try:
        sql = """select o.organizations_uid, o.cyhy_db_name, wm.was_org_id, o.fceb, o.fceb_child, o.parent_org_uid 
        from organizations o
        right join was_map wm on
        o.organizations_uid = wm.pe_org_id 
        where o.fceb = true or o.fceb_child  = true"""
        fceb_orgs_df = pd.read_sql(sql, conn)
        return fceb_orgs_df
    except (Exception, psycopg2.DatabaseError) as error:
        LOGGER.error("There was a problem with your database query %s", error)
    finally:
        if conn is not None:
            close(conn)

def get_bod_18():
    conn = connect()
    try:
        sql = """SELECT o.organizations_uid, o.cyhy_db_name, o.fceb, o.fceb_child, sss.email_compliance_pct, sss.https_compliance_pct 
		FROM scorecard_summary_stats sss
        left join organizations o on 
        sss.organizations_uid = o.organizations_uid
        where sss.email_compliance_pct notnull and sss.https_compliance_pct  notnull"""
        bod_18_df = pd.read_sql(sql, conn)
        return bod_18_df
    except (Exception, psycopg2.DatabaseError) as error:
        LOGGER.error("There was a problem with your database query %s", error)
    finally:
        if conn is not None:
            close(conn) 

def get_ports_protocols(start_date, end_date):
    conn = connect()
    try:
        sql = """select mvcpc.organizations_uid, mvcpc.cyhy_db_name, mvcpc.report_period, mvcpc.ports, mvcpc.risky_ports, mvcpc2.protocols, mvcrpc.risky_protocols, o.parent_org_uid  
        from mat_vw_cyhy_port_counts mvcpc 
        inner join mat_vw_cyhy_protocol_counts mvcpc2 on
        mvcpc2.organizations_uid  = mvcpc.organizations_uid
        inner join mat_vw_cyhy_risky_protocol_counts mvcrpc on
        mvcrpc.organizations_uid  = mvcpc.organizations_uid
        inner join organizations o on 
        o.organizations_uid = mvcpc.organizations_uid 
        where mvcpc.report_period between %(start_date)s AND %(end_date)s"""
        df_port_scans = pd.read_sql(sql, conn, params={"start_date": start_date, "end_date": end_date})
        return df_port_scans
    except (Exception, psycopg2.DatabaseError) as error:
        LOGGER.error("There was a problem with your database query %s", error)
    finally:
        if conn is not None:
            close(conn) 

def get_pe_vulns(start_date, end_date):
    conn = connect()
    try:
        sql = """select o.cyhy_db_name, o.organizations_uid, o.parent_org_uid, vsv."timestamp", vsv.cve, vsv.cvss
        from vw_shodanvulns_verified vsv 
        left join organizations o on
        o.organizations_uid = vsv.organizations_uid
        where (o.fceb = true or o.fceb_child = true) and vsv."timestamp" BETWEEN %(start_date)s AND %(end_date)s"""
        pe_vulns_df = pd.read_sql(sql, conn, params={"start_date": start_date, "end_date": end_date})
        return pe_vulns_df
    except (Exception, psycopg2.DatabaseError) as error:
        LOGGER.error("There was a problem with your database query %s", error)
    finally:
        if conn is not None:
            close(conn)  

def get_kevs():
    conn = connect()
    try:
        sql = """select kev from cyhy_kevs"""
        kevs_df = pd.read_sql(sql, conn)
        return kevs_df
    except (Exception, psycopg2.DatabaseError) as error:
        LOGGER.error("There was a problem with your database query %s", error)
    finally:
        if conn is not None:
            close(conn) 

def get_vs_open_vulns():
    conn = connect()
    try:
        sql = """select o.cyhy_db_name, o.organizations_uid, o.parent_org_uid, ct.cve, ct.cvss_base_score, ct.time_opened 
        from cyhy_tickets ct 
        left join organizations o on 
        ct.organizations_uid = o.organizations_uid
        where ct.false_positive = 'false' and ct.cvss_base_score != 'NaN' and (o.fceb = true  or o.fceb_child = true) and ct.time_closed is null"""
        vs_open_vulns_df = pd.read_sql(sql, conn)
        return vs_open_vulns_df
    except (Exception, psycopg2.DatabaseError) as error:
        LOGGER.error("There was a problem with your database query %s", error)
    finally:
        if conn is not None:
            close(conn)

def get_vs_closed_vulns(start_date, end_date):
    conn = connect()
    try:
        sql = """select o.cyhy_db_name, o.organizations_uid, o.parent_org_uid, ct.cve, ct.cvss_base_score, ct.time_opened, ct.time_closed
        from cyhy_tickets ct 
        left join organizations o on 
        ct.organizations_uid = o.organizations_uid
        where ct.false_positive = 'false' and ct.cvss_base_score != 'NaN' and (o.fceb = true  or o.fceb_child = true) and (ct.time_closed between %(start_date)s and %(end_date)s)"""
        vs_open_vulns_df = pd.read_sql(sql, conn, params={"start_date": start_date, "end_date": end_date})
        return vs_open_vulns_df
    except (Exception, psycopg2.DatabaseError) as error:
        LOGGER.error("There was a problem with your database query %s", error)
    finally:
        if conn is not None:
            close(conn)

def get_was_open_vulns(start_date, end_date):
    conn = connect()
    try:
        sql = """select wf.was_org_id, wm.pe_org_id, wf.base_score, wf.fstatus, wf.last_detected, wf.first_detected 
        from was_findings wf 
        left join was_map wm on
        wf.was_org_id = wm.was_org_id 
        where (wf.last_detected between %(start_date)s and %(end_date)s) and wf.fstatus != 'FIXED' and wm.pe_org_id notnull"""
        was_open_vulns_df = pd.read_sql(sql, conn, params={"start_date": start_date, "end_date": end_date})
        return was_open_vulns_df
    except (Exception, psycopg2.DatabaseError) as error:
        LOGGER.error("There was a problem with your database query %s", error)
    finally:
        if conn is not None:
            close(conn)

def get_was_closed_vulns(start_date, end_date):
    conn = connect()
    try:
        sql = """select wf.was_org_id, wm.pe_org_id ,wf.base_score, wf.fstatus, wf.last_detected, wf.first_detected 
        from was_findings wf 
        left join was_map wm on
        wf.was_org_id = wm.was_org_id 
        where (wf.last_detected between %(start_date)s and %(end_date)s) and wf.fstatus = 'FIXED' and wm.pe_org_id notnull"""
        was_open_vulns_df = pd.read_sql(sql, conn, params={"start_date": start_date, "end_date": end_date})
        return was_open_vulns_df
    except (Exception, psycopg2.DatabaseError) as error:
        LOGGER.error("There was a problem with your database query %s", error)
    finally:
        if conn is not None:
            close(conn)

def summarize_vs_attr(orgs_df, this_month, next_month):
    df_closed_vulns = get_vs_closed_vulns(this_month, next_month)
    kevs_df = get_kevs()
    average_time_to_remediate_list = []
    for index, org in orgs_df.iterrows():
        org_kevs = []
        org_crits = []
        org_highs = []
        for index2, vuln in df_closed_vulns.iterrows():
            if org['organizations_uid'] == vuln['organizations_uid'] or org['organizations_uid'] == vuln['parent_org_uid']:
                time_to_remediate = get_age(vuln['time_opened'], vuln['time_closed'])
                if vuln['cve'] in kevs_df['kev'].values:
                    org_kevs.append(time_to_remediate)
                if vuln['cvss_base_score'] >= 9.0:
                    org_crits.append(time_to_remediate)
                if vuln['cvss_base_score'] >= 7.0 and vuln['cvss_base_score'] < 9.0:
                    org_highs.append(time_to_remediate)
        average_kevs = average_list(org_kevs)
        average_crits = average_list(org_crits)
        average_highs = average_list(org_highs)
        average_time_to_remediate_list.append([org['organizations_uid'], org['group'], org['cyhy_db_name'], calculate_attr_compliance(average_kevs, "KEV"), calculate_attr_compliance(average_crits, "CRIT"), calculate_attr_compliance(average_highs, "HIGH")])
    df_attr = pd.DataFrame(average_time_to_remediate_list, columns= ["organizations_uid", "group", "cyhy_db_name", "attr_kevs", "attr_crits", "attr_highs"])
    return df_attr

def average_list(list):
    if len(list) == 0:
        return 0
    else:
        return round(sum(list)/len(list), 2)

def calculate_attr_compliance(vuln_attr, type):
    compliance_min = 0
    compliance_max = 0
    if vuln_attr == "N/A":
        return 100.0
    if type == "KEV":
        compliance_min = 14.0
        compliance_max = 28.0
    elif type == "CRIT":
        compliance_min = 15.0
        compliance_max = 30.0
    else:
        compliance_min = 30.0
        compliance_max = 60.0
    if vuln_attr <= compliance_min:
        return 100.0
    elif vuln_attr >= compliance_max:
        return 0.0
    else:
        return round((compliance_max-vuln_attr/compliance_min)*100, 2)

def get_bod_19_22(orgs_df):
    open_tickets_df = get_vs_open_vulns()
    kevs_df = get_kevs()

    bod_19_22_list = []
    for index, org in orgs_df.iterrows():
        total_kevs = 0
        overdue_kevs = 0
        total_crits = 0
        overdue_crits = 0
        total_highs = 0
        overdue_highs = 0
        total_medium = 0
        overdue_medium = 0
        total_low = 0
        overdue_low = 0
        for index2, ticket in open_tickets_df.iterrows():
            if org['cyhy_db_name'] == ticket['cyhy_db_name'] or org['organizations_uid'] == ticket['parent_org_uid']:
                time_opened = ticket['time_opened']
                now = datetime.now()
                age = get_age(time_opened, now)   
                if ticket['cve'] in kevs_df['kev'].values:
                    total_kevs = total_kevs + 1
                    if age > 14.0:
                        overdue_kevs = overdue_kevs + 1
                if ticket['cvss_base_score'] >= 9.0:
                    total_crits = total_crits + 1
                    if age > 15.0:
                        overdue_crits = overdue_crits + 1
                elif ticket['cvss_base_score'] >= 7.0 and ticket['cvss_base_score'] < 9.0:
                    total_highs = total_highs + 1
                    if age >30.0:
                        overdue_highs = overdue_highs + 1
                elif ticket['cvss_base_score'] >= 4.0 and ticket['cvss_base_score'] < 7.0:
                    total_medium = total_medium + 1
                    if age > 90.0:
                        overdue_medium = overdue_medium + 1
                else:
                    total_low = total_low + 1
                    if age > 180.0:
                        overdue_low = overdue_low + 1
        percent_compliance_kevs = get_percent_compliance(total_kevs, overdue_kevs)
        percent_compliance_crits = get_percent_compliance(total_crits, overdue_crits)
        percent_compliance_highs = get_percent_compliance(total_highs, overdue_highs)
        percent_compliance_medium = get_percent_compliance(total_medium, overdue_medium)
        percent_compliance_low = get_percent_compliance(total_low, overdue_low)
        bod_19_22_list.append([org['organizations_uid'], org['cyhy_db_name'], percent_compliance_kevs, percent_compliance_crits, percent_compliance_highs, percent_compliance_medium, percent_compliance_low])

    df_bod_19_22 = pd.DataFrame(bod_19_22_list, columns= ["organizations_uid", "cyhy_db_name", "percent_compliance_kevs", "percent_compliance_crits", "percent_compliance_highs", "percent_compliance_meds", "percent_compliance_lows"])
    return df_bod_19_22

def get_percent_compliance(total, overdue):
    if total == 0:
        return 100.0
    else:
        return round(((total - overdue)/total)* 100, 2)

def get_age(start_time, end_time):
    start_time = str(start_time)
    end_time = str(end_time)
    if "." in start_time:
        start_time = start_time.split(".")[0]
    if "." in end_time:
        end_time = end_time.split(".")[0]
    start_time = datetime.strptime(start_time, '%Y-%m-%d %H:%M:%S')
    start_time = start_time.timestamp()
    start_time = datetime.fromtimestamp(start_time, timezone.utc)
    start_time = start_time.replace(tzinfo=None)
    end_time = datetime.strptime(end_time, '%Y-%m-%d %H:%M:%S')
    end_time = end_time.timestamp()
    end_time = datetime.fromtimestamp(end_time, timezone.utc)
    end_time = end_time.replace(tzinfo=None)
    age = round((float(((end_time - start_time).total_seconds()))/60/60/24), 2)
    return age

def summarize_vs_vuln_counts(orgs_df, this_month):
    df_vulns = get_vs_open_vulns()
    df_kevs = get_kevs()
    vulns_list = []
    for index, org in orgs_df.iterrows():
        last_month_kevs = 0
        last_month_crits = 0
        last_month_highs = 0
        last_month_meds = 0
        last_month_lows = 0
        this_month_kevs = 0
        this_month_crits = 0
        this_month_highs = 0
        this_month_meds = 0
        this_month_lows = 0
        for index2, vulns in df_vulns.iterrows():
            if org['organizations_uid'] == vulns['organizations_uid'] or org['organizations_uid'] == vulns['parent_org_uid']:
                if vulns['time_opened'] >= this_month:
                    if vulns['cvss_base_score'] >= 9.0:
                        this_month_crits = this_month_crits + 1
                    elif vulns['cvss_base_score'] >= 7.0:
                        this_month_highs = this_month_highs + 1
                    elif vulns['cvss_base_score'] >= 4.0:
                        this_month_meds = this_month_meds + 1
                    else:
                        this_month_lows = this_month_lows + 1
                    if vulns['cve'] in df_kevs['kev'].values:
                            this_month_kevs = this_month_kevs + 1
                else:
                    if vulns['cvss_base_score'] >= 9.0:
                        last_month_crits = last_month_crits + 1
                    elif vulns['cvss_base_score'] >= 7.0:
                        last_month_highs = last_month_highs + 1
                    elif vulns['cvss_base_score'] >= 4.0:
                        last_month_meds = last_month_meds + 1
                    else:
                        last_month_lows = last_month_lows + 1
                    if vulns['cve'] in df_kevs['kev'].values:
                        last_month_kevs = last_month_kevs + 1
        change_in_kevs =  this_month_kevs - last_month_kevs
        change_in_crits = this_month_crits - last_month_crits
        change_in_highs = this_month_highs - last_month_highs
        change_in_meds = this_month_meds - last_month_meds
        change_in_lows = this_month_lows - last_month_lows
        vulns_list.append([org['organizations_uid'],org['cyhy_db_name'], org['group'], change_in_kevs, change_in_crits, change_in_highs, change_in_meds, change_in_lows])
    df_vulns = pd.DataFrame(vulns_list, columns= ["organizations_uid", "cyhy_db_name", "group", "change_in_kevs", "change_in_crits", "change_in_highs", "change_in_meds", "change_in_lows"])
    return df_vulns

def summarize_pe_vuln_counts(orgs_df, last_month, this_month, next_month):
    df_vulns = get_pe_vulns(last_month, next_month)
    df_kevs = get_kevs()
    vs_orgs = orgs_df.loc[orgs_df['report_on'] == False]
    pe_orgs = orgs_df.loc[orgs_df['report_on'] == True]
    vulns_list = []
    for index, org in pe_orgs.iterrows():
        last_month_kevs = 0
        last_month_crits = 0
        last_month_highs = 0
        last_month_meds = 0
        last_month_lows = 0
        this_month_kevs = 0
        this_month_crits = 0
        this_month_highs = 0
        this_month_meds = 0
        this_month_lows = 0
        for index2, vulns in df_vulns.iterrows():
            if org['cyhy_db_name'] == vulns['cyhy_db_name'] or org['organizations_uid'] == vulns['parent_org_uid']:
                if vulns['timestamp'] >= this_month:
                    if vulns['cvss'] >= 9.0:
                        this_month_crits = this_month_crits + 1
                    elif vulns['cvss'] >= 7.0:
                        this_month_highs = this_month_highs + 1
                    elif vulns['cvss'] >= 4.0:
                        this_month_meds = this_month_meds + 1
                    else:
                        this_month_lows = this_month_lows + 1
                    if vulns['cve'] in df_kevs['kev'].values:
                        this_month_kevs = this_month_kevs + 1
                else:
                    if vulns['cvss'] >= 9.0:
                        last_month_crits = last_month_crits + 1
                    elif vulns['cvss'] >= 7.0:
                        last_month_highs = last_month_highs + 1
                    elif vulns['cvss'] >= 4.0:
                        last_month_meds = last_month_meds + 1
                    else:
                        last_month_lows = last_month_lows + 1
                    if vulns['cve'] in df_kevs['kev'].values:
                        last_month_kevs = last_month_kevs + 1
        change_in_kevs =  this_month_kevs - last_month_kevs
        change_in_crits = this_month_crits - last_month_crits
        change_in_highs = this_month_highs - last_month_highs
        change_in_meds = this_month_meds - last_month_meds
        change_in_lows = this_month_lows - last_month_lows
        vulns_list.append([org['organizations_uid'], org['cyhy_db_name'], org['group'], change_in_kevs, change_in_crits, change_in_highs, change_in_meds, change_in_lows])
    df_pe_vulns = pd.DataFrame(vulns_list, columns= ["organizations_uid", "cyhy_db_name", "group", "change_in_kevs", "change_in_crits", "change_in_highs", "change_in_meds", "change_in_lows"])
    for index, org in vs_orgs.iterrows():
        group = org['group']
        df = df_pe_vulns.loc[df_pe_vulns['group'] == group]
        vs_change_in_kevs = df['change_in_kevs'].mean()
        vs_change_in_crits = df['change_in_crits'].mean()
        vs_change_in_highs = df['change_in_highs'].mean()
        vs_change_in_meds = df['change_in_meds'].mean()
        vs_change_in_lows = df['change_in_lows'].mean()
        vulns_list.append([org['organizations_uid'], org['cyhy_db_name'], org['group'], vs_change_in_kevs, vs_change_in_crits, vs_change_in_highs, vs_change_in_meds, vs_change_in_lows])
    df_vulns = pd.DataFrame(vulns_list, columns= ["organizations_uid", "cyhy_db_name", "group", "change_in_kevs", "change_in_crits", "change_in_highs", "change_in_meds", "change_in_lows"])
    return df_vulns

def summarize_was_vuln_counts(orgs_df, last_month, this_month, next_month):
    was_orgs = get_was_stakeholders()
    was_ids = was_orgs['cyhy_db_name'].values
    conditions = [orgs_df['cyhy_db_name'].isin(was_ids), ~orgs_df['cyhy_db_name'].isin(was_ids)]
    was_customer = ["Yes", "No"]
    orgs_df["was_org"] = np.select(conditions, was_customer)
    was_orgs_df = orgs_df.loc[orgs_df['was_org'] == "Yes"]
    vs_orgs_df = orgs_df.loc[orgs_df['was_org'] == "No"]
    was_open_vulns = get_was_open_vulns(last_month, next_month)
    vulns_list = []
    for index, org in was_orgs_df.iterrows():
        last_month_crits = 0
        last_month_highs = 0
        last_month_meds = 0
        last_month_lows = 0
        this_month_crits = 0
        this_month_highs = 0
        this_month_meds = 0
        this_month_lows = 0
        for index2, vulns in was_open_vulns.iterrows():
            if org['organizations_uid'] == vulns['pe_org_id']:
                last_detected = vulns['last_detected']
                last_detected = datetime(last_detected.year, last_detected.month, last_detected.day)
                if last_detected >= this_month:
                    if vulns['base_score'] >= 9.0:
                        this_month_crits = this_month_crits + 1
                    elif vulns['base_score'] >= 7.0:
                        this_month_highs = this_month_highs + 1
                    elif vulns['base_score'] >= 4.0:
                        this_month_meds = this_month_meds + 1
                    else:
                        this_month_lows = this_month_lows + 1
                else:
                    if vulns['base_score'] >= 9.0:
                        last_month_crits = last_month_crits + 1
                    elif vulns['base_score'] >= 7.0:
                        last_month_highs = last_month_highs + 1
                    elif vulns['base_score'] >= 4.0:
                        last_month_meds = last_month_meds + 1
                    else:
                        last_month_lows = last_month_lows + 1
        change_in_crits = this_month_crits - last_month_crits
        change_in_highs = this_month_highs - last_month_highs
        change_in_meds = this_month_meds - last_month_meds
        change_in_lows = this_month_lows - last_month_lows
        vulns_list.append([org['organizations_uid'], org['cyhy_db_name'], org['group'], change_in_crits, change_in_highs, change_in_meds, change_in_lows])
    df_was_vulns = pd.DataFrame(vulns_list, columns= ["organizations_uid", "cyhy_db_name", "group", "change_in_crits", "change_in_highs", "change_in_meds", "change_in_lows"])
    for index, org in vs_orgs_df.iterrows():
        group = org['group']
        df = df_was_vulns.loc[df_was_vulns['group'] == group]
        vs_change_in_crits = df['change_in_crits'].mean()
        vs_change_in_highs = df['change_in_highs'].mean()
        vs_change_in_meds = df['change_in_meds'].mean()
        vs_change_in_lows = df['change_in_lows'].mean()
        vulns_list.append([org['organizations_uid'], org['cyhy_db_name'], org['group'], vs_change_in_crits, vs_change_in_highs, vs_change_in_meds, vs_change_in_lows])
    df_vulns = pd.DataFrame(vulns_list, columns= ["organizations_uid", "cyhy_db_name", "group", "change_in_crits", "change_in_highs", "change_in_meds", "change_in_lows"])
    return df_vulns

def summarize_bod_18(orgs_df):
    df_bod_18 = get_bod_18()
    bod_18_list = []
    for index, org in orgs_df.iterrows():
        email_bod_compliance = 100.0
        web_bod_compliance = 100.0
        for index2, bod in df_bod_18.iterrows():
            if org['organizations_uid'] == bod['organizations_uid']:
                if bod['email_compliance_pct'] is not None:
                    email_bod_compliance = bod['email_compliance_pct']
                if bod['https_compliance_pct'] is not None:
                    web_bod_compliance = bod['https_compliance_pct']
        bod_18_list.append([org['organizations_uid'], email_bod_compliance, web_bod_compliance])
        df_vulns = pd.DataFrame(bod_18_list, columns= ["organizations_uid", "email_bod_compliance", "web_bod_compliance"])
    return df_vulns

def summarize_was_bod_19(orgs_df, this_month, next_month):
    was_orgs = get_was_stakeholders()
    was_ids = was_orgs['cyhy_db_name'].values
    conditions = [orgs_df['cyhy_db_name'].isin(was_ids), ~orgs_df['cyhy_db_name'].isin(was_ids)]
    was_customer = ["Yes", "No"]
    orgs_df["was_org"] = np.select(conditions, was_customer)
    was_orgs_df = orgs_df.loc[orgs_df['was_org'] == "Yes"]
    vs_orgs_df = orgs_df.loc[orgs_df['was_org'] == "No"]
    was_open_vulns = get_was_open_vulns(this_month, next_month)
    vulns_list = []
    for index, org in was_orgs_df.iterrows():
        total_crits = 0
        overdue_crits = 0
        total_highs = 0
        overdue_highs = 0
        total_medium = 0
        overdue_medium = 0
        total_low = 0
        overdue_low = 0
        for index2, vulns in was_open_vulns.iterrows():
            if org['organizations_uid'] == vulns['pe_org_id']:
                last_detected = vulns['last_detected']
                last_detected = datetime(last_detected.year, last_detected.month, last_detected.day)
                first_detected = vulns['first_detected']
                first_detected = datetime(first_detected.year, first_detected.month, first_detected.day)
                age = get_age(first_detected, last_detected)
                if vulns['base_score'] >= 9.0:
                    total_crits = total_crits + 1
                    if age > 15.0:
                        overdue_crits = overdue_crits + 1
                elif vulns['base_score'] >= 7.0 and vulns['base_score'] < 9.0:
                    total_highs = total_highs + 1
                    if age >30.0:
                        overdue_highs = overdue_highs + 1
                elif vulns['base_score']>= 4.0 and vulns['base_score'] < 7.0:
                    total_medium = total_medium + 1
                    if age > 90.0:
                        overdue_medium = overdue_medium + 1
                else:
                    total_low = total_low + 1
                    if age > 180.0:
                        overdue_low = overdue_low + 1
        percent_compliance_crits = get_percent_compliance(total_crits, overdue_crits)
        percent_compliance_highs = get_percent_compliance(total_highs, overdue_highs)
        percent_compliance_medium = get_percent_compliance(total_medium, overdue_medium)
        percent_compliance_low = get_percent_compliance(total_low, overdue_low)
        vulns_list.append([org['organizations_uid'], org['cyhy_db_name'], org['group'], percent_compliance_crits, percent_compliance_highs, percent_compliance_medium, percent_compliance_low])
    df_was_vulns = pd.DataFrame(vulns_list, columns= ["organizations_uid", "cyhy_db_name", "group", "percent_compliance_crits", "percent_compliance_highs", "percent_compliance_meds", "percent_compliance_lows"])
    for index, org in vs_orgs_df.iterrows():
        group = org['group']
        df = df_was_vulns.loc[df_was_vulns['group'] == group]
        was_crits_compl = df['percent_compliance_crits'].mean()
        was_highs_compl = df['percent_compliance_highs'].mean()
        was_meds_compl = df['percent_compliance_meds'].mean()
        was_lows_compl = df['percent_compliance_lows'].mean()
        vulns_list.append([org['organizations_uid'], org['cyhy_db_name'], org['group'], was_crits_compl, was_highs_compl, was_meds_compl, was_lows_compl])
    df_vulns = pd.DataFrame(vulns_list, columns= ["organizations_uid", "cyhy_db_name", "group", "percent_compliance_crits", "percent_compliance_highs", "percent_compliance_meds", "percent_compliance_lows"])
    return df_vulns

def summarize_was_attr(orgs_df, this_month, next_month):
    was_orgs = get_was_stakeholders()
    was_ids = was_orgs['cyhy_db_name'].values
    conditions = [orgs_df['cyhy_db_name'].isin(was_ids), ~orgs_df['cyhy_db_name'].isin(was_ids)]
    was_customer = ["Yes", "No"]
    orgs_df["was_org"] = np.select(conditions, was_customer)
    was_orgs_df = orgs_df.loc[orgs_df['was_org'] == "Yes"]
    vs_orgs_df = orgs_df.loc[orgs_df['was_org'] == "No"]
    df_closed_vulns = get_was_closed_vulns(this_month, next_month)
    average_time_to_remediate_list = []
    for index, org in was_orgs_df.iterrows():
        org_crits = []
        org_highs = []
        for index2, vuln in df_closed_vulns.iterrows():
            if org['organizations_uid'] == vuln['organizations_uid'] or org['organizations_uid'] == vuln['parent_org_uid']:
                time_to_remediate = get_age(vuln['first_detected'], vuln['last_detected'])
                if vuln['base_score'] >= 9.0:
                    org_crits.append(time_to_remediate)
                if vuln['base_score'] >= 7.0 and vuln['cvss_base_score'] < 9.0:
                    org_highs.append(time_to_remediate)
        average_crits = average_list(org_crits)
        average_highs = average_list(org_highs)
        average_time_to_remediate_list.append([org['organizations_uid'], org['group'], org['cyhy_db_name'], average_crits, average_highs, calculate_attr_compliance(average_crits, "CRIT"), calculate_attr_compliance(average_highs, "HIGH")])
    was_df_attr = pd.DataFrame(average_time_to_remediate_list, columns= ["organizations_uid", "group", "cyhy_db_name", "attr_crits", "attr_highs", "attr_compl_crits", "attr_compl_highs"])
    for index, org in vs_orgs_df.iterrows():
        group = org['group']
        df = was_df_attr.loc[was_df_attr['group'] == group]
        attr_crtis = df['attr_crits'].mean()
        attr_highs = df['attr_highs'].mean()
        average_time_to_remediate_list.append([org['organizations_uid'], org['cyhy_db_name'], org['group'], attr_crtis, attr_highs, calculate_attr_compliance(attr_crtis, "CRIT"), calculate_attr_compliance(attr_highs, "HIGH")])
    df_attr = pd.DataFrame(average_time_to_remediate_list, columns= ["organizations_uid", "cyhy_db_name", "group", "attr_crits", "attr_highs", "attr_compl_crits", "attr_compl_highs"])
    return df_attr

def normalize_port_scans(df_ports):
    port_list = []
    for index, org in df_ports.iterrows():
        group = org['group']
        df = df_ports.loc[df_ports['group'] == group]
        ports_max = df['change_in_ports'].max()
        ports_min = df['change_in_ports'].min()
        protocols_max = df['change_in_protocols'].max()
        protocols_min = df['change_in_protocols'].min()

        norm_ports = 0
        norm_protocols = 0
        
        if ports_max == 0 or ports_max - ports_min == 0:
            norm_ports = 75 
        else:
            norm_ports = ((org['change_in_ports'] - ports_min) / (ports_max - ports_min)) * 100

        if protocols_max == 0 or protocols_max - protocols_min == 0:
            norm_protocols = 75 
        else:
            norm_protocols = ((org['change_in_protocols'] - protocols_min) / (protocols_max - protocols_min)) * 100

        norm_services = 100

        port_list.append([org['organizations_uid'], org['group'], norm_ports, norm_protocols, norm_services])
    df_vulns = pd.DataFrame(port_list, columns= ["organizations_uid", "group", "norm_ports", "norm_protocols", "norm_services"])   
    return df_vulns
    
def summarize_port_scans(orgs_df, last_month, this_month, next_month):
    df_port_scans = get_ports_protocols(last_month, next_month)
    port_scans_list = []
    for index, org in orgs_df.iterrows():
        last_month_total_ports = 0
        last_month_vuln_ports = 0
        last_month_total_protocols = 0
        last_month_vuln_protocols = 0
        this_month_total_ports = 0
        this_month_vuln_ports = 0
        this_month_total_protocols = 0
        this_month_vuln_protocols = 0
        for index2, ports in df_port_scans.iterrows():
            if org['organizations_uid'] == ports['organizations_uid'] or org['organizations_uid'] == ports['parent_org_uid']:
                if ports['report_period'] < this_month:
                    last_month_total_ports = last_month_total_ports + ports['ports']
                    last_month_vuln_ports = last_month_vuln_ports + ports['risky_ports']
                    last_month_total_protocols = last_month_total_protocols + ports['protocols']
                    last_month_vuln_protocols = last_month_vuln_protocols + ports['risky_protocols']
                else:
                    this_month_total_ports = this_month_total_ports + ports['ports']
                    this_month_vuln_ports = this_month_vuln_ports + ports['risky_ports']
                    this_month_total_protocols = this_month_total_protocols + ports['protocols']
                    this_month_vuln_protocols = this_month_vuln_protocols + ports['risky_protocols']

        change_in_ports = average_values(this_month_vuln_ports, this_month_total_ports) - average_values(last_month_vuln_ports, last_month_total_ports)
        change_in_protocols = average_values(this_month_vuln_protocols, this_month_total_protocols) - average_values(last_month_vuln_protocols, last_month_total_protocols)
        
        port_scans_list.append([org['organizations_uid'], org['cyhy_db_name'], org['group'], change_in_ports, change_in_protocols])
    df_port_scans = pd.DataFrame(port_scans_list, columns= ["organizations_uid", "cyhy_db_name", "group", "change_in_ports", "change_in_protocols"])
    return df_port_scans
                    
def average_values(vuln_count, total_count):
    if total_count == 0:
        return 0
    else:
        return round((vuln_count/total_count) * 100, 2)
  
def normalize_vulns(df_vulns, team):
    vulns_list = []
    for index, org in df_vulns.iterrows():
        group = org['group']
        df = df_vulns.loc[df_vulns['group'] == group]

        kevs_max = 0
        kevs_min = 0
        if team != "WAS":
            kevs_max = df['change_in_kevs'].max()
            kevs_min = df['change_in_kevs'].min()
        crits_max = df['change_in_crits'].max()
        crits_min = df['change_in_crits'].min()
        highs_max = df['change_in_highs'].max()
        highs_min = df['change_in_highs'].min()
        meds_max = df['change_in_meds'].max()
        meds_min = df['change_in_meds'].min()
        lows_max = df['change_in_lows'].max()
        lows_min = df['change_in_lows'].min()

        norm_kevs = 0
        if team != "WAS":
            if kevs_max == 0 or kevs_max - kevs_min == 0:
                norm_kevs = 75
            else:
                norm_kevs = ((org['change_in_kevs'] - kevs_min) / (kevs_max - kevs_min)) * 100
        else:
            norm_kevs = "N/A"

        norm_crits = 0
        if crits_max == 0 or crits_max - crits_min == 0:
            norm_crits = 75 
        else:
            norm_crits = ((org['change_in_crits'] - crits_min) / (crits_max - crits_min)) * 100

        norm_highs = 0
        if highs_max == 0 or highs_max - highs_min == 0:
            norm_highs = 75 
        else:
            norm_highs = ((org['change_in_highs'] - highs_min) / (highs_max - highs_min)) * 100

        norm_meds = 0
        if meds_max == 0 or meds_max - meds_min == 0:
            norm_meds = 75
        else:
            norm_meds = ((org['change_in_meds'] - meds_min) / (meds_max - meds_min)) * 100

        norm_lows = 0
        if lows_max == 0 or lows_max - lows_min == 0:
            norm_lows = 75 
        else:
            norm_lows = (org['change_in_lows'] - lows_min) / (lows_max - lows_min)

        vulns_list.append([org['organizations_uid'], org['group'], norm_kevs, norm_crits, norm_highs, norm_meds, norm_lows])
    df_vulns = pd.DataFrame(vulns_list, columns= ["organizations_uid", "group", "norm_kevs", "norm_crits", "norm_highs", "norm_meds", "norm_lows"])   
    return df_vulns

def get_letter_grade(score):
    if score < 65.0:
        return "F"
    elif score >= 65.0 and score < 67.0:
        return "D"
    elif score >= 67.0 and score < 70.0:
        return "D+"
    elif score >= 70.0 and score < 73.0:
        return "C-"
    elif score >= 73.0 and score < 77.0:
        return "C"
    elif score >= 77.0 and score < 80.0:
        return "C+"
    elif score >= 80.0 and score < 83.0:
        return "B-"
    elif score >= 83.0 and score < 87.0:
        return "B"
    elif score >= 87.0 and score < 90.0:
        return "B+"
    elif score >= 90.0 and score < 93.0:
        return "A-"
    elif score >= 93.0 and score < 97.0:
        return "A"
    else:
        return "A+"

def get_next_month(report_period_year, report_period_month):
    next_report_period_month = 0
    next_report_period_year = 0
    if report_period_month == 12:
        next_report_period_month = 1
        next_report_period_year = report_period_year + 1
    else:
        next_report_period_month = report_period_month + 1
        next_report_period_year = report_period_year
    next_report_period_date = datetime(next_report_period_year, next_report_period_month, 1)
    return next_report_period_date

def get_last_month(report_period_year, report_period_month):
    last_report_period_month = 0
    last_report_period_year = 0
    if report_period_month == 1:
        last_report_period_month = 12
        last_report_period_year = report_period_year - 1
    else:
        last_report_period_month = report_period_month - 1
        last_report_period_year = report_period_year
    last_report_period_date = datetime(last_report_period_year, last_report_period_month, 1)
    return last_report_period_date
