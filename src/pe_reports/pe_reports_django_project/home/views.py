# Built in packages
import logging
import json
import socket
from datetime import datetime, timedelta
import re
import os

# Third party packages
from decouple import config
from django.views.generic import TemplateView
from django.views.generic.edit import FormView
from django.views import View
from django.shortcuts import render
from django.http import HttpResponseNotFound, \
    HttpResponseRedirect, \
    HttpResponse, \
    JsonResponse
from django.core.exceptions import ObjectDoesNotExist
from django.core import serializers
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.urls import reverse_lazy
from django.contrib.auth import logout
from django.contrib.auth.mixins import LoginRequiredMixin
from docx import Document
from docxtpl import DocxTemplate
import io

# TODO: Figure out circular referance on import
# from pe_source.data.sixgill.api import setOrganizationUsers, \
#     setOrganizationDetails
from .models import Organizations, WeeklyStatuses
from .forms import GatherStakeholderForm, WeeklyStatusesForm
import requests

# cisagov Libraries

LOGGER = logging.getLogger(__name__)


# Create your views here.

def getUserKey():
    urlIDs = 'http://127.0.0.1:8089/apiv1/get_key'
    payload = json.dumps({
        "refresh_token": f'{config("USER_REFRESH_TOKEN")}'
    })
    headers = {
        'Content-Tpye': 'application/json',

    }

    response = requests.post(urlIDs, headers=headers, data=payload).json()

    return response
#
#
theCurrentUserKey = getUserKey()
# print(f'The current key is {theCurrentUserKey}')
theSavedUserKey = config("API_KEY")
# # print(f'The saved key is {theSavedUserKey}')
#
#
def updateAPIKey(theSavedUserKey, theCurrentUserKey):
    if theSavedUserKey == theCurrentUserKey:
        print('The keys match and nothing happened. ')
    else:
        try:
            script_directory = os.path.dirname(os.path.realpath(__name__))
            print(script_directory)
            env_file_path = os.path.join(script_directory, ".env")
            with open(env_file_path, 'r') as f:
                f.seek(0)
                data = f.read()
                dataReplaced = data.replace(theSavedUserKey, theCurrentUserKey)
                print("Reading and replacing api key.")
            with open(env_file_path, 'w') as f:
                if theSavedUserKey in data:
                    print("The apiKey has been updated.")
                    f.write(dataReplaced)
            return theCurrentUserKey
        except:
            print("Failed to open and write new file.")

def getAgencies(org_name):
    """Get all agency names from P&E database."""
    # global conn, cursor

    try:
        # params = config()
        #
        # conn = psycopg2.connect(**params)
        #
        # if conn:
        #     LOGGER.info(
        #         "There was a connection made to"
        #         "the database and the query was executed."
        #     )
        #
        #     cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        #
        #     query = "select organizations_uid,name from"
        #     " organizations where name='{}';"
        #
        #     cursor.execute(query.format(org_name))
        #
        #     result = cursor.fetchall()
        result = Organizations.objects.filter(name=org_name)
        resultDict = {}

        for row in result:
            # row[0] = org UUID
            # row[1] = org name
            resultDict[f"{row[0]}"] = f"{row[1]}"
        return resultDict

    except (Exception, ObjectDoesNotExist) as err:
        LOGGER.error("There was a problem logging into the psycopg database %s",
                     err)
    finally:
        # if conn is not None:
        #     cursor.close()
        #     conn.close()
        LOGGER.info("The connection/query was completed and closed.")

        return resultDict


def getSubdomain(domain):
    """Get all sub-domains from passed in root domain."""
    allsubs = []

    url = "https://domains-subdomains-discovery.whoisxmlapi.com/api/v1"
    payload = json.dumps(
        {
            "apiKey": f"{API_WHOIS}",
            "domains": {"include": [f"{domain}"]},
            "subdomains": {"include": ["*"], "exclude": []},
        }
    )
    headers = {"Content-Type": "application/json"}
    response = requests.request("POST", url, headers=headers, data=payload)
    data = response.json()

    subdomains = data["domainsList"]
    LOGGER.info(subdomains)

    subisolated = ""
    for sub in subdomains:

        if sub != f"www.{domain}":
            LOGGER.info(sub)
            subisolated = sub.rsplit(".")[:-2]
            LOGGER.info(
                "The whole sub is %s and the isolated sub is %s", sub,
                subisolated
            )
        allsubs.append(subisolated)

    return subdomains, allsubs


