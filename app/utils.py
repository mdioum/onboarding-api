from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


from kubernetes import client, config
from openshift.dynamic import DynamicClient
import json
import ast
from openshift.dynamic.exceptions import ConflictError
from flask import abort
import smtplib, sys
import os
import logging
import ssl



k8s_client = config.new_client_from_config()
dyn_client = DynamicClient(k8s_client)


v1_services = dyn_client.resources.get(api_version='v1', kind='Service')
v1_project = dyn_client.resources.get(api_version='project.openshift.io/v1', kind='Project')
v1_clusterquota = dyn_client.resources.get(api_version='quota.openshift.io/v1', kind='ClusterResourceQuota')
v1_rolebinding= dyn_client.resources.get(api_version='authorization.openshift.io/v1', kind='RoleBinding')
v1_configmap= dyn_client.resources.get(api_version='v1', kind='ConfigMap')
v1_limitRange= dyn_client.resources.get(api_version='v1', kind='LimitRange')

MAIL_SERVER = os.environ.get('MAIL_SERVER', "10.100.56.56")
MAIL_PORT = os.environ.get('MAIL_PORT', "25")
MAIL_FROM = os.environ.get('MAIL_FROM', 'malaw@orange-sonatel.com')
MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD', '')
MAIL_REQUEST_DESTINATION = os.environ.get('MAIL_REQUEST_DESTINATION', "")

def createproject(name,demandeur):
    bodyproject = {
        "apiVersion": "project.openshift.io/v1",
        "kind": "Project",
        "metadata": {
            "labels": {
                "demandeur": demandeur
            },
            "name": name
        }
    }
    v1_project.create(body=bodyproject)
    createlimitrange(name)

def createlimitrange(namespace):
    bodyLimitRange = {
        "apiVersion": "v1",
        "kind": "LimitRange",
        "metadata": {
            "name": "limits-cpu-memory-"+namespace,
        },
        "spec": {
            "limits": [
                {
                    "default": {
                        "cpu": "1",
                        "memory": "1Gi"
                    },
                    "defaultRequest": {
                        "cpu": "50m",
                        "memory": "10Mi"
                    },
                    "max": {
                        "cpu": "1",
                        "memory": "1Gi"
                    },
                    "maxLimitRequestRatio": {
                        "cpu": "20"
                    },
                    "min": {
                        "cpu": "50m",
                        "memory": "10Mi"
                    },
                    "type": "Container"
                }
            ]
        }
    }
    v1_limitRange.create(body=bodyLimitRange,namespace=namespace)

def createrolebinding(name,admin,namespace):
    bodyrolebinding = {
        "apiVersion": "authorization.openshift.io/v1",
        "kind": "RoleBinding",
        "metadata": {
            "name": name,
            "namespace": namespace,
        },
        "roleRef": {
            "name": "malaw_devops"
        },
        "subjects": [
            {
                "kind": "User",
                "name": admin
            }
        ]
    }
    v1_rolebinding.create(body=bodyrolebinding)
def createclusterquota(data):
    bodyquota = {
        "apiVersion": "quota.openshift.io/v1",
        "kind": "ClusterResourceQuota",
        "metadata": {
            "name": data["name"]
        },
        "spec": {
            "quota": {
                "hard": {
                    "requests.cpu": data["ressource"]["cpu"],
                    "requests.memory": data["ressource"]["memory"],
                    "requests.storage": data["ressource"]["storage"]
                }
            },
            "selector": {
                "labels": {
                    "matchLabels": {
                        "demandeur": data["name"]
                    }
                }
            }
        }
    }
    v1_clusterquota.create(body=bodyquota)
def createcm(data,namespace):
    bodycm = {
        "apiVersion": "v1",
        "data": {
            "malaw": str(data)
        },
        "kind": "ConfigMap",
        "metadata": {
            "name": data["name"],
            "namespace": namespace
        }
    }
    v1_configmap.create(body=bodycm,namespace=namespace)
    if MAIL_REQUEST_DESTINATION != "":
        emails = MAIL_REQUEST_DESTINATION.split(";")
        for email in emails:
            if email != "":
                body = """Vous avez reçu une nouvelle demande de ressources. La demande est envoyée par %s.""" % (data["demandeur"]["email"])
                sendmail(email, 'Onboarding - Nouvelle demande', body)


def getcm(namespace):
    cm_list = v1_configmap.get(namespace=namespace)
    requests_list = {"data":[]}
    for cm in cm_list.items:
        requests_list["data"].append(ast.literal_eval(cm.data["malaw"]))
    return json.dumps(requests_list)


def updatecm(name,data,namespace):
    cm = v1_configmap.get(name=name,namespace=namespace)
    bodycm = {
        "apiVersion": "v1",
        "data": {
            "malaw": str(data)
        },
        "kind": "ConfigMap",
        "metadata": {
            "name": data["name"],
            "namespace": namespace
        }
    }
    v1_configmap.patch(body=bodycm,namespace=namespace)

def getclusterquota(namespace):
    cm_list = v1_configmap.get(namespace=namespace)
    requests_list = {"data":[]}
    for cm in cm_list.items:
        malawdata = ast.literal_eval(cm.data["malaw"])
        if malawdata.get("created"):
            if malawdata["created"] is True:
                crq = v1_clusterquota.get(name=malawdata["name"])
                malawdata["ressource"]["used.cpu"]=crq["status"]["total"]["used"]["requests.cpu"]
                malawdata["ressource"]["used.memory"]=crq["status"]["total"]["used"]["requests.memory"]
                malawdata["ressource"]["used.storage"]=crq["status"]["total"]["used"]["requests.storage"]
                malawdata["ressource"]["requests.cpu"]=crq["status"]["total"]["hard"]["requests.cpu"]
                malawdata["ressource"]["requests.memory"]=crq["status"]["total"]["hard"]["requests.memory"]
                malawdata["ressource"]["requests.storage"]=crq["status"]["total"]["hard"]["requests.storage"]
                requests_list["data"].append(malawdata)
    return json.dumps(requests_list)

