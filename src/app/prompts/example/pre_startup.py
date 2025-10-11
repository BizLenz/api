import textwrap

SYSTEM_PROMPT = textwrap.dedent("""
    You are an expert evaluator for the Pre-Startup Package. 
    Your sole mission is to analyze and evaluate submitted business plans strictly and objectively 
    based on the evaluation criteria provided.
""").strip()

SECTION_ANALYSIS_PROMPT_TEMPLATE = textwrap.dedent("""
    **Evaluation Criteria:** {section_name}
""").strip()

FINAL_REPORT_PROMPT = textwrap.dedent("""
    You are a system that generates a final report based on the analysis results and metadata provided.
    Please generate a valid JSON report.
""").strip()

EVALUATION_CRITERIA = [
    {
        "section_name": "1.1. section 1",
        "max_score": 100,
        "pillars": {
            "pillar 1": {
                "description": "pillar 1 description",
                "questions": ["question 1", "question 2", "question 3"],
            },
        },
    },
]
