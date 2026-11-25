"""Patient FAQ for the offline assistant: common questions with safe, general answers, matched by meaning
(TF-IDF similarity over several phrasings and keywords per entry), so differently worded questions still find
the right answer. Education only: no diagnosis, no medicine names or doses."""
from __future__ import annotations

import re
from functools import lru_cache

SEE = " If you are worried, please show your eyes to an eye doctor."

FAQ = [
    # ---- infection and spread
    (["is keratitis contagious", "can keratitis spread to others", "will my family catch it"], "contagious spread catch family",
     "Bacterial and fungal keratitis usually do not spread from person to person the way 'pink eye' does. Herpes "
     "keratitis comes from a virus that can pass by touch. Washing hands, not touching the eye and not sharing towels "
     "keeps everyone safe."),
    (["is trachoma contagious", "how does trachoma spread", "can children catch trachoma"], "trachoma spread children flies",
     "Yes. Trachoma spreads through eye and nose discharge, on hands, cloths and towels, and by flies. Children are "
     "affected most. Washing faces daily, not sharing towels and keeping toilets and surroundings clean stop the spread."),
    (["is conjunctivitis pink eye contagious", "what is pink eye", "red sticky eye", "madras eye"], "conjunctivitis pink sticky madras",
     "Conjunctivitis ('pink eye') is inflammation of the thin layer over the white of the eye: red, watery or sticky "
     "eyes. Many types spread easily, so wash hands often and do not share towels. See an eye doctor if there is pain, "
     "light sensitivity or blurred vision, because then it may be something more serious, such as keratitis."),
    # ---- seriousness and outlook
    (["can keratitis cause blindness", "will i lose my eyesight", "is this serious", "can i go blind"], "blind blindness eyesight serious lose vision",
     "Infectious keratitis can scar the cornea and reduce vision if it is not treated in time. Getting checked by an "
     "eye doctor quickly and following their treatment greatly lowers that risk. That is why OcuLens refers uncertain "
     "or worrying results instead of waiting."),
    (["how long does keratitis take to heal", "how many days to recover", "when will my eye get better"], "heal recover days weeks better",
     "It depends on the cause and how early treatment starts: often days to a few weeks, and fungal infections usually "
     "take longer. Keep every follow-up visit, even when the eye starts to feel better."),
    (["can trachoma be cured", "is trachoma treatable", "is trachoma curable"], "trachoma cure cured curable treatable",
     "Yes. Active trachoma is treated with antibiotics given by health workers or eye doctors, and face washing and "
     "clean surroundings prevent it coming back. If the eyelashes have already turned inward, a simple eyelid "
     "operation can protect the eye."),
    (["will i need surgery", "do i need an operation", "corneal transplant"], "surgery operation transplant",
     "Most eye infections are treated with medicines chosen by the eye doctor. Surgery, such as a corneal transplant, "
     "is only needed in some severe cases. Only your eye doctor can decide this after examining the eye."),
    # ---- medicines and home remedies (never prescribe)
    (["what medicine should i take", "which eye drops should i use", "can you prescribe", "tablets for eye infection"], "medicine drops tablet prescribe antibiotic",
     "I can't recommend medicines or drops; the right treatment depends on the exact germ, and only an eye doctor can "
     "choose it. Please do not use leftover, borrowed or over-the-counter drops on a red, painful eye before you see "
     "the doctor."),
    (["can i use home remedies", "rose water in eye", "breast milk in eye", "herbal drops", "honey in eye", "ayurvedic drops"], "home remedy rose water milk herbal honey ayurvedic",
     "Please don't put home remedies such as rose water, milk, honey or herbal liquids into an infected eye. They can "
     "carry germs and make the infection worse. Keep the eye clean and see an eye doctor."),
    (["can i use steroid drops", "old eye drops at home", "drops from the medical shop"], "steroid old leftover shop chemist",
     "Do not use steroid or leftover drops unless an eye doctor prescribed them for this problem. Some, especially "
     "steroid drops, can make fungal or herpes infections much worse."),
    (["how do i put eye drops", "how to apply eye drops"], "apply put instil technique",
     "Wash your hands, tilt your head back, gently pull down the lower eyelid and let one drop fall into the pocket. "
     "Close the eye gently for a minute and do not let the bottle tip touch the eye. Use only the drops your doctor "
     "prescribed, exactly as they told you."),
    # ---- daily life
    (["can i wear contact lenses", "contact lens and infection", "should i remove my lenses"], "contact lens lenses",
     "If your eye is red, painful or blurry, take your contact lenses out and see an eye doctor; do not put them back "
     "until the doctor says it is safe. Never sleep or swim in lenses, and never rinse them with tap water."),
    (["can i go to work", "can my child go to school", "should i stay at home"], "work school office stay home leave",
     "Follow your eye doctor's advice. With an infection that spreads, like conjunctivitis or trachoma, keep good "
     "hygiene: wash hands often, don't share towels, and avoid touching your eyes. Rest if the eye is painful."),
    (["can i drive", "is it safe to drive with blurry eye"], "drive driving vehicle bike car",
     "Do not drive if your vision is blurred, your eye is painful or you are very sensitive to light. Ask someone to "
     "take you to the eye hospital."),
    (["can i watch tv", "mobile phone screen with eye infection", "screen time eyes"], "screen phone mobile tv computer laptop",
     "Screens will not worsen an infection, but tired eyes feel worse. Take breaks: every 20 minutes, look at something "
     "about 20 feet away for 20 seconds. If light hurts your eyes, rest them."),
    (["can i swim", "can i take a bath", "can i wash my face"], "swim swimming bath wash face shower",
     "Washing your face with clean water is fine and helps hygiene; just don't rub the eye. Avoid swimming pools and "
     "lakes until your eye doctor says the eye has healed."),
    (["can i wear makeup", "kajal or kohl in eye"], "makeup kajal kohl eyeliner mascara",
     "Avoid eye makeup such as kajal, kohl or mascara while the eye is infected, and replace old eye makeup afterwards, "
     "because it can carry germs."),
    (["what should i eat", "food for eye health", "diet for good eyes", "can i eat non veg with eye infection",
      "food to avoid with eye infection", "can i eat chicken fish egg", "is curd or cold food bad for eyes"],
     "eat eating food diet vitamin carrot nonveg veg chicken fish egg curd avoid",
     "There is no special food to avoid with an eye infection: normal home food, including eggs, fish, chicken, "
     "curd and fruit, is fine unless your doctor says otherwise. A balanced diet with green leafy vegetables, colourful fruits and vegetables, and enough protein supports eye "
     "health; foods with vitamin A, such as carrots and leafy greens, help the surface of the eye. Food does not cure an "
     "infection, though; treatment by an eye doctor does."),
    (["i am pregnant", "pregnancy and eye infection", "breastfeeding eye drops"], "pregnant pregnancy breastfeeding",
     "Tell your eye doctor that you are pregnant or breastfeeding, so they can choose treatment that is safe for you "
     "and the baby. Please don't use any drops without their advice."),
    (["my child has an eye infection", "baby eye problem", "children eye care"], "child baby kid children infant son daughter",
     "Children's eye problems should always be checked by an eye doctor, and a newborn with red, sticky eyes needs to "
     "be seen urgently. Teach children to wash their face and hands daily and not to share towels."),
    # ---- symptoms
    (["why is my eye red", "red eye causes"], "red redness",
     "A red eye can come from allergy, dryness, conjunctivitis or infection of the cornea. It needs a doctor soon if it "
     "comes with pain, light sensitivity, blurred vision or a white spot on the dark part of the eye."),
    (["why does my eye hurt", "eye pain", "my eye is painful"], "pain hurt painful ache",
     "Eye pain can come from a scratch, an infection of the cornea, inflammation or high eye pressure. Pain together "
     "with redness or blurred vision should be checked by an eye doctor soon, and severe pain the same day."),
    (["my eye is watering", "watery eyes", "tears all the time"], "watery watering tears",
     "Watery eyes are common with allergy, dryness, irritation or infection. If watering comes with pain, redness or "
     "blurred vision, see an eye doctor."),
    (["my eyes itch", "itchy eyes allergy", "my eyes are itching"], "itch itchy itching itches allergy",
     "Itchy eyes are often due to allergy. Avoid rubbing, which can harm the cornea; a cool, clean compress can soothe "
     "them. See an eye doctor if itching continues or comes with pain or discharge."),
    (["my vision is blurry", "blurred vision", "cannot see clearly"], "blur blurry blurred unclear vision",
     "Blurred vision can simply mean you need glasses, but it can also come from infection or other eye disease. "
     "Get an eye test; and if blurring started suddenly or with pain, go the same day."),
    (["light hurts my eyes", "sensitive to light", "photophobia"], "light sensitive photophobia bright",
     "Pain in bright light is a common sign of corneal infection or inflammation inside the eye. Please see an eye "
     "doctor soon, especially if the eye is also red or blurry."),
    (["something is in my eye", "dust in eye", "foreign body"], "dust sand foreign body something stuck",
     "Don't rub. Blink and rinse the eye gently with clean water. If something is still stuck, the eye stays painful, "
     "or it was hit by metal or a plant, see an eye doctor today: scratches can become infected."),
    (["what is a stye", "bump on eyelid"], "stye bump eyelid swelling boil",
     "A stye is a painful red bump on the eyelid from a blocked, infected gland. A warm, clean compress a few times a "
     "day often helps; don't squeeze it. See a doctor if it grows, spreads or affects vision."),
    (["dry eyes", "gritty burning eyes"], "dry gritty burning",
     "Dry eye causes gritty, burning or tired eyes, often worse with screens, wind or air conditioning. Blink often and "
     "take screen breaks. An eye doctor can advise on lubricating drops if needed."),
    # ---- other eye diseases (outside what OcuLens screens)
    (["what is cataract", "does oculens check cataract"], "cataract lens cloudy",
     "A cataract is clouding of the eye's natural lens, causing slowly blurring vision; it is treated with a safe, "
     "routine operation. OcuLens does not screen for cataract; an eye test will check for it."),
    (["what is glaucoma", "does oculens check glaucoma"], "glaucoma pressure optic nerve",
     "Glaucoma damages the optic nerve, often with no early symptoms, and the vision it takes cannot be restored. "
     "Regular eye checks after age 40, or earlier with a family history, catch it early. OcuLens does not screen for "
     "glaucoma."),
    (["i have diabetes", "diabetes and eyes", "diabetic eye"], "diabetes diabetic sugar retina",
     "Diabetes can damage the retina at the back of the eye, often without early symptoms. People with diabetes need a "
     "dilated eye check at least once a year. OcuLens looks at the front of the eye, so it does not check this."),
    # ---- allergy and long-standing problems
    (["i have eye allergy for many years what should i follow", "eye allergy since years", "chronic eye allergy",
      "allergic conjunctivitis", "my eyes are allergic", "how to control eye allergy", "eye allergy precautions"],
     "allergy allergic allergies years long chronic follow precautions control season dust pollen",
     "Long-standing eye allergy (allergic conjunctivitis) is very common, and while it often comes back with seasons "
     "or dust, it can be kept well under control. What helps most:\n"
     "- Don't rub your eyes. Years of rubbing can thin and bulge the cornea (keratoconus), which blurs vision.\n"
     "- When they itch, splash cool, clean water on closed eyes or use a cool compress.\n"
     "- Cut down triggers: dust, pollen, smoke and pets. Wash your face and hands after coming home, change pillow "
     "covers weekly, and wear sunglasses outdoors.\n"
     "- Don't keep using steroid eye drops bought from a chemist; long-term use without a doctor can cause glaucoma "
     "and cataract.\n"
     "Because it has lasted so long, see an eye doctor for a long-term plan: they can prescribe safe anti-allergy "
     "drops for regular use and check that your cornea is healthy."),
    (["what triggers eye allergy", "dust allergy eyes", "pollen season eyes itching"], "trigger dust pollen season smoke pet",
     "Common triggers are dust and dust mites, pollen (worse in some seasons), smoke, pet hair, strong perfumes and "
     "some cosmetics. Keeping a simple note of when your eyes flare up helps you and your eye doctor find your own "
     "triggers."),
    (["is eye rubbing harmful", "i rub my eyes a lot", "what is keratoconus"], "rub rubbing keratoconus thin cornea",
     "Yes, frequent hard rubbing can harm the eye. Over years it is linked to keratoconus, where the cornea thins and "
     "bulges, causing blurred, changing vision. If your eyes itch often, treat the cause with an eye doctor instead "
     "of rubbing."),
    (["is my eye problem hereditary", "does it run in families", "genetic eye disease"], "hereditary genetic family parents run",
     "Some eye conditions run in families, such as glaucoma, some allergies, short-sightedness and keratoconus. "
     "Infections like keratitis and trachoma are not inherited. Tell your eye doctor about eye problems in your family."),
    # ---- eye strain, glasses and screens
    (["my eyes feel tired", "eye strain from computer", "eyes hurt after mobile use", "computer vision syndrome"],
     "strain tired computer mobile laptop screen heavy",
     "Tired, heavy or burning eyes after screens are very common (digital eye strain). Follow the 20-20-20 rule: every "
     "20 minutes look about 20 feet away for 20 seconds. Blink fully, keep the screen an arm's length away and a little "
     "below eye level, and avoid using the phone in a dark room. If it continues, get an eye test; you may need glasses."),
    (["i get headaches", "headache and eyes", "do i need glasses for headache"], "headache head ache forehead",
     "Headaches after reading or screen work can come from an uncorrected glasses power or eye strain, so an eye test "
     "is a good first step. A sudden severe headache with a red, painful eye or blurred vision needs a hospital the "
     "same day."),
    (["my spectacle power is increasing", "my child needs glasses", "short sight myopia in children"], "power spectacle myopia short sight number increasing",
     "Short-sightedness is increasing in children who spend long hours on screens and little time outdoors. At least "
     "one to two hours of outdoor play daily, screen breaks and a yearly eye check help. Children should wear the "
     "glasses prescribed for them; glasses do not make the eyes weaker."),
    (["can i remove my glasses", "laser surgery for glasses", "lasik"], "lasik laser remove glasses specs refractive",
     "Laser vision correction (such as LASIK) can reduce or remove the need for glasses in suitable adults whose power "
     "has been stable for a year or more. An eye surgeon checks the cornea first, because it is not safe for everyone."),
    (["i need reading glasses after 40", "cannot read small print", "near vision weak"], "reading near small print forty presbyopia",
     "From around age 40 almost everyone finds near work harder; this is called presbyopia and is a normal change. "
     "Reading glasses fix it. Get an eye test rather than buying ready-made glasses, so other problems are not missed."),
    (["do eye exercises help", "yoga for eyes", "palming exercise"], "exercise yoga palming natural",
     "Eye exercises and palming can relax tired eyes, but they do not cure infections or remove the need for glasses. "
     "Use them for comfort, not instead of treatment."),
    # ---- everyday symptoms
    (["my eye is twitching", "eyelid twitching", "eyelid jumping"], "twitch twitching jumping flicker",
     "Eyelid twitching is usually harmless and is linked to tiredness, stress, too much tea or coffee, or screen time. "
     "Rest and good sleep usually settle it. See a doctor if it lasts for weeks, closes the eye fully or involves the face."),
    (["my eyes are puffy", "swollen eyelids", "eyelid swelling in the morning"], "puffy swollen swelling eyelid",
     "Puffy eyelids are often due to allergy, poor sleep, salty food or crying. A cool compress helps. See a doctor if "
     "the swelling is painful, red and hot, comes with fever, or affects only one eye and keeps growing."),
    (["dark circles under eyes", "black circles around eyes"], "dark circles black under",
     "Dark circles usually come from genes, tiredness, allergy or thin skin with age, and are not an eye disease. "
     "Good sleep, sun protection and treating allergy can help."),
    (["discharge from my eye", "sticky eyes in the morning", "pus in eye", "eyelids stuck together"], "discharge sticky pus gum morning stuck",
     "Sticky discharge, especially with eyelids stuck together in the morning, is often from conjunctivitis. Clean the "
     "lids with a fresh cloth and boiled, cooled water, wash hands and don't share towels. See an eye doctor if there "
     "is pain, blurred vision, a lot of pus, or if it is a newborn baby."),
    (["burning sensation in eyes", "eyes burning", "air conditioner dries my eyes"], "burning burn sensation air conditioner fan",
     "Burning eyes are often due to dry eye, screens, air conditioning, a fan blowing on the face, smoke or allergy. "
     "Blink often, keep air flow away from your face and drink enough water. If burning continues, an eye doctor can "
     "check for dry eye."),
    (["my eyes are yellow", "yellow eyes jaundice"], "yellow jaundice liver",
     "Yellow whites of the eyes are usually a sign of jaundice, which comes from the liver or blood, not the eye. "
     "Please see a general doctor soon for a check-up and blood tests."),
    (["red spot in white of eye", "blood spot in eye", "bleeding in eye white"], "spot patch bleed bleeding white part",
     "A bright red patch on the white of the eye without pain or vision change is often a small burst blood vessel, "
     "after coughing, straining or rubbing, and fades in one to two weeks. If it follows an injury, keeps coming back, "
     "or you have high blood pressure or take blood thinners, see a doctor."),
    (["i see floaters", "black dots in vision", "spots floating in my eyes"], "floater floaters dots spots floating",
     "A few floaters that have been there for a long time are common and usually harmless. A sudden shower of new "
     "floaters, flashes of light or a shadow over your vision needs an eye doctor the same day."),
    (["night blindness", "cannot see at night", "difficulty seeing in dim light"], "night dim dark vitamin",
     "Difficulty seeing in dim light can come from vitamin A deficiency, cataract, high glasses power or some retinal "
     "conditions. Eat vitamin A rich foods (green leafy vegetables, carrots, papaya, mango, eggs) and get an eye test."),
    (["colour blindness", "i cannot see colours properly"], "colour color blind colours",
     "Colour blindness is usually inherited, is more common in men and does not get worse. An eye doctor can test it; "
     "a sudden change in colour vision needs a check soon."),
    (["my child has a squint", "lazy eye", "crossed eyes"], "squint lazy crossed amblyopia turned",
     "A squint or lazy eye in a child should be checked by an eye doctor early, ideally before age 6, because treatment "
     "works best while the eyes are still developing. Glasses, patching or sometimes surgery are used."),
    (["baby eyes watering", "newborn sticky eye", "blocked tear duct baby"], "newborn baby infant tear duct blocked watering",
     "Watering in a baby is often a blocked tear duct, which usually opens by itself within the first year. Red, swollen "
     "or very sticky eyes in a newborn need to be seen by a doctor urgently."),
    (["can i apply kajal to my baby", "surma in eyes", "kajal safe for eyes"], "kajal surma kohl baby",
     "Doctors advise against kajal or surma in babies' and children's eyes: some contain lead, and the finger or stick "
     "can carry infection. Adults should use clean, branded products and stop during any eye infection."),
    (["cold compress or warm compress", "should i put ice on my eye"], "compress cold warm ice hot",
     "A cool compress (a clean cloth dipped in cool water) soothes itching and swelling from allergy. A warm compress "
     "helps a stye or blocked eyelid glands. Don't put ice directly on the eye, and keep the cloth clean."),
    (["can i use the same eye drops after opening", "do eye drops expire", "share eye drops"], "expire expiry opened share bottle",
     "Most eye-drop bottles should be thrown away about four weeks after opening, even if liquid is left, and drops "
     "should never be shared. Always check the expiry date."),
    (["something went in my eye while cooking", "chilli in my eye", "soap in eye"], "chilli chili soap shampoo onion cooking",
     "Rinse the eye gently with plenty of clean, cool water for several minutes and don't rub it. Mild stinging usually "
     "settles. If pain, redness or blurring continues after an hour, see an eye doctor."),
    # ---- lifestyle and general health
    (["does smoking affect eyes", "alcohol and eyes"], "smoking smoke cigarette alcohol drinking",
     "Smoking raises the risk of cataract and macular degeneration, and worsens dry eye. Heavy drinking can harm the "
     "optic nerve. Stopping smoking is one of the best things you can do for your eyes."),
    (["does sleep affect eyes", "less sleep red eyes"], "sleep sleeping rest tired night",
     "Too little sleep causes red, dry, tired eyes and eyelid twitching. Seven to eight hours of sleep and putting "
     "the phone away before bed help your eyes feel fresh."),
    (["should i wear sunglasses", "is sunlight bad for eyes", "uv protection"], "sunglasses sun sunlight uv",
     "Yes, good sunglasses that block UV light protect against cataract and growths on the eye surface (pterygium), "
     "and help with glare and allergy outdoors."),
    (["high blood pressure and eyes", "bp and eyes", "thyroid and eyes"], "pressure bp hypertension thyroid",
     "High blood pressure can damage the blood vessels of the retina, and thyroid disease can cause bulging, dry or "
     "swollen eyes. People with these conditions should have regular eye checks."),
    (["how often should i get my eyes checked", "regular eye checkup"], "checkup check-up regular often yearly routine",
     "Adults should have an eye check every one to two years, and every year after 40 or with diabetes, high blood "
     "pressure or glasses. Children should be checked before starting school."),
    (["how can i donate my eyes", "eye donation"], "donate donation pledge",
     "Eyes can be donated after death to give corneas to people who are blind from corneal disease. You can pledge "
     "through an eye bank, such as those at major Bengaluru eye hospitals, and should tell your family your wish."),
    (["do i need to cover my eye", "eye patch", "should i bandage my eye"], "cover patch bandage pad",
     "Don't cover an infected eye with a tight bandage unless your doctor tells you to; it can make some infections "
     "worse. Sunglasses can help with light sensitivity."),
    (["i have fever and eye infection", "fever with red eyes"], "fever cold cough flu",
     "Red, watery eyes can come with a cold or flu. A high fever with very painful, swollen eyelids or red eyes needs "
     "a doctor soon."),
    (["how to clean contact lenses", "contact lens care"], "clean cleaning case solution care",
     "Wash and dry your hands, clean lenses only with fresh lens solution (never water or saliva), replace the case "
     "every three months, and follow the replacement schedule. Remove lenses before sleeping and swimming."),
    (["general eye care tips", "how to keep eyes healthy", "what should i follow for healthy eyes"], "healthy tips general keep habits follow",
     "Simple habits keep eyes healthy: don't rub them, wash hands before touching them, take screen breaks, eat green "
     "leafy vegetables and fruit, wear sunglasses outdoors and safety glasses for risky work, never use someone "
     "else's drops, and have an eye check every one to two years."),
    # ---- the screening, results and the app
    (["what does refer mean", "why does it say refer", "do i need to see a specialist"], "refer referral specialist",
     "REFER means the model is not sure enough, or saw possible signs of a condition that needs an eye specialist. It "
     "is a safety step, not a diagnosis: please book a visit with an eye doctor."),
    (["what does confidence mean", "what does the percentage mean"], "confidence percent percentage score",
     "The confidence is how strongly the model favours its top answer. It is not a diagnosis, and a low value means the "
     "model is unsure, which is why such results are referred."),
    (["what is a prediction set", "why are there several possibilities"], "prediction set possibilities several conformal",
     "The prediction set lists every condition the model cannot rule out. It is built so that the true condition is "
     "inside it about 95% of the time; more items mean more uncertainty."),
    (["what does uncertain mean", "model disagreement", "mutual information"], "uncertain disagreement mutual",
     "OcuLens runs ten copies of the model. 'Uncertain' means they disagree with each other, a sign the photo is hard to "
     "read, so a doctor should look at it."),
    (["how accurate is the ai", "can i trust the result", "how reliable is oculens"], "accurate accuracy reliable trust",
     "On held-out test photos it scored 0.81 balanced accuracy for trachoma, 0.68 for ulcer pattern and about 0.42 to "
     "0.49 for the hardest task, keratitis. Good for screening, not good enough to diagnose, so uncertain results are "
     "always referred to a doctor."),
    (["can the ai replace a doctor", "do i still need a doctor"], "replace doctor instead",
     "No. OcuLens is a screening aid that helps decide who should see an eye doctor first. Only an eye doctor can "
     "examine you, confirm the problem and treat it."),
    (["is the screening painful", "does the test hurt"], "painful hurt safe test scan",
     "No. The screening is just a photograph of the front of your eye. Nothing touches the eye."),
    (["is my data private", "who can see my photo", "is my information safe"], "privacy private data safe photo stored",
     "In this prototype, photos and results are stored only on the clinic computer running the portal and are seen by "
     "the logged-in health workers and doctors. Nothing is shared publicly."),
    (["how much does it cost", "is the screening free", "treatment cost"], "cost price fee free money pay",
     "The OcuLens screening in this prototype is free. Treatment costs depend on the hospital; government hospitals "
     "usually cost less. Ask the hospital's help desk about fees."),
    (["how do i book an appointment", "request appointment"], "book appointment visit schedule",
     "Open the case page in the portal and use the appointment request next to the suggested hospitals, or call the "
     "hospital directly. Take your OcuLens report (PDF) with you."),
    (["what happens at the hospital", "what will the doctor do"], "hospital doctor examine examination visit",
     "The eye doctor examines your eye with a slit lamp (a microscope with a bright light), may use a harmless dye to "
     "see scratches or ulcers, and may take a tiny sample from the cornea to find the exact germ before choosing "
     "treatment."),
    (["when should i check again", "follow up screening"], "follow up again recheck repeat",
     "Follow the date your doctor gives. OcuLens can compare a new photo with the earlier one on the Follow-up page to "
     "show whether things improved."),
    (["how do i take a good photo", "the photo is blurry"], "photo picture camera capture focus",
     "Let one eye fill the circle, keep it open, hold the camera steady, and light it from the side to avoid glare. "
     "Wait for the focus bar to turn green before capture."),
    (["how do i protect my eyes", "eye safety at work", "farm work eye protection"], "protect protection goggles safety farm",
     "Wear protective glasses for farm work, grinding or welding; don't rub your eyes; wash your hands before touching "
     "them; and never use someone else's eye drops or makeup."),
    (["what is the cornea"], "cornea clear window",
     "The cornea is the clear, dome-shaped window at the front of the eye. It focuses light, so scars or infections on "
     "it can blur vision."),
    (["what is fluorescein", "why is the eye green in the photo"], "fluorescein dye green stain",
     "Fluorescein is a harmless orange dye eye doctors put in the eye. Under blue light it glows green wherever the "
     "surface of the cornea is damaged, which shows the size of an ulcer."),
    (["who made oculens", "what is oculens", "who are you", "what is your name"], "who made what are you name team",
     "I'm the OcuLens Assistant, part of OcuLens-AI, a capstone research prototype that screens eye photos for "
     "keratitis, corneal ulcers and trachoma and helps people reach the right eye doctor."),
    (["which languages do you speak", "can you speak hindi", "kannada tamil telugu"], "language hindi kannada tamil telugu",
     "With the online assistant I can answer in English, Hindi, Kannada, Tamil and Telugu. In offline mode I answer in "
     "English."),
    (["thank you", "thanks", "ok bye"], "thank thanks bye goodbye",
     "You're welcome. Take care of your eyes, and please see an eye doctor if anything gets worse."),
]


