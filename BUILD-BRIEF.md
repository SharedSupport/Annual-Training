# Annual Training site — build brief

Handoff notes for picking this up in Claude Code.

## Source: the paper binder folders, not the PDF

The zip is the better source and the digital binder should stop being the input.

The seven numbered folders match the printed table of contents exactly. The PDF
bookmarks never did — they had 9 entries, invented a standalone MANDT section, dropped
Independent Trainings, and pinned Medication Administration to a single page. Every
question I flagged earlier about section boundaries is answered by the folder tree.

Each policy is also its own file with a revision date in the filename, so the site can
tell staff what they're reading and when it last changed. That was impossible from the
flattened binder.

**The paper files are newer than the digital binder.** The InDesign export was built
03/04/2026. These are not: Abuse Policy 7.10.26, Fleet Safety Program 07.13.26, Community
Participation July2026. Anyone currently reading the digital binder is reading stale
policy — worth raising with the training department independent of this project.

### What the extractor does

    python extract_binder.py "Annual Training - Paper Binder" --out content

61 PDFs, 646 pages. Output is a section → document tree, not a page sequence:

| Section | Documents | Image-only | Print packets |
|---|---|---|---|
| DRC: Policies | 15 | 1 | 2 |
| Incident Management & Abuse | 1 | 0 | 0 |
| Driver's Safety | 4 | 0 | 2 |
| Disaster Preparedness | 1 | 0 | 1 |
| Independent Trainings | 7 | 3 | 3 |
| Alternative Routes | 12 | 4 | 2 |
| Medication Administration | 1 | 0 | 0 |

Roughly 371k characters of clean text across 41 readable documents.

**Duplicates are excluded.** Every section carries an "Easy Print …" and/or "… Packet"
file that repeats the section's content with cover pages added. Extracting those would
duplicate every policy, so they're kept as the section's printable download instead,
which is where the print option lives.

For most sections they are exact duplicates — Drivers Safety Packet and Easy Print
Driver's Safety are both 5,707 characters; Disaster Plan and its Easy Print are both
22,692.

**Independent Trainings is the exception, and it matters.** The Medicaid Waiver & CP
packet is *not* the individual files concatenated — its Community Participation section is
a different, older version of that document. Page by page against Community Participation
July2026.pdf, none of the four pages match: the packet's page 3 carries a paragraph on CP
punch notes that the standalone file doesn't have, and the standalone has a "How to clock
in?" activity table the packet doesn't. Whoever prints the packet is handing out
superseded CP guidance. Reconcile the two before either is used.

