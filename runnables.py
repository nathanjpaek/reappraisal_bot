from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.chat_history import InMemoryChatMessageHistory
from langchain_core.runnables import RunnableLambda, RunnableMap, RunnablePassthrough
from typing import List, Dict, Literal
from pydantic import BaseModel

class CrisisRunnable:
    crisis_prompt_txt = """read the user's text and if it includes anything about self harm, suicide, or sexual abuse,
        say '::crisis::', otherwise say '::valid::'. only output 1 word
        
        <user_text>
        {input}
        </user_text>
        """
        
    def __init__(self, model=None):
        if model is None:
            model = ChatOpenAI(model_name="gpt-4o")
        self.model = model
    
    def __call__(self, input) -> Literal['::crisis::', '::valid::']:
        crisis_prompt = ChatPromptTemplate.from_messages([("system", self.crisis_prompt_txt)])
        crisis_chain = crisis_prompt | self.model | StrOutputParser()
        return crisis_chain.invoke({"input": input})


class EmotionSelectorRunnable:
    emotions = [
        "stressed", "worried", "overwhelmed", "concerned", "annoyed", "irritated",
        "frustrated", "embarrassed", "guilty", "ashamed", "disappointed", "hurt", "lonely", "sad",
        "regretful", "confused", "surprised", "peaceful", "relieved", "content",
        "inspired", "excited", "hopeful", "grateful", "proud"
    ]

    def __init__(self, crisis_runnable):
        self.crisis_runnable = crisis_runnable

    def __call__(self, input_data: Dict) -> List[str]:
        selected_emotions = input_data.get("selected_emotions", [])

        # check for crises
        crisis_check = self.crisis_runnable(" ".join(selected_emotions))
        if crisis_check == "::crisis::":
            return "::crisis::"

        return selected_emotions


class SummaryRunnable:
    prompt_template = """
    Look at the description of the issue the user described, along with their reported emotions and reasons for those emotions.
    Summarize these facets concisely, rephrasing them in different words than the user provided.
    Each bullet point should capture a specific aspect of the issue along with the corresponding negative emotion.

    Format the output as a bulleted list with phrases written in the second person.
    Ensure that each bullet point clearly reflects something negative and captures the emotional impact it has on the user.
    Make the list as short as possible without missing any important details. Do not invent any information the user did not provide.
    Avoid guessing external circumstances unless explicitly stated by the user.

    After the bulleted list, ask the user if this summary adequately captures the key facets of their situation and their emotions.

    Issue: 
    {issue}

    Emotions:
    {emotions}

    Reasons:
    {reasons}
    """

    def __init__(self, model):
        self.model = model

    def __call__(self, input: Dict):
        original_problem = input.get("issue", "")
        emotions = ", ".join(input.get("emotions", []))
        reasons = "; ".join([f"{emotion}: {reason}" for emotion, reason in input.get("emotions_data", {}).items()])

        formatted_prompt = self.prompt_template.format(
            issue=original_problem,
            emotions=emotions,
            reasons=reasons
        )
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", formatted_prompt)
        ])
        chain = prompt | self.model | StrOutputParser()
        summary = chain.invoke({})
        input["summary"] = summary
        return summary


def handle_summary_confirmation(input_data):
    user_selection = input_data.get("user_selection", "").strip().lower()
    print(f"Debug: handle_summary_confirmation received: '{user_selection}'")
    
    if user_selection == "yes":
        print("Debug: Returning confirmation '1'")
        return "1", input_data["summary"]
    elif user_selection == "no":
        print("Debug: Returning confirmation '0'")
        edited_summary = input_data.get("edited_summary", "")
        return "0", edited_summary
    
    print(f"Debug: Invalid input '{user_selection}', returning 'invalid'")
    return "invalid", None


class ReappraisalRunnable:
    prompt_txt = """You are a cognitive reappraisal bot. You will be given a summary of someone's issue and a value that they hold. Your role is to help them reframe their issue by focusing on a core value they hold. Provide a cognitive reappraisal that aligns with their value.

    Issue summary: <issue> {issue} </issue>
    Core value: <value> {value} </value>

    Please provide a thoughtful reappraisal of the issue that incorporates the user's core value. The reappraisal should:
    1. Acknowledge the user's feelings and the difficulty of the situation
    2. Highlight how the core value relates to the issue
    3. Offer a new perspective or way of thinking about the issue that aligns with the value and will help the person feel better

    Your response should be empathetic, supportive, and focused on helping the user see their situation in a new light that resonates with their core value."""

    def __init__(self, model):
        self.model = model

    def __call__(self, input: Dict) -> str:
        prompt = ChatPromptTemplate.from_messages([
            ("system", self.prompt_txt)
        ])
        chain = prompt | self.model | StrOutputParser()
        reappraisal = chain.invoke({
            "issue": input["issue"],
            "value": input["value"]
        })
        return reappraisal

