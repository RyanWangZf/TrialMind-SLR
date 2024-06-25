STUDY_FIELDS_EXTRACTION = """You are now the following python function: ```
def extract_fields_from_input_study(inputs: Dict[str, Any]) -> str:
    \"\"\"
    This function is tasked with analyzing clinical trial study reports or papers to extract specific information as structured data
    and provide citations for the extracted information.
    The user will provide a list of fields they are interested in, along with a natural language description for each field to guide you on what content to look for and from which parts of the report to extract it.

    IMPORTANT:
    For each field described by the user, you need to:
    1. Identify and extract the relevant information from the report based on the provided description.
    2. Generate a field name that accurately represents the content of the field based on its description.
    3. Structure the extracted information into a standard format whenever possible (e.g., integer, numerical values, dates, keywords, list of terms). 
        If standardization is not possible, the information should be presented in text format.
        If the field is not found in the report, the extracted value should be "NP".
    4. Provide a reference to the document ID from which this information was extracted.
        This citation id should be restricted to be integers only.
        You should NOT cite more than three sources for a single field.
        You should try your best to provide the most relevant and specific citation for each field.
        If two or more sources are equally relevant, you can just cite one of them.

    The function returns a string representing a dictionary with each key representing a field and its extracted value. The format should be as follows:

    Returns: A syntactically correct JSON string representing a list of dictionary with three keys: name, value, and source_id.
        Format:
        ```json
        [
            {{
                "name":  \\ str, length <= 25 tokens
                "value":  \\ str, length <= 25 tokens
                "source_id":  \\ list[int], length <= 3 ids
            }},
            {{
                "name":, \\ str, length <= 25 tokens
                "value":  \\ str, length <= 25 tokens
                "source_id":  \\ list[int], length <= 3 ids
            }},
            ...
        ]
        ```
    \"\"\"
```
Respond exclusively with the generated JSON string wrapped ```json and ```.

# User provided inputs
paper_content = \"\"\"{paper_content}\"\"\"
fields = \"\"\"{fields}\"\"\"

inputs = {{
    "paper_content": paper_content,
    "fields": fields
}}
"""

RESULT_TABLE_EXTRACTION = """You are now the following python function: ```
def locate_evidence_in_study_about_the_request_for_results(inputs: Dict[str, Any]) -> str:
    \"\"\"
    This function is tasked with analyzing clinical trial study reports or papers to extract specific information as structured data.

    Task Instructions:
    1. Review the clinical trial paper, paying close attention to the sections discussing results related to the "{target_outcome}" for the defined cohort "{cohort}".
    2. Summarize the findings for each cohort, emphasizing the collective data and general trends observed. Individual patient data should only be mentioned if highlighted as a significant exception or case study in the paper.
    3. Present your summary in a table format with the following columns:
    - 'Group Name': Name of the cohort.
    - 'Number of Patients': Total participants in the cohort.
    - 'Specified Outcome Measure': Key findings and metrics related to the "{target_outcome}".
    Include aggregate values such as percentages, mean values, and other statistical summaries that reflect the overall results for the group.
    Must contain quantitative data, such as hazard ratios, odds ratios, mean differences, count of events, etc.
    Do not include qualitative or descriptive data that cannot be quantified, such as "statistically significant improvement" without specific values.

    Here are the definitions of some common outcome measurements:
    - overall survival/progression-free survival/etc.: usually defined by the hazard ratio or odds ratio, which is the ratio of hazard rate or odds of an event occurring in the treatment group to that in the control group.
        it can also be expressed as the number of events in the target group of patients.
    - toxicity/adverse events/etc.: defined by the rate of occurrence of adverse events in the target groups of patients.
    - objective response rate/overall response/etc.: defined by the proportion of patients who respond to the treatment in the target groups, or number of patients with complete or partial response.
    - disease control rate/relapse rate/etc.: defined by the proportion of patients who have stable disease or better in the target groups, or number of patients with disease control.
        it can also be expressed by the number of patients who have disease progression, so the disease control rate is 1 minus the progression rate.
    
    Returns:
        A str representing a list of dictionary with three keys: Group Name, N, and Results.
        Group Name: str - name of the cohort
        N: int - number of participants in the cohort
        Results: str - key findings and metrics related to the outcome measure, must be quantitative and concise
            adhere to the input paper content.
        Example format:
        ```json
        [
            {{
                "Group Name": str, \\ the name of the cohort
                "N": int, \\ the number of participants in the cohort
                "Results": str \\ key findings and metrics related to the outcome measure, must be quantitative and concise (<= 50 tokens)
            }},
            {{
                ...
            }},
            ...
        ]
        ```
    \"\"\"
```
Respond exclusively with the generated JSON string wrapped ```json and ```.

# User provided inputs
paper_content = \"\"\"{paper_content}\"\"\"
cohort = \"\"\"{cohort}\"\"\"
target_outcome = \"\"\"{target_outcome}\"\"\"

inputs = {{
    "paper_content": paper_content,
    "cohort": cohort,
    "target_outcome": target_outcome
}}
"""

