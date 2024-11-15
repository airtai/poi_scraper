from typing import Any, Optional

from autogen import AssistantAgent, UserProxyAgent

from poi_scraper.poi_types import PoiValidationResult, ValidatePoiAgentProtocol


class ValidatePoiAgent(ValidatePoiAgentProtocol):
    """A class to check if the gien name qualifies as a Point of Interest (POI)."""

    SYSTEM_MESSAGE = """You are a helpful agent. Your task is to determine if a given name qualifies as a Point of Interest (POI).

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

    def __init__(self, llm_config: dict[str, Any]):
        """Initialize POI validator with optional custom configuration.

        Args:
            llm_config: Optional custom configuration for the validator agent
        """
        self.llm_config = llm_config
        self._validator_agent = None
        self._user_proxy = None

    @property
    def validator_agent(self) -> AssistantAgent:
        """Lazy initialization of validator agent."""
        if self._validator_agent is None:
            self._validator_agent = AssistantAgent(
                name="POI_Validator_Agent",
                system_message=ValidatePoiAgent.SYSTEM_MESSAGE,
                llm_config=self.llm_config,
                human_input_mode="NEVER",
            )
        return self._validator_agent

    @property
    def user_proxy(self) -> UserProxyAgent:
        """Lazy initialization of user proxy agent."""
        if self._user_proxy is None:
            self._user_proxy = UserProxyAgent(
                name="Poi_User_Proxy_Agent",
                system_message="You are a helpful agent",
                llm_config=self.llm_config,
            )
        return self._user_proxy

    def validate(
        self, name: str, description: str, category: str, location: Optional[str]
    ) -> PoiValidationResult:
        initial_message = f"""Please confirm if the below is a Point of Interest (POI).

- name:  {name}
- description: {description}
"""
        chat_result = self.user_proxy.initiate_chat(
            self.validator_agent,
            message=initial_message,
            summary_method="reflection_with_llm",
            max_turns=1,
        )

        messages = [msg["content"] for msg in chat_result.chat_history]
        last_message = messages[-1]

        result = PoiValidationResult(
            is_valid=last_message.lower() == "yes",
            name=name,
            description=description,
            raw_response=last_message,
        )

        return result