Filenames are inconsistent enough to need normalising: underscores, leading index numbers
("2 - Link to TED Talk"), and run-together words ("SexualHealthPersonalRelationsSexuality
Policy2019", "Incident ManagementPolicyCURRENT2025"). `tidy()` handles those, and the
revision-date regex whitelists real month names so "Policy2019" isn't parsed as a date.

### Retired content

`EXCLUDE` in the extractor holds files that stay off the site, with the reason recorded so
a future re-run doesn't quietly reinstate them. Currently one entry:

- **How to use DCI cheat sheet** (4 pages). DCI is retired; time and attendance now lives
  in iCM. Replaced on the Independent Trainings page by a link to the Time & Attendance
  help guide (https://sharedsupport.github.io/ICM-STA-Guide).

Two follow-ons that removing the file does not solve:

1. **The print packets still contain those four pages.** The packets are just their folder
   concatenated — Medicaid Waiver & CP Rules Packet is 13 pages, exactly Community
   Participation (4) + DCI cheat sheet (4) + Medicaid Waiver Compliance Policy (5). All
   three Independent Trainings packets need regenerating, or the print link hands staff the
   document the site just removed. The extractor flags any printable sitting beside an
   excluded file and the prototype marks it "needs regenerating".
2. **DCI was also referenced inside another policy.** The HEAVY HITTER LIST in DRC Policies
   said "Attendance Records, DCI clock in and clock out and mileage punches should be
   completed in real-time." That is now corrected to iCM on the site via `CORRECTIONS`
   (below), but the source PDF still says DCI.

### Display corrections

`CORRECTIONS` holds wording fixed on the site because the source document is out of date.
Each entry must match exactly once; a zero or multiple match warns rather than silently
doing nothing, so a source revision that changes the surrounding text can't quietly put
the stale wording back in front of staff.

Current entries:

| Document | Change | Why |
|---|---|---|
| HEAVY HITTER LIST | "DCI clock in and clock out" → "iCM clock in and clock out" | DCI retired; time & attendance is in iCM |

**These are display-level overrides, and each one is a source edit someone still owes.**
The site and the PDF now disagree about what the policy says. For a compliance document
that gap should be short-lived — if a surveyor pulls the file from the binder, it says
DCI. Treat this list as a to-do for the training department, not a permanent layer. If it
starts growing, the answer is to fix the documents, not to add more entries.

### Gaps worth knowing

- **Medication Administration has one 2-page image-only file** ("Topics to be covered").
  There is effectively no readable med admin content in the binder. If Day 2 covers it
  live, that's fine — but the section will look empty next to the others.
- **Incident Management and Disaster Preparedness are one document each**, 42 and 13
  pages. Long single documents on a phone want in-page headings and a jump list.
- **Nine image-only files** including PBIS MANDT (29 pages, 8.4 MB) and the Red Cross
  reference card. These stay as page images with a download.
- **"First Aid - CPR Referance Card"** has a typo in the filename, which becomes its title
  on the site.
- The certificate lists Community Participation Rules under Day 2, but the CP files live
  in the Independent Trainings folder. One of the two is wrong.

## Presentation

Text everywhere a text layer exists; page images only for the nine scanned files. No
embedded PDF viewer — that reintroduces exactly what's being fixed: no reflow on a phone,
no search, a large download.

Each section also links its existing "Easy Print" packet for anyone who wants paper. The
print stylesheet on the signature page produces the three sheets cleanly with the
navigation dropped.

## No login, no completion tracking

Staff reach this from a personal device without signing in, and sections are no longer
marked complete. The signature submission is the confirmation.

That removes the whole progress-persistence question — nothing to store per person, no
cookies, no session. It also removes the reason to have accounts at all for the reading
side.

One consequence to be deliberate about: **an unauthenticated form can be submitted by
anyone, under any name.** For a compliance record that matters. It's manageable rather
than blocking, because there are human checks either side of it — the training department
knows who attended the two Teams sessions, and Day 3 is in person. Practical mitigations,
cheapest first:

- Reconcile submissions against the roster rather than treating the form as the roster.
  A submission from someone not on the list is a flag, not a record.
- Capture UTC timestamp, source IP, and user agent with every submission.
- Email the completed packet to the staff member's directory address, never to an address
  typed into the form. A wrong name surfaces immediately.
- If a stronger link is wanted later without building logins, a per-person link emailed at
  the start of training identifies the submitter without a password.

Rate-limit and CAPTCHA the endpoint. It's a public unauthenticated POST that generates
PDFs and sends mail.

## Signature packets

Both blank packets are already fillable AcroForms with named fields. This is a large
shortcut: the site never re-typesets the certificates. It fills the existing blank PDF and
the output is byte-identical to what the training department already uses.

Field names are suffixed by track — `employee_name_recert` / `employee_name_review`, and
likewise for `job_title`, `training_date_range`, `day1_date`, `day2_date`, `day3_date`,
`staff_signature`, `trainer_date_p1`, `fire_employee_name`, `fire_employee_signature`,
`fire_training_date`, `facpr_date_top`, `facpr_employee_name`,
`facpr_employee_signature`. 14 fields per packet, 3 pages each.

Fill with pypdf (`update_page_form_field_values`) and flatten before storing, or the values
stay editable.

### The two packets differ on one page

Pages 1 and 2 (Annual Training certificate, Fire Safety) are identical across both files.
Only page 3 differs:

| | RECERT | REVIEW |
|---|---|---|
| Title | FA/CPR/AED - Recertification | FA/CPR Skill Session - For Review ONLY |
| Hours | 2.75 | 2.0 |
| Type label | FA/CPR/AED Recertification - 2.75 Hours | FA/CPR/AED Review - 2 Hours |

Track is a per-staff attribute set by the trainer, not something staff pick for themselves —
it determines credentialed hours. The prototype's toggle is there to show the branch; in
the real build it's read-only and comes from the roster.

### Submission and email

Sign → fill → flatten → store → email, in that order. Email is delivery, not the record:

- Store the flattened PDF in Blob under a versioned/immutable container. That's the
  artifact a licensing surveyor asks for.
- Email a copy to the training department and the staff member's **directory** address,
  never an address typed into the form.
- Record the e-signature audit row alongside: staff ID, typed name, UTC timestamp, source
  IP, user agent, and `content_version_id`. Typed name plus that trail is a defensible
  e-signature under ESIGN/UETA, but confirm PA licensing doesn't require wet signature for
  these specific records before retiring paper.
- Graph `sendMail` from a service mailbox is the cleaner path than SMTP here.

The trainer signature is currently pre-printed on the blanks — Jessica McKee-Snyder signs
before staff complete anything. Worth deciding whether that stays a static image or becomes
a real countersign after the fact, which is the stronger record.

## Discrepancies found in the packets

These need answers from the training department; several block a truthful attestation.

1. **"all 15 sections."** The attestation text says 15. The binder has 9 bookmarked
   sections and the printed table of contents lists 7. Staff can't attest to reading 15
   sections on a site that shows 9. Either the number is stale or the section definition
   differs from the binder's — the prototype drops the count until this is settled.
2. **Address mismatch.** Page 1 and page 3 footers read 218 Bridge Avenue; the Fire Safety
   page 2 footer reads 210 Bridge Avenue. Present in both packets, so it's a template typo.
3. **Hours arithmetic.** The Annual Training certificate says 22.5 total hours. FA/CPR is
   then certified separately at 2.75 or 2.0. But Day 3 on the 22.5-hour certificate lists
   "FA/CPR/AED Skills Session" as included. Is that double counted, and does a staff
   member's total differ by 0.75 hours depending on track?
4. **The certificate covers more than the binder.** Roughly 27 of the listed topics —
   Mission Statement, Worker's Compensation, Fatal Five HCQU, Fit Testing, the TED Talk —
   have no corresponding binder content. The site can only carry the reading portion; the
   rest stays a trainer-recorded or external activity.
5. **Day 3 can't be self-serviced.** Skills session, fit testing, and Q&A are in-person.
   Those need a trainer-side confirmation before the packet can be issued, which means a
   second role in the app, not just staff accounts.

## Open decisions

- **Identity.** Per-person login is required for tracker submission. Is there an existing
  directory to authenticate against, or does this need its own?
- **Retention.** A signed training sheet is a compliance record. Confirm how long it has
  to be retained and in what form before designing the submission table.
- **Delivery mapping.** Day 1 and Day 2 are live Teams sessions, so the site is
  follow-along and reference material rather than a course. The section-to-day mapping
  (Day 1: DRC Policies, Incident Management, Driver's Safety, Disaster Prep; Independent:
  section 5; Day 2: Alternative Routes, Med Admin) still needs the training department to
  confirm it — especially the Community Participation placement noted above.
- **FA/CPR track.** With no login, the site can't know which track a staff member is on,
  so the prototype asks them. Their trainer tells them which applies — but that's
  self-reported, and it sets credentialed hours. Worth deciding whether the training
  department corrects it on receipt instead.
- **Retrain rules.** Does a mid-year content republish reset completion for staff who
  already signed?
- **Wet signature.** Whether PA licensing accepts a typed-name e-signature with audit trail
  for these records, or paper has to stay.

## About the prototype

`training-site-prototype.html` is a single self-contained file with real extracted content
embedded. Completion state is in memory only — it resets on reload, and that's deliberate:
in the real build the tracker is the source of truth, not the browser.

Design notes, so the Claude Code build doesn't drift:

- Palette and section colors are lifted from the printed binder — the maroon and gold of
  the wordmark, and the actual tab colors, so the web nav maps 1:1 to the tabs staff
  already recognize.
- Body type is a Minion-adjacent serif because the source is set in Minion Pro. The binder
  should still feel like the binder.
- The tab rail fills in as sections are finished. That's the one piece of motion; the
  rest is static on purpose.
- No binder page numbers anywhere. Navigation is section and heading anchors. The corpus
  contains exactly one page cross-reference ("see page 1 of this policy") and it's
  internal to a policy document, so nothing breaks.
- Rail collapses to a bottom sheet under 860px. A lot of this audience is reading on a
  phone mid-shift, not at a desk.
