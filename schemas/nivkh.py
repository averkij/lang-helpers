# Nivkh language scheme
# Maps Leipzig glossing abbreviations to Universal Dependencies features
# Based on grapaul/NivkhKurng/Scheme/Nivkh_atr_val.py

morphdict = {
    "ABL": "Case=Abl",
    "PERL": "Case=Per",
    "LOC": "Case=Loc",
    "DAT": "Case=Dat",
    "INST": "Case=Ins",
    "VOC": "Case=Voc",
    "CAUSEE": "Case=Cau",
    "COM": "Case=Com",
    "COMP": "Case=Cmp",
    "LIM": "Case=Lim",
    "REP": "Case=Rep",

    "CONV": "VerbForm=Conv",
    "NMN": "VerbForm=Vnoun",
    "ATR": "VerbForm=Part",

    "SG": "Number=Sing",
    "DU": "Number=Dual",
    "PL": "Number=Plur",

    "1": "Person=1",
    "2": "Person=2",
    "3": "Person=3",
    "3SG": "Person=3|Number=Sing",

    "IND": "Mood=Ind",
    "DES": "Mood=Des",
    "IMP": "Mood=Imp",
    "COND": "Mood=Cnd",
    "HORT": "Mood=Hort",
    "JUSS": "Mood=Jus",
    "PROB": "Mood=Prob",
    "PROH": "Mood=Proh",
    "ISP": "Mood=Indir",
    "SUBJ": "Mood=Subj",

    "EVID": "Evident=Nfh",

    "INCL": "Clusivity=In",
    "EXCL": "Clusivity=Ex",

    "CAUS": "Voice=Caus",

    "INDEF": "Definite=Ind",
    "ANY": "Definite=Ind",

    "PROG": "Aspect=Prog",
    "ANT": "Aspect=Ant",
    "ITER": "Aspect=Iter",
    "USIT": "Aspect=Usit",
    "RES": "Aspect=Res",
    "COMPL": "Aspect=Compl",
    "SIM": "Aspect=Sim",
    "AVERT": "Aspect=Avert",
    "HAB": "Aspect=Hab",
    "MULT": "Aspect=Mult",

    "NEG": "Polarity=Neg",

    "FUT": "Tense=Fut",
    "POSS": "Poss=Yes",

    "DIM": "Degree=Dim",

    "CL": "Classifier=Yes",
    "PRED": "Predicative=Yes",
    "FOC": "Focus=Yes",
    "EMPH": "Emphatic=Yes",
    "QU": "Question=Yes",
    "COORD": "Coordinating=Yes",
    "REFL": "Reflex=Yes",
    "REC": "Reciprocal=Yes",
    "CONC": "Conces=Yes",
    "ADD": "Add=Yes",

    "DISC": "INTJ",

    "A": "NounType=Agent",
    "L": "NounType=Locat",
    "P": "NounType=Proc",
    "I": "NounType=Ing",
    "VRB": "NounType=Deverb",
    "COLL": "NumType=Collective",

    "AUX": "VerbType=Aux",
}

# Whether the language has adjectives as a separate POS
adjectives = False

# Whether the language uses prefixes
prefixes = True

# Default features applied when not explicitly specified
defaults = {
    "NOUN": ["Case=Abs", "Number=Sing"],
    "VERB": [
        (["Mood=Ind", "Mood!=Imp"], "Tense=Pres_Aor"),
        (["Emphatic=Yes", "Tense!=Fut"], "Tense=Pres_Aor"),
        (["VerbForm=Vnoun"], "Tense=Pres_Aor"),
    ],
}

# Language metadata
language_name = "Нивхский"
language_name_en = "Nivkh"
language_code = "niv"
