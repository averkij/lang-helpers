# Karaim language scheme

language_name = "караимский"
language_name_en = "Karaim"
language_code = "kdr"

adjectives = True
prefixes = False

morphdict = {
    "GEN": "Case=Gen",
    "ACC": "Case=Acc",
    "ABL": "Case=Abl",
    "LOC": "Case=Loc",
    "DAT": "Case=Dat",
    "O": "Case=Obl",
    "INSTR": "Case=Ins",
    "INST": "Case=Ins",
    "ABE": "Case=Abe",
    "COMP": "Case=Cmp",

    "VRB": "VerbType=Denom|POS=Verb",
    "VBZ": "VerbType=Denom|POS=Verb",
    "ABSTR": "NounType=AbstrNoun|POS=Noun",
    "ACTOR": "SemanticLabel=Agent",

    "SG": "Number=Sing",
    "PL": "Number=Plur",

    "1": "Person=1",
    "2": "Person=2",
    "3": "Person=3",

    "CMP": "Degree=Cmp",
    "DIM": "Degree=Dim",

    "ORD": "NumType=Ord",
    "COLL": "NumType=Sets",

    "ANT": "Aspect=Ant",
    "SIM": "Aspect=Sim",
    "MULT": "Aspect=Mult",
    "PFV": "Aspect=Perf",
    "IPFV": "Aspect=Imp",
    "HAB": "Aspect=Hab",

    "PRS": "Tense=Pres",
    "PST": "Tense=Past",
    "FUT": "Tense=Fut",

    "INF": "VerbForm=Inf",
    "CONV": "VerbForm=Conv",
    "PTCP": "VerbForm=Part",
    "ST": "VerbForm=Stat",
    "CVB": "VerbForm=Conv",
    "NMN": "VerbForm=Vnoun|POS=Noun",

    "REFL": "Reflex=Yes",
    "REC": "Reciprocal=Yes",
    "CAUS": "Voice=Caus",
    "PASS": "Voice=Pass",
    "ACT": "Voice=Act",

    "NEG": "Polarity=Neg",

    "OPT": "Mood=Opt",
    "HORT": "Mood=Hort",
    "COND": "Mood=Cnd",
    "IND": "Mood=Ind",
    "IMP": "Mood=Imp",

    "AUX": "POS=Aux",
    "ADJ": "POS=Adj",

    "FOC": "Focus=Yes",
    "POSS": "POSS=Yes",
}

defaults = {
    "NOUN": ["Case=Nom", "Number=Sing"],
    "VERB": ["VerbForm=Fin", (["VerbForm=Fin", "Mood!=Imp"], "Tense=Pres")],
}