STUDY_RESULTS_STANDARDIZATION = """You are now the following python function: ```
def format_study_result_table(inputs: Dict[str, Any]) -> str:
    \"\"\"
    This function is used to transform raw data (with the content described in texts) from a clinical study paper into a structured table format.

    IMPORTANT: Organize the extracted data into a structured table format. Ensure that each column represents a crucial numerical data point necessary for meta-analysis. This may include participant numbers (N), measurable outcomes, 
        and other quantifiable metrics related to the intervention or comparator.

    IMPORTANT: The input groups are not mutually exclusive, you need to decide whether to combine them or
        select the eligible groups based on the research question.

    IMPORTANT: Drop the group if no outcome value is provided.
        
    The function returns a string representing a list of dictionary, each dictionary has three keys:
    ```json
    [
        {{
            Group: str \\ the name of the group
            N: int \\ the number of participants in the group
            Outcome Value: float or int \\ the outcome value for the group, must be float or int values
        }},
        {{
            ...
        }},
        ...
    ]
    ```

    Example output 1:
    ```json
    [
        {{
            "Group": "Patient with irAEs",
            "N": 100,
            "Hazard Ratio": 0.5,
        }},
        {{
            "Group": "Patient without irAEs",
            "N": 150,
            "Hazard Ratio": 0.3,
        }},
    ]
    ```

    Example output 2:
    ```json
    [
        {{
            "Group": "CAR-T ",
            "N": 100,
            "Number of Events": 20,
        }}
    ]
    ```

    Returns:
        A str representing a list of dictionary with three keys: Groups, N, and Outcome.
        Groups: str - the name of the group
        N: int - the number of participants in the group
        {outcome}: float or int - the outcome value for the group, must be float or int
    \"\"\"
```
Respond exclusively with the generated JSON string wrapped ```json and ```.

# User provided inputs
results = \"\"\"{results}\"\"\"
outcome = \"\"\"{outcome}\"\"\"
intervention = \"\"\"{intervention}\"\"\"
comparator = \"\"\"{comparator}\"\"\"
population = \"\"\"{population}\"\"\"

inputs = {{
    "results": results,
    "outcome": outcome,
    "intervention": intervention,
    "comparator": comparator,
    "population": population
}}
"""


STUDY_RESULTS_FORMATTING = """You are now the following python function: ```
def generate_continuous_elegant_python_code(inputs: Dict[str, Any]) -> str:
    \"\"\"
    This function is used to generate python code to transform raw data into a structured format according to a specified schema.
    The raw data is collected from a clinical study paper and needs to be organized to facilitate a meta-analysis study.
    The target meta-analysis is driven by a specific research question, defined by the Population, Intervention, Comparator, and Outcome (PICO) elements.

    The function takes a dictionary of `inputs` as an argument, which contains the following keys:
    - 'research_question': contains the population, intervention, comparator, and outcome (PICO) elements of the targeted meta-analysis.
        Based on the research question's intervention and comparator, you need to classify which arms in the raw data belong to the targeted
        experimental and control groups.
        Based on the research question's population, you need to consider which parts of the observations in the raw data are relevant to the targeted meta-analysis.
    - 'raw_data': this is the markdown formatted input dataframe that contains the raw data to be transformed.
    - 'desc': the description of the target dataframe the generated code needs to produce.
    - 'target_output': the generated code needs produce a dataframe follows the structure of this target_output.

    IMPORTANT: 'raw_data' does **NOT** need to be parsed or loaded into a dataframe. In your generated code,
        just use `df` to represent the dataframe that contains the raw data.

    IMPORTANT: NaN values should be treated with caution. If the raw data contains NaN values, ensure that your code handles them appropriately,
        either by removing the row with any NaN values or by filling all NaN with zeros.

    IMPORTANT: Never use `pd.DataFrame.append` to add data to pd.DataFrame. This method has been deprecated, and it is recommended to use `pd.concat` instead.
        For example, to add a new row to a dataframe, you can use `df = pd.concat([df, new_row], ignore_index=True)`
        Never use `df.append(new_row, ignore_index=True)`
    
    The function returns a string of raw Python code, wrapped within <code> and </code> tags. For example:
    <code>
    # df
    # Your generated python code here...
    </code>

    You should implemented three functions in your code, each of which takes a dataframe as input and returns a dataframe as output:
    <code>
    # Dataframe definition should be ignored and not show again
    # df = ...

    def classify_arms(df: pd.DataFrame):
        # you need to define a new column in the dataframe to indicate which group each arm belongs to
        # each arm should be classified as either experimental or control
        # e.g., `df['Group'] = ['Experimental', 'Control', 'Experimental', ...]`
        return df
    
    def consolidate_data(df: pd.DataFrame):
        # consolidate the data for each group
        return df

    def calculate_statistics(df: pd.DataFrame):
        # calculate the statistics for each group
        return df

    # run these functions in sequence to get the final dataframe
    df = classify_arms(df)
    df = consolidate_data(df)
    df = calculate_statistics(df)
    </code>

    Returns:
        Executable Python code that will be used to transform the raw data into the structured format.
    \"\"\"
```
Respond exclusively with the generated code wrapped <code></code>. Ensure that the code you generate is executable Python code that can be run directly in a Python environment, requiring no additional string encapsulation.

# User provided inputs
research_question = \"\"\"Population: {population}, Intervention: {intervention}, Comparator: {comparator}, Outcome: {outcome}\"\"\"
raw_data = \"\"\"{raw_data}\"\"\"
desc = \"\"\"{desc}\"\"\"
target_output = \"\"\"{target_output}\"\"\"

inputs = {{
    "research_question": research_question,
    "raw_data": raw_data,
    "desc": desc
    "target_output": target_output
}}
"""

