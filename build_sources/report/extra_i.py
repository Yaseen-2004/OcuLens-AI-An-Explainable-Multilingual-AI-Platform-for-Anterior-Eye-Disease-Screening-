s.append(PageBreak())
s += [p("Part I - Third download round and the image total", H1),
      p("Written on 17 Nov 2026, after you asked for many more images. I searched again for free datasets (Hugging Face, Mendeley, Figshare, Zenodo, the ESCRS list of public anterior-segment datasets) "
        "and downloaded the two that are open and relevant. Images were not visually inspected.")]

s += [p("I1. Downloaded and verified", H2)]
s.append(table([
    ["Dataset", "Source and licence", "What is inside", "Verification"],
    ["Trachoma conjunctival photographs", "Figshare DOI 10.6084/m9.figshare.7551053.v1, listed by ESCRS (Niger and Ethiopia). Figshare lists the licence as GPL 3.0 or later, which is unusual for image data; confirm what it allows before any reuse.",
     "1,656 JPEG photographs of the everted upper eyelid, taken with a single-lens reflex camera, plus tfti.csv. Labels: TF (follicular trachoma) positive in 527, TI (intense inflammation) positive in 272. 3.5 GB.",
     "MD5 matches Figshare; tar extracted with a path check."],
    ["Slit-lamp cataract temporal sequences", "PLOS ONE supplementary file on Figshare (DOI 10.1371/journal.pone.0201142.s001), CC BY 4.0.",
     "60 slit-lamp JPEGs: 10 patients with 6 images each, in time order. Small (0.4 MB), but it is the only free time-series set found.",
     "MD5 matches Figshare."],
], [3.2*cm, 4.4*cm, 6.4*cm, 3.0*cm]))

s += [p("I2. Folder locations", H2),
      Preformatted(r"""D:\Capston_Project\datasets\
|-- trachoma_conjunctiva_figshare\   _download\m.tar    raw\m\ image1.jpg ... + tfti.csv
`-- slitlamp_cataract_temporal_figshare\   _download\*.zip   raw\S1_file\0001..0010\
""", ParagraphStyle("t4", fontName="Courier", fontSize=7, leading=8.8))]

s += [p("I3. Cautions", H2),
      bullets([
        "<b>Trachoma is outside your label taxonomy.</b> It is an eyelid / conjunctiva infection photographed in the field, not with a slit lamp. "
        "It can help conjunctiva and eyelid work (steps 4 and 5) and a possible later extension, but do not mix it into the cataract or cornea classes.",
        "<b>Trachoma licence:</b> GPL on a dataset is not a standard choice. Read the original paper and the Figshare page before redistributing anything.",
        "<b>The temporal set is tiny:</b> 10 patients is enough to build and test the follow-up code (step 10), not enough to train a change-detection network.",
        "<b>Split trachoma by person:</b> the CSV has an image key but no person ID. Several photos may come from the same person.",
      ])]

s += [p("I4. Total images collected (all rounds)", H2)]
s.append(table([
    ["Dataset", "Images", "Type", "Round"],
    ["Nuclear Cataract", "1,320", "Clinical slit-lamp", "G"],
    ["SUSTech-SYSU corneal ulcer", "712", "Clinical slit-lamp", "G"],
    ["Infectious Keratitis (ZEH + AGEH)", "1,373", "Clinical slit-lamp", "H"],
    ["Eye Diseases Classification", "2,298", "Web-sourced", "H"],
    ["Trachoma conjunctival photos", "1,656", "Field photographs (SLR)", "I"],
    ["Slit-lamp cataract temporal sequences", "60", "Clinical slit-lamp", "I"],
    ["<b>Total</b>", "<b>7,419</b>", "3,465 slit-lamp + 1,656 field + 2,298 web", ""],
], [6.2*cm, 2.2*cm, 6.0*cm, 2.6*cm]))
s += [Spacer(1, 4), p("Masks, overlays, spreadsheets and videos are not counted. Disk use is about 9.5 GB extracted plus about 9.5 GB of original archives; D: had about 46 GB free before the last download.")]

s += [p("I5. Why free data has run out, and what would add much more", H2),
      p("The free, openly downloadable anterior-eye photo sets are now mostly exhausted. The ESCRS public list is mostly confocal microscopy and OCT, which are different image types. "
        "Large increases only come from datasets that need a request:"),
      ]
s.append(table([
    ["Source", "Images", "Access", "Gain"],
    ["CatScreen (IIT Jodhpur)", "18,640", "Licence agreement", "Largest slit-lamp set; Indian patients"],
    ["SLID (Zhejiang)", "2,617", "Not released yet", "Segmentation plus 13 lesion types"],
    ["EyeHealer", "2,192", "Data Access Committee", "Pixel-level structures and lesions"],
    ["Your hospital partner", "Your choice", "Ethics approval and consent", "The only source with your target population and device"],
    ["Kaggle / Roboflow sets", "Many", "Account and API token needed; quality and licences vary", "Prototype data only; I have no token set up"],
], [4.2*cm, 2.0*cm, 5.4*cm, 5.4*cm]))
s += [Spacer(1, 4), p("<b>If the three request-only datasets are granted,</b> the total would rise from about 7,400 to roughly 30,000 images, with CatScreen supplying most of the increase. "
        "The real limit is the request process, not the downloading.")]
