from flask import Flask, request, jsonify, abort
from flask_basicauth import BasicAuth
import os
import logging
from utils import createcm, getcm, getcmrejected, rejectcm, getcmnew, acceptedcm, getclusterquota, sendmail, updatecm
from openshift.dynamic.exceptions import ConflictError
from flask_cors import CORS, cross_origin
import re

log = logging.getLogger('werkzeug')
log.setLevel(logging.DEBUG)

app = Flask(__name__)
app.config['BASIC_AUTH_USERNAME'] = os.environ.get('USERNAME', "username")
app.config['BASIC_AUTH_PASSWORD'] = os.environ.get('PASSWORD', "password")

CORS(app, origins='*',
     headers=['Content-Type', 'Authorization'],
     expose_headers='Authorization')
basic_auth = BasicAuth(app)

@app.route("/requests",methods = ['POST'])
@cross_origin(origin='*',headers=['Content-Type','Authorization'])
def requests():
    if request.method == 'POST':
        content = request.json
        content["rejected"]= False
        content["created"]= False
        content["name"] = replaceCorrectValues(content["name"])
        i = 0
        while i < len(content["environnements"]):
          content["environnements"][i]=replaceCorrectValues(content["environnements"][i])
          i += 1
        try:
            createcm(content,"malaw-requests")
            return "Successfully created."
        except ConflictError as err:
            abort(400, 'Already exists')

@app.route("/requests",methods = ['GET'])
@cross_origin(origin='*',headers=['Content-Type','Authorization'])
@basic_auth.required
def requestsget():
    if request.method == 'GET':
        data = getcm("malaw-requests")
        return data

@app.route("/requests",methods = ['PUT'])
@cross_origin(origin='*',headers=['Content-Type','Authorization'])
@basic_auth.required
def requestsput():
    if request.method == 'PUT':
        content = request.json
        name = content["name"]
        content["rejected"]= False
        data = updatecm(name,content,"malaw-requests")
        return "Successfully updated."

@app.route("/requests/<name>/rejected",methods = ['POST'])
@cross_origin(origin='*',headers=['Content-Type','Authorization'])
@basic_auth.required
def rejectedrequest(name):
    if request.method == 'POST':
        content = request.json
        message = content["message"]
        rejectcm(name,"malaw-requests",message)
        return "rejected"

@app.route("/requests/rejected",methods = ['GET'])
@cross_origin(origin='*',headers=['Content-Type','Authorization'])
@basic_auth.required
def rejected():
    if request.method == 'GET':
        data = getcmrejected("malaw-requests")
        return data

@app.route("/requests/new",methods = ['GET'])
@cross_origin(origin='*',headers=['Content-Type','Authorization'])
@basic_auth.required
def newquest():
    if request.method == 'GET':
        data = getcmnew("malaw-requests")
        return data

@app.route("/requests/<name>/accepted",methods = ['POST'])
@cross_origin(origin='*',headers=['Content-Type','Authorization'])
@basic_auth.required
def acceptedrequest(name):
    if request.method == 'POST':
        content = request.json
        acceptedcm(name,"malaw-requests","message")
        return "Successfully created."

@app.route("/clusterquota",methods = ['GET'])
@cross_origin(origin='*',headers=['Content-Type','Authorization'])
@basic_auth.required
def clusterquotas():
    if request.method == 'GET':
        data = getclusterquota("malaw-requests")
        return data

def replaceCorrectValues(data):
    resultat = ''
    data = data.replace('/', '-').lower()
    for c in data:
        if bool (re.match('[a-z]', c )) or (c == '-'):
            resultat += c;
    return resultat

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=8080)
