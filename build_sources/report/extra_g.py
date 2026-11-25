s.append(PageBreak())
s += [p("Part G - Dataset download record (new section)", H1),
      p("Written on 17 Nov 2026. Everything below reflects what was actually done in this session. "
        "I downloaded only the datasets that are openly available. I have <b>not</b> opened or visually inspected any of the images, "
        "so label quality and image content are still unchecked.")]

s += [p("G1. Where the files are", H2),
      Preformatted(r"""D:\Capston_Project\
|-- OcuLens-AI_Step_Log_and_Pre-Implementation_Guide.pdf
`-- datasets\
    |-- DATA_LICENSES.md                 licence and access register
    |-- _verify_report.json              hash and integrity results
    |-- sustech_sysu_corneal_ulcer\
    |   |-- _download\sustech_sysu.zip   original archive (1.16 GB)
    |   `-- raw\  rawImages\ corneaLabels\ ulcerLabels\ corneaOverlay\ ulcerOverlay\
    |             Category information.xlsx   + 3 demo videos
    `-- nuclear_cataract_mendeley\
        |-- _download\nuclear_cataract.zip   original archive (648 MB)
        `-- raw\...\Nuclear Cataract Dataset\<patient 01..115>\ DER\ IZQ\ DATAFILE
""", ParagraphStyle("t2", fontName="Courier", fontSize=7, leading=8.8))]

s += [p("G2. Downloaded and verified", H2)]
s.append(table([
    ["Dataset", "Source and licence", "What is inside", "Verification"],
    ["SUSTech-SYSU corneal ulcer", "Figshare (article 10247501), CC0. Paper: Scientific Data 2020.",
     "712 slit-lamp fluorescein-stained images (JPG); 712 cornea masks; 354 ulcer masks (PNG); overlays; category spreadsheet; 3 demo videos. 2,853 files, 1.25 GB.",
     "MD5 matches Figshare; zip CRC clean."],
    ["Nuclear Cataract Database", "Mendeley Data (DOI 10.17632/6wv33nbcvv.2), CC BY 4.0 (credit required).",
     "1,320 slit-lamp JPEGs from 115 patients, folders DER (right eye) and IZQ (left eye); <b>no LOCS III grade file</b> (correction, 18 Nov: the only spreadsheet is a 165-byte Office lock file, '~$Base de Datos LOCS...xlsx'); per-patient camera metadata file (DATAFILE). Topcon DC-3 camera on a Topcon SL-D7 slit lamp; graded by ophthalmologists at Instituto Conde Valenciana, Mexico. 1,436 files, 687 MB.",
     "SHA-256 of all 1,436 files matches Mendeley's published hashes."],
], [3.0*cm, 4.0*cm, 6.6*cm, 3.4*cm]))

s += [p("G3. Not downloaded, and how to get each", H2)]
s.append(table([
    ["Dataset", "Why I could not download it", "What you need to do"],
    ["CatScreen (IIT Jodhpur), 18,640 slit-lamp images", "Needs a licence agreement.", "Request via the IAB lab page (iab-rubric.org, healthcare datasets) or the authors listed in the TMLR 2026 paper. I could not confirm the request form."],
    ["SLID (Zhejiang), 2,617 images", "Not public yet. The paper says it was token-protected for reviewers and will be on GitHub upon publication. I found no official repository.", "Check the Frontiers data report (DOI 10.3389/fdgth.2025.1716501) periodically, or ask the authors."],
    ["EyeHealer, 2,192 photos", "Access goes through a Data Access Committee, on reasonable request.", "Write to the corresponding authors of Precision Clinical Medicine 4(2):85-92 (DOI 10.1093/pcmedi/pbab009)."],
    ["SBVPI", "Needs a hand-signed form.", "Download and sign the form on sclera.fri.uni-lj.si/datasets.html and email it to the contact named on that page (matej.vitek@fri.uni-lj.si)."],
    ["MOBIUS, OpenEDS", "Form or request needed. MOBIUS is mobile-captured and OpenEDS is VR-headset imagery, so both are low priority now.", "Same page for MOBIUS; OpenEDS access steps were not checked."],
], [4.0*cm, 6.0*cm, 7.0*cm]))
s += [Spacer(1, 4),
      p("<b>Also found:</b> CADMUS (Moorfields and UCL, about 945,000 anterior-segment images from 22,482 patients) is an anterior-segment OCT dataset, not photographs, "
        "and access is by application through INSIGHT. It does not match the slit-lamp image design, so I did not pursue it.")]

s += [p("G4. Problem found and fixed during download", H2),
      p("My first downloads were interrupted when the background shell exited, and I resumed them. Both resumed files then failed integrity checks: "
        "the SUSTech-SYSU zip was 1,211,874,679 bytes with an MD5 that did not match Figshare (expected 1,159,073,143 bytes), and the Nuclear Cataract zip reported a CRC error on a member. "
        "I deleted both and downloaded them again from scratch without resuming. The second copies pass every check listed in G2. "
        "Lesson for later: always verify dataset hashes before training.")]

s += [p("G5. What these datasets do and do not cover", H2),
      bullets([
        "<b>Cornea:</b> SUSTech-SYSU gives cornea masks for all 712 images and ulcer masks for only 354. Single-hospital data (Zhongshan Ophthalmic Center) with fluorescein staining.",
        "<b>Lens / cataract:</b> the Nuclear Cataract set covers nuclear cataract, but the public download has <b>no grade labels</b> (correction, 18 Nov), so it cannot train a grading model until the grades are obtained from the authors. It does not cover cortical, mature or posterior subcapsular types. Single-hospital data from one camera.",
        "<b>Still missing:</b> conjunctivitis, pterygium, sclera yellowing, pale inner eyelid, and eyelid/lens segmentation masks. These need CatScreen, SLID, EyeHealer or your own hospital data.",
        "<b>Splitting:</b> the Nuclear Cataract folders are per patient (115), so split at the patient-folder level. SUSTech-SYSU has no patient identifiers in the files I listed; check the spreadsheet before splitting.",
        "<b>Not yet checked:</b> image content, label correctness, class balance, duplicates, and the meaning of the per-patient data file and the category spreadsheet.",
      ]),
      p("G6. Where each is used", H2)]
s.append(table([
    ["Dataset", "Report steps", "Use"],
    ["SUSTech-SYSU", "4, 5", "Cornea segmentation and ulcer segmentation/grading; also a source of slit-lamp images for synthetic-data experiments (step 3)."],
    ["Nuclear Cataract", "5", "Cataract grading baseline (RQ1 image-only baseline) and Grad-CAM checks (step 7)."],
    ["CatScreen, SLID, EyeHealer (once obtained)", "4, 5, 7", "Anatomy segmentation, larger cataract training set, external test between datasets."],
], [4.0*cm, 2.5*cm, 10.5*cm]))
s += [Spacer(1, 4), p("<b>Suggested next step:</b> inspect a sample of images and masks from both datasets, then build the dataset loader and patient-level split (Step 1 in Part C).")]