def getallsubdomainIPS(domain):
    """Get a list of IP addresses associated with a subdomain."""
    LOGGER.info("The domain at getallsubdomsinIPS is %s", domain)
    alladdresses = []
    for x in getSubdomain(domain)[0]:
        domainaddress = theaddress(x)
        if domainaddress not in alladdresses and domainaddress != "":
            alladdresses.append(domainaddress)
    return alladdresses


def theaddress(domain):
    """Get actual IP address of domain."""
    gettheAddress = ""
    try:
        gettheAddress = socket.gethostbyname(domain)
    except socket.gaierror:
        LOGGER.info("There is a problem with the domain that you selected")

    return gettheAddress


def setStakeholder(customer):
    """Insert customer into the P&E reports database."""
    global conn, cursor

    try:
        LOGGER.info("Starting insert into database...")

        params = config()

        conn = psycopg2.connect(**params)

        if conn:
            LOGGER.info(
                "There was a connection made to "
                "the database and the query was executed "
            )

            cursor = conn.cursor()

            cursor.execute(
                f"insert into organizations(name)" f"values('{customer}')")

            return True

    except (Exception, psycopg2.DatabaseError) as err:
        LOGGER.error("There was a problem logging into the psycopg database %s",
                     err)
        return False
    finally:
        if conn is not None:
            conn.commit()
            cursor.close()
            conn.close()
            LOGGER.info("The connection/query was completed and closed.")


def setCustRootDomain(customer, rootdomain, orgUUID):
    """Insert customer root domain into the PE-Reports database."""
    global conn, cursor

    try:
        LOGGER.info("Starting insert into database...")

        params = config()

        conn = psycopg2.connect(**params)

        if conn:
            LOGGER.info(
                "There was a connection made to "
                "the database and the query was executed "
            )

            cursor = conn.cursor()

            cursor.execute(
                f"insert into root_domains("
                f"organizations_uid,"
                f"organization_name,"
                f" root_domain)"
                f"values('{orgUUID}', '{customer}','{rootdomain}');"
            )
            return True

    except (Exception, psycopg2.DatabaseError) as err:
        LOGGER.error("There was a problem logging into the psycopg database %s",
                     err)
        return False
    finally:
        if conn is not None:
            conn.commit()
            cursor.close()
            conn.close()
            LOGGER.info("The connection/query was completed and closed.")


def setCustSubDomain(subdomain, rootUUID, rootname):
    """Insert customer into the PE-Reports database."""
    global conn, cursor

    try:

        LOGGER.info("Starting insert into database...")

        params = config()

        conn = psycopg2.connect(**params)

        if conn:

            LOGGER.info(
                "There was a connection made to "
                "the database and the query to "
                "insert the subdomains was executed "
            )

            cursor = conn.cursor()

            for sub in subdomain:
                cursor.execute(
                    f"insert into sub_domains("
                    f"sub_domain,"
                    f"root_domain_uid,"
                    f" root_domain)"
                    f"values('{sub}',"
                    f" '{rootUUID}',"
                    f"'{rootname}');"
                )
            return True

    except (Exception, psycopg2.DatabaseError) as err:
        LOGGER.error("There was a problem logging into the psycopg database %s",
                     err)
        return False
    finally:
        if conn is not None:
            conn.commit()
            cursor.close()
            conn.close()
            LOGGER.info("The connection/query was completed and closed.")


