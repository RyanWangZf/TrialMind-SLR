SCREENING_CRITERIA_GENERATION  = '''
You are a clinical specialist. You are conducting a clincial meta-analysis.
The research is defined by the following PICO elements:
P (Patient, Problem or Population): {P}
I (Intervention): {I}
C (Comparison): {C}
O (Outcome): {O}

## Task
Your task is to design the eligibility criteria for selecting studies for this meta-analysis study following these 3 steps:

### Step 1
Based on the PRISMA guidelines and the PICO elements of this research, please identify five eligibility criteria for the studies to be included in the meta-analysis. Provide a rationale for each criterion.

ELIGIBILITY_ANALYSIS: your items and reasons here...

### Step 2
Next, create {num_title_criteria} binary questions that will help you select studies based on their titles. 
These questions should be designed so that a "YES" answer indicates the study meets the criteria, while a "NO" answer means it doesn't. 
The information required to answer these questions should be general and easily found in the study title.

TITLE_CRITERIA n: ...

### Step 3
Finally, develop {num_abstract_criteria} more binary questions to further filter the studies based on their content. 
These questions should also be designed for a "YES" or "NO" answer, 
but the information required to answer them will be more detailed and is expected to be found within the main content of the study.

CONTENT_CRITERIA n: ...

## Reply Format
You should reply in a format like:

{{
    "ELIGIBILITY_ANALYSIS": ["rationale1", "rationale12", ...] \\ the bullet points of your analysis
    "TITLE_CRITERIA": ["criterion1", "criterion2", "..."] \\ the {num_title_criteria} binary title-based criteria
    "CONTENT_CRITERIA": ["criterion1", "criterion2", "..."] \\ the {num_abstract_criteria} binary content-based criteria
}}
'''