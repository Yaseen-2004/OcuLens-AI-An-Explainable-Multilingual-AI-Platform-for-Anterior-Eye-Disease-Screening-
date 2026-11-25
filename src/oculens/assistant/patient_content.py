"""Patient-facing education content for the OcuLens patient portal (general information, never a diagnosis).
Translations live in translations.json (machine-translated, to be reviewed by native speakers)."""
from __future__ import annotations

TIPS = [
    "Wash your hands before touching your eyes, putting in drops or handling contact lenses.",
    "Every 20 minutes of screen time, look about 20 feet away for 20 seconds.",
    "Never use someone else's eye drops, towel or eye makeup.",
    "Wear protective glasses for farm work, grinding, welding and when bursting crackers.",
    "Green leafy vegetables, carrots, papaya and eggs help keep the surface of the eye healthy.",
    "If your eye is red and painful, take out contact lenses and see an eye doctor.",
    "Splash cool, clean water on closed eyes when they itch, instead of rubbing them.",
    "Good sunglasses that block UV light protect your eyes outdoors.",
    "Children should play outdoors for at least one to two hours a day to protect their eyesight.",
    "After age 40, or with diabetes, have an eye check every year.",
    "Throw away eye-drop bottles about four weeks after opening.",
    "Sleep seven to eight hours; tired eyes are often red and dry.",
]

LEARN = [
    ("The cornea", "The cornea is the clear window at the front of your eye. It focuses light, so an infection or "
                   "scar on it can blur your vision. That is why OcuLens looks at it closely."),
    ("Keratitis", "Keratitis is an infection or inflammation of the cornea. The eye becomes red and painful, waters, "
                  "and may blur or hurt in bright light. It needs an eye doctor quickly."),
    ("Corneal ulcer", "A corneal ulcer is an open sore on the cornea, usually from infection. It is an emergency: "
                      "treatment within a day or two protects your sight."),
    ("Trachoma", "Trachoma is an eye infection that spreads through hands, towels and flies. Washing faces daily and "
                 "keeping surroundings clean stop it. Repeated infections can turn the eyelashes inward."),
    ("Eye allergy", "Allergy makes eyes itchy, red and watery, often with dust or pollen. Avoid rubbing, use a cool "
                    "compress, and see an eye doctor for safe long-term care."),
    ("Dry eye", "Dry eyes feel gritty, burning or tired, often with screens or air conditioning. Blink often, take "
                "breaks and keep fans away from your face."),
    ("Screen time", "Screens do not damage the eyes, but they tire them. Follow the 20-20-20 rule and keep the "
                    "screen an arm's length away."),
    ("Protect your eyes", "Most eye injuries can be prevented with safety glasses. Never rub an eye after dust, "
                          "chemicals or plant matter get in; rinse with clean water instead."),
]

MYTHS = [
    ("Rose water, honey or breast milk can cure an eye infection.",
     "No. They can carry germs and make an infection worse. Only an eye doctor's treatment cures it."),
    ("Wearing glasses makes your eyes weaker.",
     "No. Glasses help you see clearly; they do not change the eye's power."),
    ("Watching TV from close up damages the eyes.",
     "No, but long screen time tires the eyes. Take regular breaks."),
    ("Looking at someone with conjunctivitis spreads it.",
     "No. It spreads by touch: hands, towels and pillows, not by looking."),
    ("Eye drops from the chemist are always safe.",
     "No. Some drops, especially steroid drops, can make infections much worse. Use only what a doctor prescribes."),
    ("Kajal or surma keeps a baby's eyes healthy.",
     "No. Some contain lead, and fingers can carry infection. Doctors advise against it."),
]

SYMPTOMS = [  # (key, label, help)
    ("pain", "Pain", "0 = none, 10 = the worst pain you can imagine"),
    ("redness", "Redness", "How red the eye looks"),
    ("itching", "Itching", "How much the eye itches"),
    ("watering", "Watering or discharge", "Tears, sticky discharge"),
    ("blur", "Blurred vision", "How unclear your vision is"),
    ("light", "Pain in bright light", "Discomfort in sunlight or bright rooms"),
]

DIARY_ALERT = ("Your symptoms are severe today. Please see an eye doctor today, or go to the nearest hospital "
               "emergency department, especially if your vision has dropped suddenly.")
DIARY_WORSE = ("Your symptoms are worse than at your last entry. If this continues for a day, or your vision "
               "drops, please see an eye doctor.")
DIARY_BETTER = "Your symptoms look better than at your last entry. Keep following your doctor's advice."

RESULT_PLAIN = {
    "refer": ("See an eye specialist soon",
              "The photo shows possible signs that need an eye specialist, or the model was not sure. This is a "
              "safety step, not a diagnosis. Please book a visit within the next one or two days, and sooner if "
              "the pain or redness gets worse."),
    "routine": ("No urgent signs found",
                "The model did not find strong signs that need urgent care. A doctor will still review your photo. "
                "If your eye is painful, red or blurry, please see an eye doctor anyway."),
    "pending": ("A doctor will review this", "Your photo has been saved and added to the doctor's review list."),
}


EMERGENCY = [
    "Sudden loss of vision or a dark curtain over your sight",
    "A chemical, acid, lime or cement splash in the eye",
    "An injury to the eye, or something stuck in it",
    "Severe eye pain, or pain with a white spot on the dark part of the eye",
    "Sudden flashes of light or a shower of new floaters",
    "Pain, redness or blurring after eye surgery",
]
FIRSTAID_CHEM = [
    "Rinse the eye at once with clean running water for at least 15 minutes, holding the eyelids open.",
    "Remove contact lenses if they come out easily.",
    "Do not rub the eye and do not put any drops in it.",
    "Go to the nearest hospital, and take the chemical's name or bottle if you can.",
]
FIRSTAID_INJURY = [
    "Do not press on or rub the eye.",
    "Do not try to remove anything stuck in the eye.",
    "Cover the eye gently with a clean cup or shield.",
    "Go to a hospital straight away.",
]
PATIENT_QS = ["What does my result mean?", "What should I do next?", "Which hospital should I visit?",
              "Is it contagious?", "How can I protect my eyes?"]
UI_EXTRA = ["Requested", "Confirmed", "Completed", "Declined", "Cancelled", "Your reviewing doctor",
            "Matched to your last check", "Password changed.", "The current password is not correct.",
            "The new password needs at least 6 characters."]


def all_strings() -> list[str]:
    out = list(TIPS) + EMERGENCY + FIRSTAID_CHEM + FIRSTAID_INJURY + UI_EXTRA + PATIENT_QS
    for t, d in LEARN:
        out += [t, d]
    for m, f in MYTHS:
        out += [m, f]
    out += [lab for _, lab, _ in SYMPTOMS] + [h for _, _, h in SYMPTOMS]
    out += [DIARY_ALERT, DIARY_WORSE, DIARY_BETTER]
    for h, b in RESULT_PLAIN.values():
        out += [h, b]
    return out
