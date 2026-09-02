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

# What the certificate lists under each day. Copied from the blank packet so
# the sign page reads like the paper sheet; many of these topics have no
# binder content and are covered live.
CERT_TOPICS = {
    "day1": [
        "Mission Statement", "Self Determination", "Circle Meetings",
        "Continuous Quality Improvement", "Worker's Compensation", "Community Inclusion",
        "Relationship Building", "Person-Centered Practices/IDD",
        "Department Issued Policies and Procedures",
        "Safe and Appropriate Use of Behavior Supports", "Confidentiality Policy",
        "Family Dynamics", "Fundamental/Individual Rights and Choices",
        "Sexual Health, Personal Relationships & Sexuality Policy",
        "Job Description/Staff Responsibilities", "Recognizing and Reporting Incidents",
        "Emergency On-Call Procedures", "Use of Personal Vehicle Policy",
        "Standard Universal Precautions", "6400/6500 Regulations",
        "Policies & Procedures of the Home", "Trauma Informed Support",
        "PBIS MANDT Training", "MANDT Trauma Overview", "Incident Management Policy",
        "Abuse Policy", "Emergency Disaster Preparedness",
        "Power/Heat Source Outage Procedure", "Disaster Preparedness Policy",
        "Driver's Safety and Fleet Policy",
    ],
    "independent": ["Compliance Policy/Medicaid Waiver",
                    "Video: TED Talk - Disabling Segregation",
                    "Adult First Aid/CPR/AED Learning Course"],
    "day2": ["Alternative Routes", "Oxygen Storage Policy", "Fatal Five HCQU",
             "Community Participation Rules", "Diversity and Acceptance Training",
             "Med Admin Review"],
    "day3": ["FA/CPR/AED Skills Session", "Fit Testing",
             "Review of Annual Training Materials", "Q&A Session"],
}

# Page 3 of the packet, per track. The track is set by the trainer.
FACPR = {
    "recert": {"title": "FA/CPR/AED - Recertification (2.75 Hours)", "hours": "2.75 Hours",
               "description": "Complete Adult First Aid/CPR/AED recertification requirements.",
               "type": "FA/CPR/AED Recertification - 2.75 Hours",
               "button": "Recertification (2.75 hours)"},
    "review": {"title": "FA/CPR Skill Session - For Review ONLY", "hours": "2.0 Hours",
               "description": "Demonstrate First Aid and CPR skills post a review course.",
               "type": "FA/CPR/AED Review - 2 Hours",
               "button": "Review only (2.0 hours)"},
}
FACPR_OBJECTIVES = [
    ("Choking Adult", ["Responsive", "Non-Responsive"]),
    ("CPR Adult", ["2 minutes/5 sets of compressions & breaths with face shield", "AED Adult"]),
]
TRAINER = "Jessica McKee-Snyder"
TRAINER_SIGNATURE = "static/trainer-signature.png"   # as pre-printed on the packet
TRAINER_DEPT = "Training Department"
# Pages 1 and 3 of the packet say 218; page 2 says 210 (known typo). 218 is used.
FOOTER_ADDRESS = ("218 Bridge Avenue \u00b7 Sunbury, PA 17801 \u00b7 Phone: 570.286.4982 \u00b7 "
                  "Fax: 570.286.4984 \u00b7 www.sharedsupport.org")

# Video embedded above a document's text.
EMBEDS = {
    "link-to-ted-talk": {
        "title": "Disabling segregation: Dan Habib at TEDxAmoskeagMillyard",
        "src": "https://www.youtube.com/embed/izkN5vLbnw8?si=IS6SQyYKb_jEBTMj",
    },
}

# Documents shown as page images even though they have a text layer: forms
# and diagrams whose extracted text reads badly. Text still feeds search.
AS_PAGES = {
    "auto-accident-form": "a form with an accident-scene diagram; the text layer reads badly",
}

# The packet says "all 15 sections"; the binder has 7. {n} is filled in by
# build_site.py with the number of sections the site actually shows.
ATTESTATION = (
    "I attest that I have read and reviewed all {n} sections of the Annual Training "
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
SIGN_TO = "TrainingDept@sharedsupport.org"

# Display-level title fixes for filename artifacts. Same rule as CORRECTIONS
# in the extractor: the source file still carries the old name, so each entry
# is a rename someone owes.
TITLE_FIXES = {
    "First Aid - CPR Referance Card": "First Aid / CPR Reference Card",
    "Frequently Asked Questions - Steph": "Frequently Asked Questions",
}

# Documents that are licensed third-party material. Never re-typeset, never
# offered as a download, and not reproduced at all on the public site: page
# images appear only when build_site.py runs with --serve-licensed, for a
# host behind sign-in.
LICENSED = {
    "first-aid-cpr-referance-card":
        "American Red Cross reference card. Licensed material, shown as the "
        "printed card. Do not copy, edit, or redistribute it outside Shared Support.",
}
