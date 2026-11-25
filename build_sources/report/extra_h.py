s.append(PageBreak())
s += [p("Part H - Additional free datasets (second download round)", H1),
      p("Written on 17 Nov 2026. These two datasets are free and open (CC BY 4.0), so I downloaded them after you approved the suggestion. "
        "As in Part G, I have <b>not</b> opened or visually inspected the images.")]

s += [p("H1. Downloaded and verified", H2)]
s.append(table([
    ["Dataset", "Source and licence", "What is inside", "Verification"],
    ["Infectious Keratitis Dataset (multimodal slit-lamp)", "Figshare DOI 10.6084/m9.figshare.28578860.v1, CC BY 4.0. Two hospitals: Zhejiang Eye Hospital (ZEH) and Aier Guangming Eye Hospital (AGEH).",
     "1,373 slit-lamp JPEGs, 4.0 GB. Classes (folder names): HSK herpes simplex, BK bacterial, FK fungal, other corneal abnormalities. AGEH 429 files (BK 57, FK 20, HSK 138, other 214). ZEH 944 files (BK 93, FK 66, HSK 310, other 475). Three illumination modes per the dataset description: slit-beam, diffuse white, cobalt-blue with fluorescein.",
     "MD5 of both zips matches Figshare; zip CRC clean."],
    ["Eye Diseases Classification with Symptoms", "Mendeley Data DOI 10.17632/n9zp473wfw.2, CC BY 4.0.",
     "2,298 images plus 2 notebooks, 44 MB. Classes: Cataract 544, Conjunctivitis 357, Eyelid drooping 525, Normal 649, Uveitis 223. Images were collected from web searches.",
     "SHA-256 of all 2,300 files matches Mendeley's published hashes."],
], [3.2*cm, 4.0*cm, 6.8*cm, 3.0*cm]))

s += [p("H2. Folder locations", H2),
      Preformatted(r"""D:\Capston_Project\datasets\
|-- infectious_keratitis_figshare\
|   |-- _download\AGEH_Dataset.zip  ZEH_Dataset.zip
|   `-- raw\AGEH_Dataset\AGEH_Dataset\{BK,FK,HSK,other_corneal_abnormalities}\
|       raw\ZEH_Dataset\ZEH_Dataset\{BK,FK,HSK,other_corneal_abnormalities}\
`-- eye_disease_classification_mendeley\
    |-- _download\eye_disease_classification.zip
    `-- raw\...\{Cataract,Conjunctivitis,Eyelid,Normal,Uveitis}\  + 2 .ipynb notebooks
""", ParagraphStyle("t3", fontName="Courier", fontSize=7, leading=8.8)),
      p("The two .ipynb notebooks in the Mendeley set are third-party code. I did not run them.")]

s += [p("H3. Cautions before using them", H2),
      bullets([
        "<b>Image counts differ from the description.</b> The Figshare description says ZEH has 475 images from 380 eyes and AGEH has 429 images from 239 patients. "
        "The folders hold 944 and 429 files. ZEH's 944 is about twice the described 475, so some files may be extra views or illumination modes. I have not resolved this; check the file names and any metadata before counting classes.",
        "<b>Several images per eye or patient.</b> Split by patient or eye, never by image, or the same eye lands in both train and test. The folder names carry no patient ID, so find the mapping first.",
        "<b>Eye Diseases Classification is web-sourced.</b> Provenance, labeling and duplicates are unverified, and the images are not clinical-grade. Use it only for prototyping and pre-training. Keep it out of every validation and test set.",
        "<b>Class meaning:</b> Eyelid drooping and uveitis are not in the report's label taxonomy. Decide whether to map, drop or add them.",
        "<b>Not yet checked:</b> image content, duplicates between the two keratitis hospitals, and label correctness.",
      ])]

s += [p("H4. Where each is used", H2)]
s.append(table([
    ["Dataset", "Report steps", "Use"],
    ["Infectious Keratitis", "5, 7, 8", "Cornea condition classification (urgent vs. other); feeds the 'Urgent' triage level for suspected infection; two-hospital data allows a first cross-hospital test (train on one, test on the other)."],
    ["Eye Diseases Classification", "5 (prototype)", "Early conjunctivitis and cataract prototyping, and example symptom wording for the questionnaire (step 8). Not for evaluation."],
], [4.0*cm, 2.5*cm, 10.5*cm]))

s += [p("H5. Coverage summary after both rounds", H2)]
s.append(table([
    ["Dataset", "Region / condition", "Annotation type", "Quality tier"],
    ["Nuclear Cataract (G)", "Lens: nuclear cataract", "None in download (grades missing)", "Clinical, single hospital"],
    ["SUSTech-SYSU (G)", "Cornea: ulcer", "Cornea and ulcer masks", "Clinical, single hospital"],
    ["Infectious Keratitis (H)", "Cornea: HSK, bacterial, fungal, other", "Image-level class", "Clinical, two hospitals"],
    ["Eye Diseases Classification (H)", "Cataract, conjunctivitis, uveitis, eyelid", "Image-level class", "Web-sourced, prototype only"],
], [4.4*cm, 5.0*cm, 3.8*cm, 3.8*cm]))
s += [Spacer(1, 4),
      p("<b>Still missing:</b> pterygium, sclera yellowing, pale inner eyelid, and lens, eyelid and sclera segmentation masks. "
        "Those need CatScreen, SLID, EyeHealer or your own hospital data (see G3). "
        "<b>Totals so far:</b> 4 datasets: about 3,400 clinical slit-lamp images (counting files) plus about 2,300 web-sourced images. Disk use is about 6.0 GB extracted plus about 5.9 GB of original zips.")]
