"""Shared configuration for the site builders: how the binder maps to the
three training days, and the wording on the signature sheets."""

# How each binder section is delivered. Day 1 and Day 2 are live virtual
# sessions -- the site is the material staff follow along with and refer back
# to, not a self-paced course. The mapping is inferred from certificate topic
# names and still needs the training department to confirm it.
DELIVERY = {
    "drc-policies": "day1",
    "incident-management-abuse": "day1",
    "drivers-safety": "day1",
    "disaster-preparedness": "day1",
    "independent-trainings": "independent",
    "alternative-routes": "day2",
    "medication-administration": "day2",
}

SCHEDULE = [
    {"key": "day1", "label": "Day 1",
     "how": "Virtual, on Teams",
     "blurb": "Live session with the training department. The sections below are "
              "what you'll be walked through. Open them during the meeting or "
              "come back to them any time."},
    {"key": "independent", "label": "Independent trainings",
     "how": "On your own, before Day 2",
     "blurb": "Work through these yourself between the two virtual sessions."},
    {"key": "day2", "label": "Day 2",
     "how": "Virtual, on Teams",
     "blurb": "Second live session. Same idea: the material is here to follow "
              "along with and to look back at afterwards."},
    {"key": "day3", "label": "Day 3",
     "how": "In person",
     "blurb": "Skills session, fit testing, and Q&A with your trainer. Nothing "
              "to read here beforehand.",
     "items": ["FA/CPR/AED skills session", "Fit testing",
               "Review of annual training materials", "Q&A"]},
]

FIRE_TOPICS = [
    "Fire Prevention and Safety (fire hazards, safety of closed doors)",
    "Fire Extinguishers (use of, type, and placement)",
    "Evacuation Procedures and Evacuation Plan", "Smoking Policy",
    "Procedures for Emergency Notification (local fire department)",
    "Fire Drills, Inspections, & Records",
    "Smoke Detectors and Alarms (placement and general maintenance)",
    "Designated Meeting Areas", "Emergency Contact Information",
    "Responsibilities During a Fire", "Fire and Disaster Plans",
    "Activating the Alarms", "Fire Safety Training DVD",
]

# The packet says "all 15 sections"; the binder has 7. The count is dropped
# until the training department settles it.
ATTESTATION = (
    "I attest that I have read and reviewed all sections of the Annual Training "
    "Binder. I understand the material covered and acknowledge my responsibility to "
    "apply this training in my daily work supporting the people served by Shared "
    "Support, Inc. I certify that I have completed the Shared Support, Inc. training "
    "and policies documented above. All my questions have been answered to my full "
    "and complete satisfaction."
)

# Where signed sheets go until the fill-and-flatten submission endpoint exists.
# With no endpoint configured, the sign page opens the staff member's own mail
# app with the three sheets filled in and addressed here, so the email itself
# says who sent it. Change this one line to redirect submissions.
SIGN_TO = "rwilliams@sharedsupport.org"

# Display-level title fixes for filename artifacts. Same rule as CORRECTIONS
# in the extractor: the source file still carries the old name, so each entry
# is a rename someone owes.
TITLE_FIXES = {
    "First Aid - CPR Referance Card": "First Aid / CPR Reference Card",
    "Frequently Asked Questions - Steph": "Frequently Asked Questions",
}

# Documents that are licensed third-party material. Shown as scanned pages
# only, never re-typeset, with a notice.
LICENSED = {
    "first-aid-cpr-referance-card":
        "American Red Cross reference card. Licensed material, shown as the "
        "printed card. Do not copy, edit, or redistribute it outside Shared Support.",
}
