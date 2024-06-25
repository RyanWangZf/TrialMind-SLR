PRIMARY_TERM_EXTRACTION = '''You are a clinical specialist. You are conducting a clinical study meta-analysis.
The research is defined by the following PICO elements:
P (Patient, Problem or Population): {P}
I (Intervention): {I}
C (Comparison): {C}
O (Outcome): {O}

## Task
Your task is to identify the primary clinical term(s) in this research. 
The clinical terms should be specific medical conditions, treatments, or procedures. 
General terms such as 'patients', or 'therapy' should not be included.

## Reply Format
You should only reply with 1~3 primary term. Your output should be in JSON format, like this:

{{
    "terms": ["term1", "term2", "term3"]
}}
'''

SEARCH_TERM_EXTRACTION = """
## background

You are a clinical specialist. You are conducting a clincial meta-analysis.
The research is defined by the following PICO elements:
P (Patient, Problem or Population): {P}
I (Intervention): {I}
C (Comparison): {C}
O (Outcome): {O}

## Reference

You've already gathered these related papers: 
{pubmed_reference_text}

## Task

Your task is to further your literature search by these 3 steps:

### Step 1
Extract related term in the reference papers.
Provide three lists of query terms: TREATMENTS, CONDITIONS, and OUTCOMES.

CONDITIONS: words about any conditions or disease that is related to this meta-analysis (refering to Problem section)
TREATMENTS: primary related clinical terms/keywords showed in these reference papers (refering to Intervention section)
OUTCOMES: clinical endpoints or outcome measurements that are related to this meta-analysis (refering to Outcome section)

### Step 2
Double-check these query terms, remove the terms that is not directly related to the PICO elements of this research.
Provide three lists of refined core terms: CORE_CONDITIONS, CORE_TREATMENTS, and CORE_OUTCOMES.

CORE_CONDITIONS: refined terms of conditions or disease
CORE_TREATMENTS: refined terms of primary related clinical terms/keywords
CORE_OUTCOMES: refined terms of clinical endpoints or outcome measurements

### Step 3
To expand the scope of query term searches, please extend each query term by: 
1. Synonyms and other names/forms; 
2. Possible abbreviations or full forms; 
3. Split into elements for compound phrases. 
Provide three lists of expanded query terms: EXPAND_CONDITIONS, EXPAND_TREATMENTS, EXPAND_OUTCOMES.

EXPAND_CONDITIONS: expanded terms of conditions or disease
EXPAND_TREATMENTS: expanded terms of primary related clinical terms/keywords
EXPAND_OUTCOMES: expanded terms of clinical endpoints or outcome measurements


## Reply format
There should be no overlap between these each pair of lists

Your reply should be in a format like: 

{{

"step 1": {{
    "CONDITIONS": [condition1, condition2, ..] \\ (~10 items)
    "TREATMENTS": [term1, term2 .. ] \\ (~10 items)
    "OUTCOMES": [outcome1, outcome2, ..] \\ (~10 items)
}},

\\ Refine according to P (Patient, Problem or Population): {P} and I (Intervention): {I} and O (Outcome): {O}
"step 2": {{
    "CORE_CONDITIONS": [condition1, condition2, ..] \\ (~5 items)
    "CORE_TREATMENTS": [term1, term2, .. ] \\ (~5 items)
    "CORE_OUTCOMES" : [outcome1, outcome2 ..] \\ (~5 items)
}},

\\ Augumentation
"step 3": {{
    "EXPAND_CONDITIONS": [condition1, condition2, ..]  \\ (~10 items)
    "EXPAND_TREATMENTS": [term1, term2 ..] \\ (~10 items)
    "EXPAND_OUTCOMES": [outcome1, outcome2 ..] \\ (~10 items)
    }}
}}
"""