''' download salesforce attachments '''

import csv, os

import requests
from simple_salesforce import Salesforce

RESULTS = "results/"


def make_connection(sandbox: str):
    ''' make a connection '''
    if sandbox == 'PRODUCTION':
        return Salesforce(
            username=os.environ.get("PRODUCTION_USER"),
            password=os.environ.get("PRODUCTION_PW"),
            security_token=os.environ.get("PRODUCTION_TOKEN")
        )
    return Salesforce(
        username=os.environ.get("SANDBOX_USER"),
        password=os.environ.get("SANDBOX_PW"),
        security_token=os.environ.get("SANDBOX_TOKEN"),
        domain='test')


def attachment_body(parent_id, connection):
    ''' get the url to the attachment's body'''
    qr_str = (
        f"SELECT Id, Body, Name FROM Attachment "
        f"WHERE ParentId = '{parent_id}'"
    )
    return connection.query(qr_str)["records"][0]


def get_attachment(body, connection):
    ''' get the attachment download'''
    body_url = body["Body"]
    return requests.get(
        f"https://{connection.sf_instance}{body_url}",
        headers = {"Content-Type": "application/json" ,
              "Authorization": "Bearer " + connection.session_id}
    )


def save_attachment(parent_id, name, connection):
    ''' get and save the attachment '''
    body = attachment_body(parent_id, connection)
    attachment = get_attachment(body, connection)
    old_filename = body["Name"]
    filename = f"{RESULTS}{name}-{old_filename}"
    with open(filename, "wb") as f:
        f.write(attachment.content)


def download_attachments(connection):
    ''' download attachments from csv file '''
    with open("to_download.csv", "r") as f:
        to_download = list(csv.DictReader(f))
    for row in to_download:
        parent_id = row["id"]
        name = row["name"]
        save_attachment(parent_id, name, connection)


if __name__ == "__main__":
    connection = make_connection("PRODUCTION")
    download_attachments(connection)