def setCustomerExternalCSG(
        customer, customerIP, customerRootDomain, customerSubDomain,
        customerExecutives
):
    """Insert customer not in cyhyDB into the PE-Reports database."""
    global conn, cursor

    iplist = []
    domainlist = []
    try:
        LOGGER.info("Starting insert into database...")

        params = config()

        conn = psycopg2.connect(**params)

        if conn:

            LOGGER.info(
                "There was a connection made to"
                " the database and the query was executed "
            )

            cursor = conn.cursor()

            for ip in customerIP:
                iplist.append(ip)

                cursor.execute(
                    f"insert into organizations(domain_name,"
                    f" domain_ip,"
                    f" date_saved) "
                    f"values('{customer}',"
                    f" '{ip}',"
                    f"'{thedateToday}');"
                )
            for domain in customerRootDomain:
                domainlist.append(domain)
                cursor.execute(
                    f"insert into domain_assets(domain_name,"
                    f" domain_ip,"
                    f" date_saved) "
                    f"values('{customer}',"
                    f" '{ip}', '{thedateToday}');"
                )

    except (Exception, psycopg2.DatabaseError) as err:
        LOGGER.error("There was a problem logging into the psycopg database %s",
                     err)
    finally:
        if conn is not None:
            conn.commit()
            cursor.close()
            conn.close()
            LOGGER.info("The connection/query was completed and closed.")

    return iplist


def setNewCSGOrg(newOrgName, orgAliases, orgdomainNames, orgIP, orgExecs):
    """Set a new stakeholder name at CSG."""
    newOrganization = json.dumps(
        {
            "name": f"{newOrgName}",
            "organization_commercial_category": "customer",
            "countries": ["worldwide"],
            "industries": ["Government"],
        }
    )
    url = "https://api.cybersixgill.com/multi-tenant/organization"

    headers = {
        "Content-Type": "application/json",
        "Cache-Control": "no-cache",
        "Authorization": f"Bearer {getToken()}",
    }

    response = requests.post(url, headers=headers, data=newOrganization).json()

    newOrgID = response["id"]

    if newOrgID:
        LOGGER.info("A new org_id was created: %s", newOrgID)

        setOrganizationUsers(newOrgID)
        setOrganizationDetails(newOrgID, orgAliases, orgdomainNames, orgIP,
                               orgExecs)

    return response


@login_required
def index(request):
    allUsers = Organizations.objects.filter(name='EAC')
    # output = '<br>'.join([c.username for c in customers])
    users = {
        "user": allUsers
    }
    return render(request, 'index.html', users)


@login_required
def home(request):
    try:
        return render(request, 'home.html')
    except:
        return HttpResponseNotFound('Nothing found')


@login_required
def stakeholder(request):
    try:
        if request.method == 'POST':
            LOGGER.info('Got to the stakeholder form')
            form = GatherStakeholderForm(request.POST)
            if form.is_valid():
                cust = form.cleaned_data['cust'].upper()
                custDomainAliases = form.cleaned_data[
                    'custDomainAliases'].split(
                    ",")
                custRootDomain = form.cleaned_data["custRootDomain"].split(",")
                custRootDomainValue = custRootDomain[0]
                custExecutives = form.cleaned_data["custExecutives"].split(",")
                allDomain = getAgencies(cust)
                allSubDomain = getSubdomain(custRootDomainValue)
                allValidIP = getallsubdomainIPS(custRootDomainValue)
                # print(custExecutives)

                try:

                    if cust not in allDomain.values():
                        messages.success(request,

                                         f"You successfully submitted a new"
                                         f" customer {cust}")

                        if setStakeholder(cust):
                            LOGGER.info("The customer %s was entered.", cust)
                            allDomain = list(getAgencies(cust).keys())[0]

                            if setCustRootDomain(cust, custRootDomainValue,
                                                 allDomain):
                                rootUUID = getRootID(allDomain)[cust]

                                LOGGER.info(
                                    "The root domain %s was entered at root_domains.",
                                    custRootDomainValue,
                                )
                                if allSubDomain:
                                    for subdomain in allSubDomain:
                                        if setCustSubDomain(subdomain, rootUUID,
                                                            cust):
                                            LOGGER.info(
                                                "The subdomains have been entered.")
                                            setNewCSGOrg(
                                                cust,
                                                custDomainAliases,
                                                custRootDomain,
                                                allValidIP,
                                                custExecutives,
                                            )

                    else:
                        messages.warning(request, f"The customer"
                                                  f" {cust} already exists.")

                except ValueError as e:
                    messages.warning(request,
                                     "The customer IP %s is not a valid IP, please try again.",
                                     "danger", e)
                    return HttpResponseRedirect("/stakeholder/")
                messages.success(request,
                                 "The new stakeholder has been inserted.d")
                return HttpResponseRedirect("/stakeholder/")



        else:
            form = GatherStakeholderForm()
        return render(request, 'stakeholder/stakeholder.html', {'form': form})


    except:
        return HttpResponseNotFound('Nothing found')