@lru_cache(maxsize=1)
def _index():
    # Words plus character fragments: fragments catch variants such as "contacts" / "contact lens" or
    # "curable" / "cured". On 30 test phrasings this matched 29 correctly (24 with words alone).
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.pipeline import FeatureUnion
    import numpy as np
    docs = [" ".join(qs) + " " + kw for qs, kw, _ in FAQ]
    owner = list(range(len(FAQ)))
    # the same questions in Hindi, Kannada, Tamil and Telugu (pre-translated), so they match without English
    from oculens.assistant.i18n import _table
    table = _table()
    for lang in ("hi", "kn", "ta", "te"):
        t = table.get(lang, {})
        for i, (qs, _, _) in enumerate(FAQ):
            tq = [t[x] for x in qs[:2] if x in t]
            if tq:
                docs.append(" ".join(tq))
                owner.append(i)
    vec = FeatureUnion([("w", TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True)),
                        ("c", TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), sublinear_tf=True))])
    return vec, vec.fit_transform(docs), np.array(owner)


_EXTRA_DOMAIN = {"eye", "eyes", "vision", "sight", "see", "seeing", "doctor", "hospital", "clinic", "nurse", "health",
                 "infection", "infected", "pain", "sore", "sand", "dust", "phone", "sugar", "medicine", "treatment",
                 "report", "result", "scan", "ai", "app", "oculens", "lens", "lenses", "glasses", "spectacles",
                 "eyelid", "eyelids", "eyesight", "allergy", "itching", "itchy", "follow", "symptom", "symptoms"}


