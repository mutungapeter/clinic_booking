"""Stable identities for synthetic demo records used by the seed commands."""

from uuid import NAMESPACE_URL, uuid5

PATIENT_NAMES = (
    ("Amina", "Otieno"),
    ("Brian", "Kamau"),
    ("Carol", "Wanjiku"),
    ("David", "Omondi"),
    ("Esther", "Njeri"),
    ("Felix", "Mutua"),
    ("Grace", "Achieng"),
    ("Henry", "Kiptoo"),
    ("Irene", "Wambui"),
    ("James", "Mwangi"),
)

DOCTOR_NAMES = (
    ("Alice", "Njoroge"),
    ("Benjamin", "Ouma"),
    ("Catherine", "Mutiso"),
    ("Daniel", "Chebet"),
    ("Elizabeth", "Maina"),
)

DEMO_PATIENT_PASSWORD = "ClinicDemo-Patients-2030!"

# Same order as DOCTOR_NAMES, preserving the existing doctors' stable UUIDs.
DOCTOR_SPECIALIZATIONS = (
    "Cardiologist",
    "Pediatrician",
    "Dermatologist",
    "General Practitioner",
    "Orthopedic Surgeon",
)


def seed_id(entity, key):
    return uuid5(NAMESPACE_URL, f"clinic-booking-api/demo/{entity}/{key}")


def patient_username(index):
    return f"demo_patient_{index:03d}"
