import os
import json
import pandas
from gcp_api_client import gcp_api_client

term_df = pandas.read_csv("term_library.csv", header=0)
api_client = gcp_api_client()


def transform(notes):
    notes = notes.lower()
    medical_terms = extract_medical_terms(notes)
    transformed = ""
    last_idx = 0

    for entry in medical_terms["entityMentions"]:
        term = entry["text"]["content"]
        begin_idx = entry["text"]["beginOffset"]

        transformed += notes[last_idx:begin_idx]

        transformed = replace_text(transformed, term)
        last_idx = begin_idx + len(term)

    transformed += notes[last_idx:]
    print("Transformed in transform.py file ", transformed)
    # print("last_idx: ", last_idx)
    # print("transformed: ", transformed)
    return transformed


def extract_medical_terms(notes):
    nlpService = (
        f'projects/{os.getenv("GCP_PROJECT_ID")}/locations/us-central1/services/nlp'
    )
    body = f"""
    {{ "documentContent": "{notes}" }}
    """
    medical_terms = api_client.analyzeEntities(
        nlpService=nlpService, body=json.loads(body)
    ).execute()

    print("gcp_api_client: ", medical_terms)
    return medical_terms


def replace_text(transformed, term):
    layman_term = term_df.loc[term_df["technical_term"] == term]["layman_term"].values

    if len(layman_term) > 0:
        transformed += layman_term[0]
    else:
        splits = term.split(" ")

        if len(splits) > 1:
            for i in range(len(splits)):
                transformed = replace_text(transformed, splits[i])
                if i != len(splits) - 1:
                    transformed += " "
        else:
            transformed += term
    return transformed


# jargon = "CIRCULATORY DISORDERS WITH ACUTE MYOCARDIAL INFARCTION & MAJOR COMPLICATION, DISCHARGED ALIVE"
# jargon = jargon
# print(transform(jargon))
