import argparse
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from langchain_classic.agents import create_tool_calling_agent, AgentExecutor

from fiction_editor_agent import run_fiction_editor
from tools import search_tool, wiki_tool, save_tool

# Load environment variables from an explicit project .env path.
PROJECT_ROOT = Path(__file__).resolve().parent
load_dotenv(dotenv_path=PROJECT_ROOT / ".env")

# Define the structure of the research response using Pydantic
class ResearchResponse(BaseModel):
    topic: str
    summary: str
    sources: list[str]
    tools_used: list[str]

def _build_research_executor():
    """Initialize research-mode dependencies only when needed."""
    llm = ChatOpenAI(model="gpt-4")
    _ = ChatAnthropic(model="claude-3-5-sonnet-20241022")
    parser = PydanticOutputParser(pydantic_object=ResearchResponse)

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

    tools = [search_tool, wiki_tool, save_tool]
    agent = create_tool_calling_agent(llm=llm, prompt=prompt, tools=tools)
    agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)
    return agent_executor, parser

def run_research_mode(query: str):
    agent_executor, parser = _build_research_executor()
    raw_response = agent_executor.invoke({"query": query})
    try:
        output_text = raw_response.get("output", "")
        structured_response = parser.parse(output_text)
        print(structured_response)
    except Exception as e:
        print("error parsing response:", e, "Raw Response - ", raw_response)


def main():
    arg_parser = argparse.ArgumentParser(
        description="Run the research agent or fiction editor agent."
    )
    arg_parser.add_argument(
        "--file",
        dest="file_path",
        help="Path to a manuscript file (.txt, .pdf, .doc, .docx) for editor mode.",
    )
    arg_parser.add_argument(
        "--query",
        dest="query",
        help="Research query. If omitted in research mode, interactive prompt is used.",
    )
    args = arg_parser.parse_args()

    if args.file_path:
        summary = run_fiction_editor(args.file_path)
        print("Fiction editor run complete")
        print(summary)
        return

    query = args.query or input("What can I help you research?")
    run_research_mode(query)


if __name__ == "__main__":
    main()