def create_word_document(request):
    """Create a word document."""

    accomplishments_list = []
    ongoing_tasks_list = []
    upcoming_tasks_list = []
    obstacles_list = []
    non_standard_meeting_list = []
    deliverables_list = []
    pto_list = []

    # Get the current week ending date
    current_date = datetime.now()
    days_to_week_end = (4 - current_date.weekday()) % 7
    week_ending_date = current_date + timedelta(days=days_to_week_end)
    reformatted_week_ending_date = week_ending_date.strftime("%m-%d-%Y")

    # Create a Document object
    doc = Document()

    weeklyInfo = WeeklyStatuses.objects.filter(week_ending=week_ending_date)

    # Serialize the queryset to JSON
    serialized_data = serializers.serialize('json', weeklyInfo)

    # Load the serialized data into a JSON object
    json_data = json.loads(serialized_data)

    # print(json_data)
    # Iterate through the JSON object and set variables from the fields
    for status in json_data:
        accomplishments = status['fields']['key_accomplishments']
        ongoing_tasks = status['fields']['ongoing_task']
        upcoming_tasks = status['fields']['upcoming_task']
        obstacles = status['fields']['obstacles']
        non_standard_meeting = status['fields']['non_standard_meeting']
        deliverables = status['fields']['deliverables']
        pto = status['fields']['pto']
        week_ending = status['fields']['week_ending']
        the_current_user = status['fields']['user_status']
        statusComplete = status['fields']['statusComplete']

        # Append each status to their respective list
        if accomplishments not in accomplishments_list:
            split_data = re.split(r',\s+(?=ISSUE\s*-\s*\d+:)', accomplishments)

            for item in split_data:
                if item:
                    accomplishments_list.append(item)

        if ongoing_tasks not in ongoing_tasks_list:
            split_data = re.split(r',\s+(?=ISSUE\s*-\s*\d+:)', ongoing_tasks)

            for item in split_data:
                if item:
                    ongoing_tasks_list.append(ongoing_tasks)
        if upcoming_tasks not in upcoming_tasks_list:
            split_data = re.split(r',\s+(?=ISSUE\s*-\s*\d+:)', upcoming_tasks)

            for item in split_data:
                if item:
                    upcoming_tasks_list.append(upcoming_tasks)
        if obstacles not in obstacles_list:
            split_data = re.split(r',\s+(?=ISSUE\s*-\s*\d+:)', obstacles)

            for item in split_data:
                if item:
                    obstacles_list.append(obstacles)
        if non_standard_meeting not in non_standard_meeting_list:
            split_data = re.split(r',\s+(?=ISSUE\s*-\s*\d+:)',
                                  non_standard_meeting)

            for item in split_data:
                if item:
                    non_standard_meeting_list.append(non_standard_meeting)
        if deliverables not in deliverables_list:
            split_data = re.split(r',\s+(?=ISSUE\s*-\s*\d+:)', deliverables)

            for item in split_data:
                if item:
                    deliverables_list.append(deliverables)
        if pto not in pto_list:
            split_data = re.split(r',\s+(?=ISSUE\s*-\s*\d+:)', pto)

            for item in split_data:
                if item:
                    pto_list.append(pto)

        # Load the template
        template = DocxTemplate("/Users/duhnc/Desktop/allInfo/"
                                "pe-reports-apiextended/src/pe_reports/"
                                "pe_reports_django_project/home/"
                                "PEWeeklyStatusReportTemplate.docx")

        # Define the values to insert into the template, including a list of tasks
        context = {
            'user': the_current_user.capitalize(),
            'week_ending': reformatted_week_ending_date,
            "accomplishments_list": accomplishments_list,
            "ongoing_tasks_list": ongoing_tasks_list,
            "upcoming_task_list": upcoming_tasks_list,
            "obstacles_list": obstacles_list,
            "non_standard_meeting_list": non_standard_meeting_list,
            "deliverables_list": deliverables_list,
            "pto_list": pto_list
        }

        # Render the template with the context
        template.render(context)

        # Save the rendered document as a new Word file
        template.save("/Users/duhnc/Desktop/allInfo/pe-reports-apiextended/"
                      "src/pe_reports/pe_reports_django_project/home/"
                      "statusReportArchive/"
                      "weeklyStatus_%s.docx" % week_ending_date)

    messages.success(request, "The weekly status report has been created.")
    return HttpResponse("Word document created successfully.")