RESULT_TABLE_TEMPLATE = {
    "binary": {
        "desc": """
When the study has a dichotomous (binary) outcome the
results of each study can be presented in a 2x2 table (Table 1) giving the numbers of participant
who do or do not experience the event in each of the two groups (here called experimental (or 1)
and control (or 2)). 
If the dataset contains data from multiple experimental groups or multiple control groups, consolidate this information so that all experimental group data is summarized into one row, 
and all control group data is summarized into another row, resulting in two distinct rows for the table: 
one representing the combined data for all experimental groups and another for all control groups.
If no control group is present, set c=0, d=0, n_2=0.

# a (int): number of participants who experience the event in experimental group
# b (int): number of participants who do not experience the event in experimental group
# n_1 (int): group size of experimental group
# c (int): number of participants who experience the event in control group
# d (int): number of participants who do not experience the event in control group
# n_2 (int): group size of control group
""",
        "table":"""
# Study: string, name of the experiment/control group
# Event: int, number of participants who experience the event
# No event: int, number of participants who do not experience the event
# Total: int, total number of participants
| Study | Event | No event | Total |
|-------|-------|----------|------ |
| Experimental | a | b | n_1 |
| Control | c | d | n_2 |""",
        "return_vars": ["a", "b", "n_1", "c", "d", "n_2"]
    },

    "continuous": {
        "desc": """If the outcome is a continuous measure, the number of participants in each of the two groups, their
mean response and the standard deviation of their responses are required to perform meta-analysis
(Table 2).
If the dataset contains data from multiple experimental groups or multiple control groups, consolidate this information so that all experimental group data is summarized into one row, 
and all control group data is summarized into another row, resulting in two distinct rows for the table: 
one representing the combined data for all experimental groups and another for all control groups.
If no control group is present, set n_2=0, m_2=0, sd_2=0.

# n_1 (int): group size of experimental group
# m_1 (float): mean response of experimental group
# sd_1 (float): standard deviation of experimental group
# n_2 (int): group size of control group
# m_2 (float): mean response of control group
# sd_2 (float): standard deviation of control group
""",
        "table": """
# Study: string, name of the experiment/control group
# Group size: int, number of participants in the group
# Mean response: float, mean response of the group
# Standard deviation: float, standard deviation of the response in this group
| Study | Group size | Mean response | Standard deviation |
|-------|------------|---------------|---------------------|
| Experimental | n_1 | m_1 | sd_1 |
| Control | n_2 | m_2 | sd_2 | 
""",
        "return_vars": ["n_1", "m_1", "sd_1", "n_2", "m_2", "sd_2"]
    },

    "o-minus-e": {
        "desc": """
If the outcome is analysed by comparing observed with expected values (for example using the Peto
method or a log-rank approach for time-to-event data), then "O - E" statistics and their variances are
required to perform the meta-analysis. Group sizes may also be entered by the review author, but are
not involved in the analysis.
If the dataset contains data from multiple experimental groups or multiple control groups, consolidate this information so that all group's data
is summarized into one row.

# Z (float): O - E
# V (float): Variance of O - E
# n_1 (int): group size of experimental group
# n_2 (int): group size of control group
""",
        "table": """
# Study: string, name of the experiment/control group
# O - E: float, observed minus expected value
# Variance of O - E: float, variance of observed minus expected value
# Group size (experimental): int, number of participants in the experimental group
# Group size (control): int, number of participants in the control group
| Study | O - E | Variance of O - E | Group size (experimental) | Group size (control) |
|-------|-------|-------------------|---------------------------|-----------------------|
| NA | Z | V | n_1 | n_2 |
""",
        "return_vars": ["Z", "V", "n_1", "n_2"]
    },

    "generic": {
        "desc": """
For other outcomes a generic approach can be used, the user directly specifying the values of the
intervention effect estimate and its standard error for each study (the standard error may be calculable
from a confidence interval). "Ratio" measures of effect effects (e.g. odds ratio, risk ratio, hazard ratio,
ratio of means) will normally be expressed on a log-scale, "difference" measures of effect (e.g. risk 
difference, differences in means) will normally be expressed on their natural scale. Group sizes can
optionally be entered by the review author, but are not involved in the analysis.

Calculation of different types of ratio measures as estimate of effect:
- Risk Ratio = Hazard Ratio of Treatment Group / Hazard Ratio of Control Group
- Risk Difference = Hazard Ratio of Treatment Group - Hazard Ratio of Control Group
- Hazard Ratio =  treatment hazard rate/placebo hazard rate
- Odds Ratio =  p1/(1-p1) / p2/(1-p2), where p1 and p2 are the probabilities of the event in the treatment and control groups, respectively.

If the dataset contains data from multiple experimental groups or multiple control groups, consolidate this information so that all group's data
is summarized into one row.

# E (float): estimate of effect
# SE (float): standard error of effect
# n_1 (int): group size of experimental group
# n_2 (int): group size of control group
""",
        "table": """
# Study: string, name of the experiment/control group
# Estimate of effect: float, estimate of effect
# Standard error of effect: float, standard error of effect
# Group size (experimental): int, number of participants in the experimental group
# Group size (control): int, number of participants in the control group
| Study | Estimate of effect | Standard error of effect | Group size (experimental) | Group size (control) |
|-------|--------------------|--------------------------|---------------------------|-----------------------|
| NA | E | SE | n_1 | n_2 |
""",
        "return_vars": ["E", "SE", "n_1", "n_2"]
    }
}