def rejectcm(name,namespace,message):
    cm = v1_configmap.get(name=name,namespace=namespace)
    malawdata = ast.literal_eval(cm.data["malaw"])
    malawdata["rejected"] = True
    memoire = malawdata["ressource"]["memory"]
    cpu = malawdata["ressource"]["cpu"]
    projectName = malawdata["projet"]["nom"]
    bodycm = {
        "apiVersion": "v1",
        "data": {
            "malaw": str(malawdata)
        },
        "kind": "ConfigMap",
        "metadata": {
            "name": malawdata["name"],
            "namespace": namespace
        }
    }
    v1_configmap.patch(body=bodycm,namespace=namespace)
    mail_demandeur = malawdata["demandeur"]["email"]
    mail_admin = malawdata["projet"]["emailAdmin"]
    subject = 'Onboarding - Demande Refusée'
    body_demandeur = """Votre demande de creation de ressources (%s de mémoire et %s cores) pour le projet %s a été refusée.\n Cause: %s""" % ((memoire, cpu, projectName, message))
    body_admin = """La demande de creation de ressources (%s de mémoire et %s cores) pour le projet %s a été refusée.\n Cause: %s""" % ((memoire, cpu, projectName, message))
    sendmail(mail_demandeur,subject,body_demandeur)
    sendmail(mail_admin,subject,body_admin)

def getcmrejected(namespace):
    cm_list = v1_configmap.get(namespace=namespace)
    requests_list = {"data":[]}
    for cm in cm_list.items:
        malawdata = ast.literal_eval(cm.data["malaw"])
        if malawdata["rejected"] is True:
            requests_list["data"].append(malawdata)
    return json.dumps(requests_list)

def getcmnew(namespace):
    cm_list = v1_configmap.get(namespace=namespace)
    requests_list = {"data":[]}
    for cm in cm_list.items:
        malawdata = ast.literal_eval(cm.data["malaw"])
        if malawdata["rejected"] is False and malawdata["created"] is False:
            requests_list["data"].append(malawdata)
    return json.dumps(requests_list)

def acceptedcm(name,namespace,message):
    cm = v1_configmap.get(name=name,namespace=namespace)
    malawdata = ast.literal_eval(cm.data["malaw"])
    adminlogin =  malawdata["projet"]["loginAdmin"]
    adminrolebinding =  adminlogin+"-admin"
    mail_demandeur = malawdata["demandeur"]["email"]
    mail_admin = malawdata["projet"]["emailAdmin"]
    memoire = malawdata["ressource"]["memory"]
    cpu = malawdata["ressource"]["cpu"]
    projectName = malawdata["projet"]["nom"]
    environnements = malawdata["environnements"]
    try:
        createclusterquota(malawdata)
        for project in malawdata["environnements"]:
            createproject(project,name)
            createrolebinding(adminrolebinding,adminlogin,project)
        malawdata["rejected"] = False
        malawdata["created"] = True
        bodycm = {
            "apiVersion": "v1",
            "data": {
                "malaw": str(malawdata)
            },
            "kind": "ConfigMap",
            "metadata": {
                "name": malawdata["name"],
                "namespace": namespace
            }
        }
        v1_configmap.patch(body=bodycm,namespace=namespace)
    except ConflictError as err:
        abort(400, 'Already exists')
    #Send MAil to admin and requester
    subject = 'Onboarding - Demande Acceptée'
    body_requester = """Les ressources que vous aviez demandées (%s de mémoire et %s cores) pour le projet %s vous ont ete allouées et sont disponibles sur le cluster OpenShift à partir des environnements: %s .\n\n -  Onboarding Team""" % (memoire, cpu, projectName, environnements)
    body_admin = """Nous venons d'approuver votre demande de création de ressources (%s de mémoire et %s cores) pour le projet %s.\n Les ressources sont maintenant allouées et disponibles sur le cluster OpenShift à partir des environnements: %s.\n\n - Onboarding Team""" % (memoire, cpu, projectName, environnements)

    sendmail(mail_demandeur,subject,body_requester)
    sendmail(mail_admin,subject,body_admin)



def sendmail(to, subject,body):
    email_text = MIMEMultipart("alternative")
    email_text["From"] = MAIL_FROM
    email_text["To"] = to
    email_text["Subject"] = subject
    email_text.attach(MIMEText(body, "plain"))
    try:
        server = smtplib.SMTP(MAIL_SERVER, MAIL_PORT)
        server.ehlo()
        server.sendmail(MAIL_FROM, to, email_text.as_string())
        server.close()
        logging.warning("Mail sent")
    except Exception as e:
        logging.warning(str(e))
        logging.warning('Something went wrong...')

def sendMailWithUserAndPassword(to, subject,body):
    email_text = MIMEMultipart("alternative")
    email_text["From"] = "malaw@orange-sonatel.com"
    email_text["To"] = to
    email_text["Subject"] = subject
    email_text.attach(MIMEText(body, "plain"))
    try:
        context = ssl.create_default_context()
        server = smtplib.SMTP(MAIL_SERVER, MAIL_PORT)
        server.ehlo()
        server.starttls(context=context)
        server.ehlo()
        server.login(MAIL_FROM, MAIL_PASSWORD)
        server.sendmail(MAIL_FROM, to, email_text.as_string())
        server.close()

        logging.warning("Mail sent")
    except Exception as e:
        print(e)
        logging.warning(str(e))
        logging.warning('Something went wrong...')
