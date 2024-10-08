''' download salesforce attachments '''

import argparse
import csv
import os

import maya

import requests
from simple_salesforce import Salesforce
from PIL import Image
from PyPDF2 import PdfMerger


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
    first_query =(
        "SELECT ContentDocumentId FROM ContentDocumentLink "
        f"WHERE LinkedEntityId = '{parent_id}'")
    first_result = connection.query(first_query)["records"]
    final = []
    for result in first_result:
        first_result_id = result["ContentDocumentId"]
        qr_str = (
            #f"SELECT Id, Body, Name FROM Attachment "
            #f"WHERE ParentId = '{parent_id}'"
            "SELECT Id, LatestPublishedVersionID, "
            "LatestPublishedVersion.VersionData, "
            "LatestPublishedVersion.Title, "
            "LatestPublishedVersion.FileExtension "
            "FROM ContentDocument "
            f"WHERE Id = '{first_result_id}'"
        )
        final += connection.query(qr_str)["records"]
    return final


def get_attachment(body, connection):
    ''' get the attachment download'''
    body_url = body['LatestPublishedVersion']["VersionData"]
    return requests.get(
        f"https://{connection.sf_instance}{body_url}",
        headers = {"Content-Type": "application/json" ,
              "Authorization": "Bearer " + connection.session_id}
    )


def mk_filename(name, date, body, output):
    ''' make filename for attachment'''
    old_filename = body["LatestPublishedVersion"]["Title"]
    extension = body["LatestPublishedVersion"]["FileExtension"]
    return f"{output}/{date}-{name}-{old_filename}.{extension}"


def save_attachment(parent_id, name, date, connection, output):
    ''' get and save the attachment '''
    bodies = attachment_bodies(parent_id, connection)
    for body in bodies:
        attachment = get_attachment(body, connection)
        #old_filename = body["LatestPublishedVersion"]["Title"]
        #filename = f"{output}/{date}-{name}-{old_filename}"
        filename = mk_filename(name, date, body, output)
        print(f"-> Downloading {filename}")
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
        date = set_date(row)
        save_attachment(parent_id, name, date, connection, output_dir)


def set_date(row):
    ''' sets date for file download, or defaults to today'''
    possible_date = row["Date Filed"]
    if possible_date:
        return maya.when(possible_date).iso8601()[:10]
    if "Created Date" in row and row["Created Date"]:
        return maya.when(row["Created Date"]).iso8601()[:10]
    return maya.now().iso8601()[:10]



def get_col_names(input_file):
    with open(input_file, "r") as f:
        to_figure_out = list(csv.DictReader(f))
    first_key, second_key, *_ = to_figure_out[0].keys()
    return first_key.strip(), second_key.strip()


# merge PDFs
def merge_pdfs(orig_filename, output):
    ''' merge pdfs into single document '''
    convert_images(output)
    merger = PdfMerger(strict=False)
    files = os.listdir(f"{output}/originals")
    files.sort()
    for file in files:
        if file.endswith(".pdf"):
            input = open(os.path.join(f"{output}/originals", file), "rb")
            merger.append(input)
    filename = f"{output}/{orig_filename.split('.')[0]}-combined.pdf"
    merger.write(filename)
    merger.close()


def convert_images(output):
    files = os.listdir(output)
    for file in files:
        if is_image(file):
            print(f"converting {file}")
            img = Image.open(f"{output}/{file}")
            filename = f"{output}/{file.split('.')[0]}.pdf"
            print(f"new filename {filename}")
            img.save(filename, "PDF")


def is_image(filename):
    lower_filename = filename.lower()
    return lower_filename[-3:] in ['jpg', 'png'] or lower_filename[-4:] in ['jpeg', 'heic']



# CLI
PARSER = argparse.ArgumentParser(description="download salesforce attachments")

PARSER.add_argument("-f", "--filename",
                    help="filename for when not in interactive mode",
                    required=False)
PARSER.add_argument("-d", "--directory",
                    help="output directory",
                    required=False)

def set_input(args):
    ''' set input argument'''
    if args.filename:
        return args.filename
    filename = input("What's the name of your file? ")
    return filename


def set_output(args):
    ''' set output directory '''
    if args.directory:
        return args.directory
    output = input("What directory should I save this in? ")
    return output


if __name__ == "__main__":
    connection = make_connection("PRODUCTION")
    ARGS = PARSER.parse_args()
    INPUT = set_input(ARGS)
    OUTPUT = set_output(ARGS)
    os.makedirs(f"{OUTPUT}/originals")
    NAME_COL, ID_COL = get_col_names(INPUT)
    download_attachments(connection, INPUT, f"{OUTPUT}/originals", ID_COL, NAME_COL)

    merge_pdfs(INPUT, OUTPUT)
