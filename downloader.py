''' download salesforce attachments '''

import csv, os

import requests
from simple_salesforce import Salesforce


def make_connection(sandbox: str):
    ''' make a connection '''
    if sandbox == 'PRODUCTION':
        return Salesforce(
            username=os.environ.get("PRODUCTION_USER"),
            password=os.environ.get("SF_PRODUCTION_PW"),
            security_token=os.environ.get("SF_PRODUCTION_TOKEN")
        )
    return Salesforce(
        username=os.environ.get("SANDBOX_USER"),
        password=os.environ.get("SANDBOX_PW"),
        security_token=os.environ.get("SANDBOX_TOKEN"),
        domain='test')


def attachment_bodies(parent_id, connection):
    ''' get the url to the attachment's body'''
    qr_str = (
        f"SELECT Id, Body, Name FROM Attachment "
        f"WHERE ParentId = '{parent_id}'"
    )
    return connection.query(qr_str)["records"]


def get_attachment(body, connection):
    ''' get the attachment download'''
    body_url = body["Body"]
    return requests.get(
        f"https://{connection.sf_instance}{body_url}",
        headers = {"Content-Type": "application/json" ,
              "Authorization": "Bearer " + connection.session_id}
    )


def save_attachment(parent_id, name, connection, output):
    ''' get and save the attachment '''
    bodies = attachment_bodies(parent_id, connection)
    for body in bodies:
        attachment = get_attachment(body, connection)
        old_filename = body["Name"]
        filename = f"{output}/{name}-{old_filename}"
        print(f"-> Downloading {old_filename}")
        with open(filename, "wb") as f:
            f.write(attachment.content)


def download_attachments(connection, input_file, output_dir,
                         id_column, name_column):
    ''' download attachments from csv file '''
    with open(input_file, "r") as f:
        to_download = list(csv.DictReader(f))
    print(f"Preparing to download {len(to_download)} files")
    for row in to_download:
        parent_id = row[id_column]
        name = row[name_column]
        save_attachment(parent_id, name, connection, output_dir)


def get_col_names(input_file):
    with open(input_file, "r") as f:
        to_figure_out = list(csv.DictReader(f))
    first_key, second_key, *_ = to_figure_out[0].keys()
    return first_key.strip(), second_key.strip()


if __name__ == "__main__":
    connection = make_connection("PRODUCTION")
    INPUT = input("What's the name of your file? ")
    OUTPUT = input("What directory should I save this in? ")
    NAME_COL, ID_COL = get_col_names(INPUT)
    download_attachments(connection, INPUT, OUTPUT, ID_COL, NAME_COL)
