# IMPORTS
from dotenv import load_dotenv
from pydantic import BaseModel
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from langchain_classic.agents import create_tool_calling_agent, AgentExecutor
from tools import search_tool, wiki_tool, save_tool

# Load environment variables from .env file
load_dotenv()

# Define the structure of the research response using Pydantic
class ResearchResponse(BaseModel):
    topic: str
    summary: str
    sources: list[str]
    tools_used: list[str]

# Initialize language models, output parser
llm = ChatOpenAI(model="gpt-4")
llm2 = ChatAnthropic(model="claude-3-5-sonnet-20241022")
parser = PydanticOutputParser(pydantic_object=ResearchResponse)

# PROMPT TEMPLATE
prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """
            You are a research assistant that will help generate a research paper.
            Answer the user query and use neccessary tools. 
            Wrap the output in this format and provide no other text\n{format_instructions}
            """,
        ),
        ("placeholder", "{chat_history}"),
        ("human", "{query}"),
        ("placeholder", "{agent_scratchpad}"),
    ]
).partial(format_instructions=parser.get_format_instructions())

# TOOLS (called from tools.py)
tools = [search_tool, wiki_tool, save_tool]

# AGENT
agent = create_tool_calling_agent(
    llm=llm,
    prompt=prompt,
    tools=tools,
)

# EXECUTOR
agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)

# MAIN
query = input("What can I help you research?")

# Invoke the agent with the user query and get the raw response
raw_response = agent_executor.invoke({"query": query})

# Parse the raw response using the Pydantic output parser and print the structured response
try:
    output_text = raw_response.get("output", "")
    structured_response = parser.parse(output_text)
    print(structured_response)
except Exception as e:
    print("error parsing response:", e, "Raw Response - ", raw_response)