EXAMPLE_RESULT_EXTRACTION = [
    """
    INPUTS:
    - `results`:
    {{
        "Groups": [
            "Patients with irAEs",
            "Patients without irAEs",
            "Patients with rash",
            "Patients with vitiligo",
            "Patients treated with systemic steroids",
            "Patients not treated with systemic steroids"
        ],
        "Number of Patients": [
            101,
            47,
            64,
            19,
            9,
            134
        ],
        "Results": [
            "Statistically significant OS difference noted with greater benefit in those reporting 3 or more irAE events (p=<0.001).",
            "No significant OS difference mentioned for patients without irAEs.",
            "Statistically significant improvement in OS associated with rash in both univariate and multivariate analyses (p=0.002 [HR 0.423, 95% CI: 0.243-0.735]).",
            "Statistically significant improvement in OS associated with vitiligo in both univariate and multivariate analyses (p=0.042 [HR 0.184, 95% CI: 0.036-0.94]).",
            "Statistically significant difference in OS in favor of the steroid group (p=0.026).",
            "Significant OS benefit for those with any grade of irAE, even without steroid treatment (p=0.001)."
        ]
    }}

    `population`: "patients with cancer receiving immune checkpoint inhibitors (ICIs): nivolumab, pembrolizumab, atezolizumab, durvalumab, avelumab, or ipilimumab"
    `intervention`: "occurrence of immune-related AEs (irAEs); "
    `comparator`: "non-occurrence of irAEs"

    """
]


