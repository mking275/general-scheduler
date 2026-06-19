"""
T057 / W-08: Generate Avimark fixture ZIP (847 patients).

Usage (standalone):
    python -m backend.scripts.generate_avimark_fixture

Returns:
    ZIP bytes containing clients.csv and patients.csv
    with 621 owners and 847 patients respectively.
"""

from __future__ import annotations

import csv
import io
import random
import string
import zipfile
from datetime import datetime, timedelta


_FIRST_NAMES = [
    "James", "Mary", "John", "Patricia", "Robert", "Jennifer", "Michael", "Linda",
    "William", "Barbara", "David", "Elizabeth", "Richard", "Susan", "Joseph",
    "Jessica", "Thomas", "Sarah", "Charles", "Karen", "Christopher", "Lisa",
    "Daniel", "Nancy", "Matthew", "Betty", "Anthony", "Margaret", "Donald",
    "Sandra", "Mark", "Ashley", "Paul", "Dorothy", "Steven", "Kimberly",
]

_LAST_NAMES = [
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller",
    "Davis", "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez",
    "Wilson", "Anderson", "Thomas", "Taylor", "Moore", "Jackson", "Martin",
    "Lee", "Perez", "Thompson", "White", "Harris", "Sanchez", "Clark",
    "Ramirez", "Lewis", "Robinson", "Walker", "Young", "Allen", "King",
]

_PET_NAMES = [
    "Bella", "Max", "Charlie", "Luna", "Cooper", "Lucy", "Buddy", "Bailey",
    "Molly", "Daisy", "Sadie", "Maggie", "Sophie", "Tucker", "Oliver",
    "Rocky", "Bear", "Duke", "Zeus", "Lola", "Stella", "Lily", "Penny",
    "Finn", "Milo", "Gus", "Murphy", "Teddy", "Jake", "Toby", "Buster",
    "Rex", "Cleo", "Nala", "Simba", "Oreo", "Peanut", "Shadow", "Zoe",
    "Coco", "Roxy", "Harley", "Thor", "Odin", "Ace", "Bruno", "Hugo",
]

_SPECIES = ["dog", "dog", "dog", "dog", "cat", "cat", "cat", "bird", "rabbit"]

_BREEDS_DOG = [
    "Labrador Retriever", "Golden Retriever", "German Shepherd", "Bulldog",
    "Beagle", "French Bulldog", "Poodle", "Rottweiler", "Yorkshire Terrier",
    "Dachshund", "Siberian Husky", "Boxer", "Australian Shepherd",
    "Shih Tzu", "Border Collie", "Cavalier King Charles Spaniel",
]

_BREEDS_CAT = [
    "Domestic Shorthair", "Domestic Longhair", "Siamese", "Maine Coon",
    "Persian", "Ragdoll", "Bengal", "Sphynx", "Scottish Fold",
]

_BREEDS_OTHER = ["Parakeet", "Cockatiel", "Holland Lop", "Mini Rex"]


def _rand_phone() -> str:
    area = random.randint(200, 999)
    num = random.randint(1000000, 9999999)
    return f"({area}) {str(num)[:3]}-{str(num)[3:]}"


def _rand_email(first: str, last: str) -> str:
    domains = ["gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "icloud.com"]
    return f"{first.lower()}.{last.lower()}{random.randint(1, 99)}@{random.choice(domains)}"


def _rand_date(years_back: int = 12) -> str:
    days = random.randint(30, years_back * 365)
    return (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")


def _rand_weight(species: str) -> float:
    if species == "dog":
        return round(random.uniform(3.0, 50.0), 1)
    elif species == "cat":
        return round(random.uniform(2.5, 7.0), 1)
    else:
        return round(random.uniform(0.1, 2.5), 1)


def generate_avimark_zip(
    num_clients: int = 621,
    num_patients: int = 847,
) -> bytes:
    """
    Generate a ZIP containing clients.csv and patients.csv
    with the specified counts.
    """
    rng = random.Random(42)  # Fixed seed for reproducibility

    # ── Generate clients ─────────────────────────────────────────────────────
    clients = []
    for i in range(1, num_clients + 1):
        first = rng.choice(_FIRST_NAMES)
        last  = rng.choice(_LAST_NAMES)
        clients.append({
            "ClientID":  str(i),
            "FirstName": first,
            "LastName":  last,
            "Phone1":    _rand_phone(),
            "Email":     _rand_email(first, last),
            "Address1":  f"{rng.randint(100, 9999)} {rng.choice(['Main St', 'Oak Ave', 'Pine Rd', 'Elm Dr', 'Maple Ln'])}",
            "City":      rng.choice(["Springfield", "Riverdale", "Maplewood", "Lakeside", "Hillcrest"]),
            "State":     rng.choice(["CA", "TX", "FL", "NY", "IL", "PA", "OH"]),
        })

    # ── Generate patients ────────────────────────────────────────────────────
    patients = []
    for i in range(1, num_patients + 1):
        owner = rng.choice(clients)
        species = rng.choice(_SPECIES)
        if species == "dog":
            breed = rng.choice(_BREEDS_DOG)
        elif species == "cat":
            breed = rng.choice(_BREEDS_CAT)
        else:
            breed = rng.choice(_BREEDS_OTHER)

        patients.append({
            "PatientID": str(i),
            "ClientID":  owner["ClientID"],
            "Name":      rng.choice(_PET_NAMES),
            "Species":   species,
            "Breed":     breed,
            "Sex":       rng.choice(["M", "F", "MN", "FS"]),
            "Birthdate": _rand_date(years_back=14),
            "Weight":    str(_rand_weight(species)),
        })

    # ── Build CSVs ───────────────────────────────────────────────────────────
    def _to_csv(rows: list[dict]) -> bytes:
        buf = io.StringIO()
        if not rows:
            return b""
        writer = csv.DictWriter(buf, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
        return buf.getvalue().encode("utf-8")

    # ── Pack into ZIP ────────────────────────────────────────────────────────
    zip_buf = io.BytesIO()
    with zipfile.ZipFile(zip_buf, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("clients.csv",  _to_csv(clients))
        zf.writestr("patients.csv", _to_csv(patients))

    return zip_buf.getvalue()


if __name__ == "__main__":
    import sys, os
    out_path = sys.argv[1] if len(sys.argv) > 1 else "avimark-export.zip"
    data = generate_avimark_zip()
    with open(out_path, "wb") as f:
        f.write(data)
    print(f"Generated {out_path} ({len(data):,} bytes)")
    print("Contents: clients.csv (621 records), patients.csv (847 records)")
