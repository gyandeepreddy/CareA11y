from curses import keyname
import os
from flask import Flask, jsonify, request
import pandas as pd
from flask_cors import CORS
from dotenv import find_dotenv, load_dotenv
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import or_
import requests
from bs4 import BeautifulSoup
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from transform import transform

app = Flask(__name__)
CORS(app, resources={r"*": {"origins": "*"}})

load_dotenv(find_dotenv())
url = os.getenv("DATABASE_URL")
if url and url.startswith("postgres://"):
    url = url.replace("postgres://", "postgresql://", 1)

app.config["SQLALCHEMY_DATABASE_URI"] = url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY")

db = SQLAlchemy(app)


class Users(db.Model):
    id = db.Column(db.Integer, unique=True, nullable=False, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    password = db.Column(db.String(120), unique=True, nullable=False)
    role = db.Column(db.String(10), nullable=False)


class Patient(db.Model):
    id = db.Column(db.Integer, unique=True, nullable=False, primary_key=True)
    appointment_id = db.Column(db.Integer, nullable=False)
    subject_id = db.Column(db.String(5), nullable=False)
    subject_name = db.Column(db.String(100), nullable=False)
    doctor_id = db.Column(db.String(6), nullable=False)
    doctor_name = db.Column(db.String(100), nullable=False)
    general_notes = db.Column(db.Text, nullable=False)
    procedure_notes = db.Column(db.Text, nullable=False)
    diagnosis_notes = db.Column(db.Text, nullable=False)
    transformed_general_notes = db.Column(db.Text)
    transformed_procedure_notes = db.Column(db.Text)
    transformed_diagnosis_notes = db.Column(db.Text)
    date = db.Column(db.DateTime, nullable=False)


class ICDDiagnosis(db.Model):
    id = db.Column(db.Integer, unique=True, nullable=False, primary_key=True)
    icd9_code = db.Column(db.String(10), nullable=False)
    icd10_code = db.Column(db.String(20))
    short_title = db.Column(db.Text, nullable=False)
    long_title = db.Column(db.Text, nullable=False)


class ICDProcedure(db.Model):
    id = db.Column(db.Integer, unique=True, nullable=False, primary_key=True)
    icd9_code = db.Column(db.String(10), nullable=False)
    icd10_code = db.Column(db.String(20))
    short_title = db.Column(db.Text, nullable=False)
    long_title = db.Column(db.Text, nullable=False)


@app.route("/login", methods=["POST"])
def login():
    authorization_verification = verify_authorization()
    if authorization_verification != "success":
        return authorization_verification

    input_json = request.get_json()
    id = input_json["id"]
    password = input_json["password"]
    user_data = Users.query.filter_by(id=id).first()
    is_invalid_id = user_data is None
    role = user_data.role
    name = user_data.name
    data = {
        "id": id,
        "role": role,
        "name": name,
        "appointments": get_all_appointments(id, role),
    }
    if is_invalid_id or not check_password_hash(user_data.password, password):
        return jsonify(status="error", message="Invalid user id or password")
    return jsonify(status="success", data=data)


@app.route("/signup", methods=["POST"])
def signup():
    authorization_verification = verify_authorization()
    if authorization_verification != "success":
        return authorization_verification

    input_json = request.get_json()
    id = input_json["id"]
    password = input_json["password"]
    name = input_json["name"]
    role = input_json["role"]
    user_exists = Users.query.filter_by(id=id).first() is not None
    if user_exists:
        return jsonify(
            status="error",
            message="An account with the provided id already exists",
        )
    else:
        password_hash = generate_password_hash(password, method="sha256")
        user = Users(id=id, password=password_hash, role=role, name=name)
        db.session.add(user)
        db.session.commit()
        return jsonify(status="success")


@app.route("/add-appointment", methods=["POST"])
def add_appointment():
    authorization_verification = verify_authorization()
    if authorization_verification != "success":
        return authorization_verification

    input_json = request.get_json()
    subject_id = input_json["patient_id"]
    doctor_id = input_json["doctor_id"]
    doctor_name = input_json["doctor_name"]
    general_notes = input_json["general_notes"]
    transformed_general_notes = transform(general_notes)

    patient = Patient.query.filter_by(subject_id=subject_id).first()
    subject_name = patient.subject_name

    appointments = (
        Patient.query.filter_by(subject_id=subject_id)
        .order_by(Patient.appointment_id.desc())
        .all()
    )

    if len(appointments) > 0:
        appointment_id = int(appointments[0].appointment_id) + 1
    else:
        appointment_id = 1

    date = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")

    # diagnosis_data = ICDDiagnosis.query.filter(
    #     or_(
    #         ICDDiagnosis.icd9_code == diagnosis_icd_code,
    #         ICDDiagnosis.icd10_code == diagnosis_icd_code,
    #     )
    # ).first()
    # diagnosis_short_text = diagnosis_data.short_title
    # diagnosis_long_text = diagnosis_data.long_title
    if (
        "diagnosis_icd_code" not in input_json
        or not input_json["diagnosis_icd_code"].strip()
    ):
        diagnosis_data = ""
        transformed_diagnosis_notes = ""
        diagnosis_notes = ""
    else:
        diagnosis_icd_code = input_json["diagnosis_icd_code"]
        diagnosis_data = get_diagnostics(diagnosis_icd_code)
        if diagnosis_data == "error":
            transformed_diagnosis_notes = ""
            diagnosis_notes = ""
        else:
            transformed_diagnosis_notes = transform(diagnosis_data)
            diagnosis_notes = (
                "The patient was diagnosed with " + transformed_diagnosis_notes
            )

    # procedure_data = ICDProcedure.query.filter(
    #     or_(
    #         ICDProcedure.icd9_code == procedure_icd_code,
    #         ICDProcedure.icd10_code == procedure_icd_code,
    #     )
    # ).first()
    # procedure_short_text = procedure_data.short_title
    # procedure_long_text = procedure_data.long_title
    if (
        "procedure_icd_code" not in input_json
        or not input_json["procedure_icd_code"].strip()
    ):
        procedure_data = ""
        transformed_procedure_notes = ""
        procedure_notes = ""
    else:
        procedure_icd_code = input_json["procedure_icd_code"]
        procedure_data = get_procedure(procedure_icd_code)
        if procedure_data == "error":
            procedure_notes = ""
            transformed_procedure_notes = ""
        else:
            transformed_procedure_notes = transform(procedure_data)
            procedure_notes = "The patient received " + transformed_procedure_notes

    patient = Patient(
        subject_id=subject_id,
        doctor_id=doctor_id,
        doctor_name=doctor_name,
        subject_name=subject_name,
        general_notes=general_notes,
        procedure_notes=procedure_notes,
        diagnosis_notes=diagnosis_notes,
        transformed_diagnosis_notes=transformed_diagnosis_notes,
        transformed_procedure_notes=transformed_procedure_notes,
        transformed_general_notes=transformed_general_notes,
        appointment_id=appointment_id,
        date=date,
    )

    data = {
        "subject_id": subject_id,
        "doctor_id": doctor_id,
        "doctor_name": doctor_name,
        "patient_name": subject_name,
        "general_notes": general_notes,
        "procedure_notes": procedure_notes,
        "diagnosis_notes": diagnosis_notes,
        "transformed_diagnosis_notes": transformed_diagnosis_notes,
        "transformed_procedure_notes": transformed_procedure_notes,
        "transformed_general_notes": transformed_general_notes,
        "appointment_id": appointment_id,
        "date": date,
    }

    db.session.add(patient)
    db.session.commit()
    return jsonify(status="success", data=data)


@app.route("/edit-text", methods=["POST"])
def edit_texts():
    authorization_verification = verify_authorization()
    if authorization_verification != "success":
        return authorization_verification

    input_json = request.get_json()
    appointment_id = input_json["appointment_id"]
    subject_id = input_json["subject_id"]

    appointment_info = Patient.query.filter_by(
        appointment_id=appointment_id, subject_id=subject_id
    ).first()

    transformed_diagnosis_notes = appointment_info.transformed_diagnosis_notes
    transformed_procedure_notes = appointment_info.transformed_procedure_notes
    transformed_general_notes = appointment_info.transformed_general_notes

    if "transformed_diagnosis_notes" in input_json:
        appointment_info.transformed_diagnosis_notes = input_json[
            "transformed_diagnosis_notes"
        ]
        transformed_diagnosis_notes = input_json["transformed_diagnosis_notes"]

    if "transformed_procedure_notes" in input_json:
        appointment_info.transformed_procedure_notes = input_json[
            "transformed_procedure_notes"
        ]
        transformed_procedure_notes = input_json["transformed_procedure_notes"]

    if "transformed_general_notes" in input_json:
        appointment_info.transformed_general_notes = input_json[
            "transformed_general_notes"
        ]
        transformed_general_notes = input_json["transformed_general_notes"]

    db.session.commit()

    updated_data = {
        "transformed_diagnosis_notes": transformed_diagnosis_notes,
        "transformed_procedure_notes": transformed_procedure_notes,
        "transformed_general_notes": transformed_general_notes,
    }

    return jsonify(status="success", data=updated_data)


@app.route("/get-appointment", methods=["POST"])
def get_appointment():
    authorization_verification = verify_authorization()
    if authorization_verification != "success":
        return authorization_verification

    input_json = request.get_json()
    appointment_id = input_json["appointment_id"]
    subject_id = input_json["patient_id"]

    appointment_info = Patient.query.filter_by(
        appointment_id=appointment_id, subject_id=subject_id
    ).first()
    transformed_general_notes = appointment_info.transformed_general_notes
    transformed_diagnosis_notes = appointment_info.transformed_diagnosis_notes
    transformed_procedure_notes = appointment_info.transformed_procedure_notes

    data = {
        "transformed_notes": transformed_general_notes,
        "diagnosis_notes": transformed_diagnosis_notes,
        "procedure_notes": transformed_procedure_notes,
    }

    return jsonify(data)


@app.route("/add-to-dictionary", methods=["POST"])
def add_to_dictionary():
    authorization_verification = verify_authorization()
    if authorization_verification != "success":
        return authorization_verification

    try:
        df = pd.read_csv("term_library.csv")
        input_json = request.get_json()
        key = input_json["key"]
        value = input_json["value"]

        df_len = len(df)

        df.loc[df_len] = [df_len, key, value]
        df.to_csv("term_library.csv", index=False)

        return jsonify(status="success")
    except Exception as e:
        print(e)
        return jsonify(
            status="error", message="An unexpected error occured. Please try again"
        )


# @app.route("/get-all-appointments", methods=["POST"])
def get_all_appointments(patient_id, role):
    authorization_verification = verify_authorization()
    if authorization_verification != "success":
        return authorization_verification

    if role.lower() == "doctor":
        return []

    subject_id = patient_id
    appointments = (
        Patient.query.filter_by(subject_id=subject_id)
        .order_by(Patient.appointment_id)
        .all()
    )
    data = []
    for appointment in appointments:
        dictionary = {}

        dictionary["appointment_id"] = appointment.appointment_id
        dictionary["transformed_general_notes"] = appointment.transformed_general_notes
        dictionary[
            "transformed_diagnosis_notes"
        ] = appointment.transformed_diagnosis_notes
        dictionary[
            "transformed_procedure_notes"
        ] = appointment.transformed_procedure_notes
        dictionary["date"] = appointment.date

        # data[appointment_id] = [transformed_notes, diagnosis_notes, procedure_notes]
        data.append(dictionary)
        # data.append[
        #     appointment_id, transformed_notes, diagnosis_notes, procedure_notes
        # ]()
    # return jsonify(data)
    return data


def verify_authorization():
    if "Authorization" not in request.headers or request.headers[
        "Authorization"
    ] != os.getenv("AUTHORIZATION"):
        return "Authentication failed. Invalid token provided"
    return "success"


def get_diagnostics(icd_code):
    url_base = "https://icdcodelookup.com/icd-10/codes/"
    url = url_base + icd_code
    response = requests.get(url)
    content = response.content
    soup = BeautifulSoup(content, "html.parser")
    des_out = soup.find_all("span", {"class": "unbold"})
    if len(des_out) > 0:
        output = des_out[0].text.lower()
    else:
        output = "error"
    return output


def get_procedure(icd_code):
    url_base = "https://www.findacode.com/code.php?set=ICD10CM&c="
    url = url_base + icd_code
    response = requests.get(url)
    content = response.content
    soup = BeautifulSoup(content, "html.parser")

    v = soup.find_all("title")[0].text

    output = " ".join(v.split(",")[0].split(" ")[1:]).lower()

    if "not found" in output:
        output = "error"
    return output


if __name__ == "__main__":
    app.run(
        host=os.getenv("IP", "0.0.0.0"),
        port=int(os.getenv("PORT", 8080)),
    )