@lru_cache(maxsize=1)
def _domain():
    from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS
    words = set()
    for qs, kw, _ in FAQ:
        for w in re.findall(r"[a-z]+", (" ".join(qs) + " " + kw).lower()):
            if len(w) > 2 and w not in ENGLISH_STOP_WORDS:
                words.add(w)
    return words | _EXTRA_DOMAIN


def on_topic(question: str) -> bool:
    """Does the question use any eye / health / OcuLens word? Off-topic questions must not get a random FAQ answer."""
    return any(w in _domain() for w in re.findall(r"[a-z]+", (question or "").lower()))


_FIXES = {"allergi": "allergy", "alergy": "allergy", "alergi": "allergy", "allegy": "allergy", "allergies": "allergy",
          "allergic": "allergy", "ey": "eye", "eys": "eyes", "eyez": "eyes", "iching": "itching", "itchng": "itching",
          "watring": "watering", "paining": "pain", "blurr": "blurry", "doc": "doctor", "dr": "doctor",
          "specs": "spectacles", "spects": "spectacles", "medicin": "medicine", "tablate": "tablet", "lense": "lens",
          "infaction": "infection", "infecton": "infection", "itchy": "itchy", "colour": "colour", "redness": "redness"}


@lru_cache(maxsize=1)
def _vocab():
    return sorted(w for w in _domain() if len(w) >= 4)