def email_notification(request):
    """Email notification to notify the user that the status has been submitted."""
    # TODO - Add the email notification to nofity the user that
    #  the status has been not been submitted


class FetchWeeklyStatusesView(View):
    """Fetch the weekly statuses from the API
     and pass to Weekly Statuses template"""
    updateAPIKey(theSavedUserKey, theCurrentUserKey)
    def get(self, request, *args, **kwargs):

        url = 'http://127.0.0.1:8089/apiv1/fetch_weekly_statuses'
        headers = {
            'Content-Type': 'application/json',
            'access_token': f'{config("API_KEY")}'
        }

        try:

            response = requests.post(url, headers=headers)
            response.raise_for_status()  # Raise an exception if the response contains an HTTP error status
            data = response.json()
            return JsonResponse(data, safe=False)

        except requests.exceptions.HTTPError as errh:
            LOGGER.error(errh)
        except requests.exceptions.ConnectionError as errc:
            LOGGER.error(errc)
        except requests.exceptions.Timeout as errt:
            LOGGER.error(errt)
        except requests.exceptions.RequestException as err:
            LOGGER.error(err)
        except json.decoder.JSONDecodeError as err:
            LOGGER.error(err)

        # Return an error JsonResponse if an exception occurs
        return JsonResponse({"error": "Failed to fetch weekly statuses"},
                            status=400)


class StatusView(TemplateView):
    template_name = 'weeklyStatus.html'
    LOGGER.info('Got to Status')


class StatusForm(LoginRequiredMixin, FormView):
    form_class = WeeklyStatusesForm
    template_name = 'weeklyStatus.html'

    success_url = reverse_lazy('weekly_status')

    def get_form_kwargs(self):
        kwargs = super(StatusForm, self).get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        the_current_user = ''
        statusComplete = 0
        week_ending = 0
        current_date = datetime.now()
        days_to_week_end = (4 - current_date.weekday()) % 7
        week_ending_date = current_date + timedelta(days=days_to_week_end)

        weeklyInfo = WeeklyStatuses.objects. \
            filter(week_ending=week_ending_date,
                   user_status=self.request.user.first_name)

        # Serialize the queryset to JSON
        serialized_data = serializers.serialize('json', weeklyInfo)

        # Load the serialized data into a JSON object
        json_data = json.loads(serialized_data)

        # Iterate through the JSON object and set variables from the fields
        for status in json_data:
            the_current_user = status['fields']['user_status']
            statusComplete = status['fields']['statusComplete']
            week_ending = status['fields']['week_ending']

        if statusComplete == 1:
            messages.warning(self.request,
                             f"The weekly status for {the_current_user.title()}"
                             f" for the weekending {week_ending} "
                             f"has already been completed.")
            return HttpResponseRedirect("/weekly_status/")

        key_accomplishments = form.cleaned_data['key_accomplishments'].upper()

        ongoing_task = form.cleaned_data['ongoing_task'].upper()

        upcoming_task = form.cleaned_data['upcoming_task'].upper()

        obstacles = form.cleaned_data['obstacles'].upper()

        non_standard_meeting = form.cleaned_data['non_standard_meeting'].upper()

        deliverables = form.cleaned_data['deliverables'].upper()

        pto = form.cleaned_data['pto_time'].upper()

        messages.success(self.request,
                         f'The weekly status was saved successfully.')

        weeklyStatus = WeeklyStatuses(
            key_accomplishments=key_accomplishments,
            user_status=self.request.user.first_name,
            ongoing_task=ongoing_task,
            upcoming_task=upcoming_task,
            obstacles=obstacles,
            non_standard_meeting=non_standard_meeting,
            deliverables=deliverables,
            pto=pto,
        )

        weeklyStatus.save()

        return super().form_valid(form)