RESULT_TABLE_EXTRACTION_OLD = """
Analyze the provided clinical trial paper with a focus on summarizing the overall results for the outcome measure "{target_outcome}" across the specified cohorts.

Paper Details:
{paper_content}

Cohorts of Interest:
{cohort}

Task Instructions:
1. Review the clinical trial paper, paying close attention to the sections discussing results related to the "{target_outcome}" for the defined cohorts.
2. Summarize the findings for each cohort, emphasizing the collective data and general trends observed. Individual patient data should only be mentioned if highlighted as a significant exception or case study in the paper.
3. Present your summary in a table format with the following columns:
   - 'Group Name': Name of the cohort.
   - 'Number of Patients': Total participants in the cohort.
   - 'Specified Outcome Measure': Key findings and metrics related to the "{target_outcome}".
      Include aggregate values such as percentages, mean values, and other statistical summaries that reflect the overall results for the group. 
      Mention individual patient data only if it's highlighted as a significant part of the study's findings.

Note: Your analysis should focus on the aggregate data and main conclusions drawn for each group, ensuring a concise and clear presentation of the trial's outcomes.

Note: Do not include group that does not have numerical or quantifiable outcomes reported.

**Reply Format:**
Please provide the summary in a syntactically correct JSON format, focusing on group-level data and findings:

```json
{{
    "Groups": ["A", "B", "C"],
    "Number of Patients": [100, 100, 50],
    "Results": [
        "60% reduction in tumor size at 3 months for the group, with 15% achieving complete remission",
        "70% reduction in tumor size at 3 months for the group, 20% complete remission, with group-level side effects observed in 30% of patients",
        "Group-level observations show minimal changes, with an overall 5% showing slight reduction in tumor size"
    ]
}}
```
"""

STUDY_RESULTS_STANDARDIZATION_OLD = """
Given a clinical study paper containing raw data on various arms of a trial, your task is to transform this data into a standard structured table format. 

The data extraction should be guided by a specific research question, defined by the Population, Intervention, Comparator, and Outcome (PICO) elements. 

**Input Data:**
```
{results}
```

**Research Question:**
1. Population (P): {population}
2. Intervention (I): {intervention}
3. Comparator (C): {comparator}
4. Outcome (O): {outcome}

**Instructions:**

**Step 1:** Identify Key Study Arms
- Start by reviewing the research question, paying close attention to the Population, Intervention, Comparator, and Outcome (PICO) elements.
- From the raw study data, pinpoint the study arms that directly relate to the specified Intervention and Comparator. These will be the focus of your analysis.

**Step 2:** Data Extraction and Consolidation
- Carefully extract relevant data from the identified study arms. Pay special attention to details such as number of participants, outcome values, and other pertinent outcome metrics that are crucial for the target meta-analysis.
- If multiple entries pertain to the same intervention, merge their data into one row to represent the experimental group. If there are separate interventions and comparators, allocate two rows: one for the experimental group and one for the comparator group.
- For unknown but important information such as participant numbers (N), you may need to deduce the figure from descriptive text. 
    For instance, if the raw data mentions "Four of seven patients achieved...", interpret this as "N": 7. Convert such textual descriptions into numerical data wherever possible.
    If the raw data describes the individual outcomes of participants, summarize these outcomes to obtain the total number of participants and the overall outcome value for each arm.

**Step 3:** Structuring the Data into a Table
- Organize the extracted data into a structured table format. Ensure that each column represents a crucial numerical data point necessary for meta-analysis. This may include participant numbers (N), measurable outcomes, and other quantifiable metrics related to the intervention or comparator.
- Classify each arm as belonging to the experimental or control group, which is important for subsequent meta-analysis.
- All columns must contain numerical data that is pertinent to the PICO-driven research question. This is essential for the subsequent meta-analysis.
- Assign clear and concise headings to each column to reflect the data it contains. The table should be formatted consistently to facilitate easy interpretation and analysis.

## Reply Format
You should reply in a syntactically correct JSON format like the below example:
```json
{{
    "step1": {{
        "experimental_group": [arm1, arm2, ...], \\ list of relevant intervention arms
        "control_group": [arm1, arm2, ...] \\ list of relevant control arms (if applicable), otherwise be empty list
    }},

    "step2": {{
        "experimental_group": [data1, data2, ...], \\ list of extracted data for experimental group, data format is up to you
        "control_group": [data1, data2, ...] \\ list of extracted data for control group (if applicable), otherwise be empty list
    }},

    "step3": {{
        "columns": [
            {{ "name": "N", "description": "Number of participants" }},
            {{ "name": "Group", "description": "if this arm belongs to experimental or control group" }},
            {{ "name": "Outcome Value", "description": "Value of the outcome measure" }},
            ... \\ all columns extracted
        ],
        "data": [
            {{ "N": 100, "Outcome Value": "0.5" , "Group": "Experimental"}},
            {{ "N": 150, "Outcome Value": "0.3", "Group": "Control"}},
            ... \\ all rows of extracted data
        ]
    }}
}}```
"""