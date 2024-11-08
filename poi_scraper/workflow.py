import os
from typing import Annotated, Any, Optional

from autogen import AssistantAgent, register_function, UserProxyAgent

from fastagency import UI
from fastagency.runtimes.autogen import AutoGenWorkflows

from poi_scraper.custom_web_surfer import CustomWebSurferTool
from poi_scraper.utils import get_all_unique_sub_urls, is_valid_url, generate_poi_markdown_table

system_message = """You are a web surfer agent tasked with identifying Points of Interest (POI) on a given webpage. 
Your objective is to find and list all notable POIs where people can visit or hang out. 

Instructions:

    - Scrape only the given webpage to identify POIs (do not explore any child pages or external links).
    - ALWAYS visit the full webpage before collecting POIs.
    - NEVER call `register_poi` without visiting the full webpage. This is a very important instruction and you will be penalised if you do so.
    - After visiting the webpage and identifying the POIs, you MUST call the `register_poi` function to record the POI.

Ensure that you strictly follow these instructions to capture accurate POI data."""

poi_validator_system_message = """You are a helpful agent. Your task is to determine if a given name qualifies as a Point of Interest (POI).

Definition of a POI:
    A POI is a specific place where people can visit or gather, such as tourist attractions, landmarks, parks, museums, cultural venues, and historic sites.
    General terms that describe activities or broad categories, like "Things to do in Chennai" or "Places to visit in Chennai," are not POIs.

Instructions:
    If the given name is a POI, reply with "Yes".
    If the given name is not a POI, reply with "No".
    Do not provide any response other than "Yes" or "No"; you will be penalized for any additional information.

Examples:
    - name: "Marina Beach", description: "Marina Beach is a natural urban beach in Chennai, Tamil Nadu, India."
    - Your response: "Yes"

    - name: "Explore Chennai", description: "Discover the best places to visit in Chennai."
    - Your response: "No"

    - name: "Kapaleeshwarar Temple", description: "Kapaleeshwarar Temple is a Hindu temple dedicated to Lord Shiva."
    - Your response: "Yes"

    - name: "Best Restaurants in Chennai", description: "Explore the top restaurants in Chennai."
    - Your response: "No"

    - name: "Arignar Anna Zoological Park", description: "Arignar Anna Zoological Park is a zoological garden located in Vandalur, a suburb in the southwestern part of Chennai."
    - Your response: "Yes"

    - name: "Treks in Chennai", description: "Discover the best trekking spots in Chennai."
    - Your response: "No"
"""


llm_config = {
    "config_list": [
        {
            # "model": "gpt-4o-mini",
            "model": "gpt-4o",
            "api_key": os.getenv("OPENAI_API_KEY"),
        }
    ],
    "temperature": 0.8,
}

wf = AutoGenWorkflows()

@wf.register(name="poi_scraper", description="POI scraper chat")  # type: ignore[type-var]
def websurfer_workflow(
    ui: UI, params: dict[str, Any]
) -> str:

    registered_pois: dict[str, str] = {}
    
    summaries: list[str] = []

    # Create POI agents
    poi_validator_agent = AssistantAgent(
        name="POI_Validator_Agent",
        system_message=poi_validator_system_message,
        llm_config=llm_config,
        human_input_mode="NEVER",
    )

    poi_user_proxy = UserProxyAgent(
        name="Poi_User_Proxy_Agent",
        system_message="You are a helpful agent",
        llm_config=llm_config,
    )
    
    def register_poi(
            name: Annotated[str, "The name of POI"], 
            description: Annotated[str, "The descrption of POI"], 
            category: Annotated[str, "The category of the POI"],
            location: Annotated[Optional[str], "The location of the POI"] = None
            ) -> str:

        def is_poi(name: str, description: str) -> str:
            initial_message = f"Please confirm if this {name} is a Point of Interest (POI). You can use the {description} to make your decision. Reply with 'Yes' if it is a POI, and 'No' if it is not a POI."
            chat_result = poi_user_proxy.initiate_chat(
                poi_validator_agent,
                message=initial_message,
                summary_method="reflection_with_llm",
                max_turns=1,
            )
            messages = [msg["content"] for msg in chat_result.chat_history]
            last_message = messages[-1]
            
            return last_message
        
        is_valid_poi = is_poi(name, description)
        if is_valid_poi == "Yes":
            registered_pois[name] = {"description": description, "category": category, "location": location}
            ui.text_message(sender="WebSurfer", recipient="POI Database", body=f"POI registered. name: {name}, description: {description}, category: {category}, location: {location}")
            return "POI registered"
        
        ui.text_message(sender="WebSurfer", recipient="POI Database", body=f"POI not registered. name: {name}, description: {description}, category: {category}, location: {location}")
        return "POI not registered"
    
    # Get valid URL from user
    while True:
        webpage_url = ui.text_input(
            sender="Workflow",
            recipient="User",
            prompt="I can collect Points of Interest (POI) data from any webpage—just share the link with me!",
        )
        if is_valid_url(webpage_url):
            break
        ui.text_message(
            sender="Workflow",
            recipient="User",
            body="The provided URL is not valid. Please enter a valid URL. Example: https://www.example.com",
        )
    
    # Collect all unique sub-links
    all_unique_sub_urls = get_all_unique_sub_urls(webpage_url)

    # Create agents and tools
    assistant_agent = AssistantAgent(
        name="Assistant_Agent",
        system_message="You are a helpful agent",
        llm_config=llm_config,
        human_input_mode="NEVER",
    )

    web_surfer = AssistantAgent(
        name="WebSurfer_Agent",
        system_message=system_message,
        llm_config=llm_config,
        human_input_mode="NEVER",
    )
    
    web_surfer_tool = CustomWebSurferTool(
        name_prefix="Web_Surfer_Tool",
        llm_config=llm_config,
        summarizer_llm_config=llm_config,
        bing_api_key=os.getenv("BING_API_KEY"),
    )

    web_surfer_tool.register(
        caller=web_surfer,
        executor=assistant_agent,
    )

    register_function(
        register_poi,
        caller=web_surfer,
        executor=assistant_agent,
        name="register_poi",
        description="Register Point of Interest (POI)",
    )

    for url in all_unique_sub_urls:
        
        def scrape_poi_data(url: str) -> str:
            
            initial_message = f"""Please collect all the Points of Interest (POI) data from this webpage: {url}."""


            chat_result = assistant_agent.initiate_chat(
                web_surfer,
                message=initial_message,
                summary_method="reflection_with_llm",
                max_turns=3,
            )

            return chat_result.summary

        summaries.append(scrape_poi_data(url))    
    
    table = generate_poi_markdown_table(registered_pois)
    ui.text_message(sender="Workflow", recipient="User", body=f"List of all POIs:\n{table}")
    
    # Return combined summary of all processed links
    return f"POI collection completed for {len(all_unique_sub_urls)} links.\n" + "\n".join(summaries)