def normalise(question: str) -> str:
    """Lower-case, fix common spellings ("allergi", "ey") and snap near-misses to the eye-health vocabulary."""
    import difflib
    out = []
    for w in re.findall(r"[a-z0-9']+", (question or "").lower()):
        w = _FIXES.get(w, w)
        if len(w) >= 5 and w not in _domain():
            m = difflib.get_close_matches(w, _vocab(), n=1, cutoff=0.84)
            if m:
                w = m[0]
        out.append(w)
    return " ".join(out)


@lru_cache(maxsize=1)
def _keywords():
    return [set(kw.split()) for _, kw, _ in FAQ]


_EYE_WORDS = re.compile(r"\b(eyes?|eyelids?|eyesight|vision|sight|see|seeing|cornea|lens|lenses|glasses|spectacles|"
                        r"specs|tears?|blink\w*|pupil|retina|squint|stye|kajal|surma|oculens)\b", re.I)
_OTHER_BODY = re.compile(r"\b(stomach|belly|knee|leg|legs|back|chest|tooth|teeth|ear|ears|nose|throat|skin|hair|"
                         r"hand|hands|foot|feet|joint|joints|period|periods|kidney|heart|lungs?|bones?)\b", re.I)


def other_body_part(question: str) -> bool:
    """Asks about another part of the body and not about the eyes (e.g. "my knee hurts")."""
    q = question or ""
    return bool(_OTHER_BODY.search(q)) and not _EYE_WORDS.search(q)


def on_topic_norm(question: str) -> bool:
    return on_topic(question) or on_topic(normalise(question))


_INDIC = re.compile(r"[ऀ-ॿ஀-௿ఀ-೿]")


def best(question: str) -> tuple[str | None, float]:
    """Best FAQ answer and its score (0..1: the mean of the word and character cosines, plus a small bonus for each
    entry keyword the question uses). Off-topic questions (no eye or health word) score 0."""
    import numpy as np
    raw = question or ""
    indic = bool(_INDIC.search(raw))
    q = normalise(raw)
    if other_body_part(q) or (not indic and not on_topic(q)):
        return None, 0.0
    vec, mat, owner = _index()
    doc_sims = (mat @ vec.transform([raw + " " + q if indic else q]).T).toarray().ravel() / 2.0
    sims = np.zeros(len(FAQ))
    np.maximum.at(sims, owner, doc_sims)      # best phrasing per entry, in any language
    words = set(q.split())
    for i, kws in enumerate(_keywords()):
        sims[i] += min(0.10, 0.05 * len(words & kws))
    i = int(sims.argmax())
    return (FAQ[i][2], float(sims[i])) if sims[i] > 0 else (None, 0.0)
