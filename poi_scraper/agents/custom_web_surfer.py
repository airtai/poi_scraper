from typing import Annotated, Any, Optional

from autogen.agentchat.chat import ChatResult
from fastagency.runtimes.autogen.tools import WebSurferTool
from pydantic import BaseModel, Field, HttpUrl


class CustomWebSurferAnswer(BaseModel):
    task: Annotated[str, Field(..., description="The task to be completed")]
    is_successful: Annotated[
        bool, Field(..., description="Whether the task was successful")
    ]
    poi_details: Annotated[
        str,
        Field(..., description="The details of all the POIs found in the webpage"),
    ]
    visited_links: Annotated[
        list[HttpUrl],
        Field(..., description="The list of visited links to generate the POI details"),
    ]

    @staticmethod
    def get_example_answer() -> "CustomWebSurferAnswer":
        return CustomWebSurferAnswer(
            task="Collect Points of Interest data and links with score from the webpage https://www.kayak.co.in/Chennai.13827.guide",
            is_successful=True,
            poi_details="Below are the list of all the POIs found in the webpage: \n\n1. Name: Marina Beach, Location: Chennai\n2. Name: Kapaleeshwarar Temple, Location: Chennai\n3. Name: Arignar Anna Zoological Park, Location: Chennai\n4. Name: Guindy National Park. Below are the list of all links found in the webpage: 1. link: https://www.kayak.co.in/Chennai.13827.guide/activities, score: 0.75\n2. link: https://www.kayak.co.in/Chennai.13827.guide/contact-us, score: 0.0\n5. link: https://www.kayak.co.in/Chennai.13827.guide/places, score: 1.0\n\n",
            visited_links=[
                "https://www.kayak.co.in/Chennai.13827.guide",
            ],
        )


class CustomWebSurferTool(WebSurferTool):  # type: ignore[misc]
    def __init__(self, *args: Any, **kwargs: Any):
        """Initialize the CustomWebSurferTool with the given arguments.

        Args:
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.
        """
        super().__init__(*args, **kwargs)

    @property
    def system_message(self) -> str:
        return (
            """You are in charge of navigating the web_surfer agent to scrape the web.
web_surfer is able to CLICK on links, SCROLL down, and scrape the content of the web page. e.g. you cen tell him: "Click the 'Getting Started' result".
Each time you receive a reply from web_surfer, you need to tell him what to do next. e.g. "Click the TV link" or "Scroll down".

You need to guide the web_surfer agent to gather Points of Interest (POIs) on a given webpage. Instruct the web_surfer to visit the
specified page and scroll down until the very end to view the full content.

Guiding Examples:
    - "Click the "given webpage" - This way you will navigate to the given webpage and you will find more information about the POIs.
    - "Scroll down" - this will get you more information about the POIs on the page.
    - "Register the POI" - this will get you the POI information from the page.
    - "Register new link" - this will get you the new link information from the page.


For a given page your objective is to:
    - Collect as many POIs as possible from the given webpage.
    - Return a list of links available on that page along with a score for each link. The score be in the range of 0 to 1. The score should be based on the likelihood that the link will lead to more POIs collections.

Follow the below instructions for collecting the POI's and new links from the webpage:

GENERAL INSTRUCTIONS:
- You MUST visit the full webpage. This is non-negotiable and you will be penalized if you do not do so.
- As you scroll the webpage, collect as much POI's as possible from the given webpage.
- Do not click on any links or navigate to other pages. Focus solely on the current page.
- Create a summary after you have collected all the POI's from the webpage.  The summary must be in English!
- If you get some 40x error, please do NOT give up immediately, but try again on the same page. Give up only if you get 40x error after multiple attempts.


POI COLLECTION INSTRUCTIONS:
- If the webpage has POI information, then encode the POI name, location, category and description as a JSON string. For example:
    {
        "name":"Marina Beach",
        "location":"Chennai",
        "category":"Beach",
        "description":"Marina Beach is a natural urban beach in Chennai, Tamil Nadu, India, along the Bay of Bengal. The beach runs from near Fort St. George in the north to Foreshore Estate in the south, a distance of 6.0 km (3.7 mi), making it the longest natural urban beach in the country."
    }
- Sometimes the webpages will have the category names like "Explore Chennai", "Things to do in Chennai", "Places to visit in Chennai" etc. You SHOULD NOT consider these as POIs. The POI's are the specific names like "Marina Beach", "Kapaleeshwarar Temple", "Arignar Anna Zoological Park" etc. NEVER EVER break this rule.
- If there is no POI infomation in the given page then return "The page does not contain any POI information".

NEW LINK COLLECTION INSTRUCTIONS:
    - For each link on the page, assign a score between 0 and 1 based on the context of the link. The score should be based on the likelihood that the link will lead to more POIs.
    - If the link is likely to lead to more POIs, assign a score closer to 1. If the link is unlikely to lead to more POIs, assign a score closer to 0.
    - If the url contains information about activities or broad categories where people can visit or gather such as tourist attractions, landmarks, parks, museums, cultural venues, and historic sites then assign a score closer to 1.0.
    - If the url contains information about contact-us, transport, about-us, privacy-policy, terms-and-conditions, etc. then assign a score closer to 0.0.
    - For each link you MUST call `register_link` function to record the link along with the score (0.0 to 1.0) indicating the relevance of the link to the POIs. This is a very important instruction and you will be penalised if you do not do so.

    - Few examples of the links with score:
        - link: https://www.kayak.co.in/Chennai.13827.guide/places, score: 1.0
        - link: https://www.kayak.co.in/Chennai.13827.guide/activities, score: 1.0
        - link: https://www.kayak.co.in/Chennai.13827.guide/hotels/Taj-Coromandel, score: 1.0
        - link: https://www.kayak.co.in/Chennai.13827.guide/nightlife, score: 1.0
        - link: https://www.kayak.co.in/Chennai.13827.guide/food, score: 0.75
        - link: https://www.kayak.co.in/Chennai.13827.guide/contact-us, score: 0.0
        - link: https://www.kayak.co.in/Chennai.13827.guide/transport, score: 0.5
        - link: https://www.kayak.co.in/Chennai.13827.guide/contact-us, score: 0.0
        - link: https://www.kayak.co.in/Chennai.13827.guide/about-us, score: 0.0
        - link: https://www.kayak.co.in/Chennai.13827.guide/privacy-policy, score: 0.0
        - link: https://www.kayak.co.in/Chennai.13827.guide/faq, score: 0.0


FINAL MESSAGE:
- Once you have retrieved all the POI's from the webpage, all links with score and created the summary, you need to send the JSON-encoded summary to the web_surfer.
- You MUST not include any other text or formatting in the message, only JSON-encoded summary!

"""
            + f"""An example of the JSON-encoded summary:
{self.example_answer.model_dump_json()}

TERMINATION:
When YOU are finished and YOU have created JSON-encoded answer, write a single 'TERMINATE' to end the task.

OFTEN MISTAKES:
- Enclosing JSON-encoded answer in any other text or formatting including '```json' ... '```' or similar!
- Considering the category names like "Explore Chennai", "Things to do in Chennai", "Places to visit in Chennai" etc. as POIs. The POI's are the specific names like "Marina Beach", "Kapaleeshwarar Temple", "Arignar Anna Zoological Park" etc.
"""
        )

    @property
    def initial_message(self) -> str:
        return f"""We are tasked with the following task: {self.task}"""

    @property
    def error_message(self) -> str:
        return f"""Please output the JSON-encoded answer only in the following message before trying to terminate the chat.

IMPORTANT:
  - NEVER enclose JSON-encoded answer in any other text or formatting including '```json' ... '```' or similar!
  - NEVER write TERMINATE in the same message as the JSON-encoded answer!

EXAMPLE:

{self.example_answer.model_dump_json()}

NEGATIVE EXAMPLES:

1. Do NOT include 'TERMINATE' in the same message as the JSON-encoded answer!

{self.example_answer.model_dump_json()}

TERMINATE

2. Do NOT include triple backticks or similar!

```json
{self.example_answer.model_dump_json()}
```

THE LAST ERROR MESSAGE:

{self.last_is_termination_msg_error}

"""

    def is_termination_msg(self, msg: dict[str, Any]) -> bool:
        # print(f"is_termination_msg({msg=})")
        if (
            "content" in msg
            and msg["content"] is not None
            and "TERMINATE" in msg["content"]
        ):
            return True
        try:
            CustomWebSurferAnswer.model_validate_json(msg["content"])
            return True
        except Exception as e:
            self.last_is_termination_msg_error = str(e)
            return False

    def _get_error_message(self, chat_result: ChatResult) -> Optional[str]:
        messages = [msg["content"] for msg in chat_result.chat_history]
        last_message = messages[-1]
        if "TERMINATE" in last_message:
            return self.error_message

        try:
            CustomWebSurferAnswer.model_validate_json(last_message)
        except Exception:
            return self.error_message

        return None

    def _get_answer(self, chat_result: ChatResult) -> CustomWebSurferAnswer:
        messages = [msg["content"] for msg in chat_result.chat_history]
        last_message = messages[-1]
        return CustomWebSurferAnswer.model_validate_json(last_message)

    def _chat_with_websurfer(
        self, message: str, clear_history: bool, **kwargs: Any
    ) -> CustomWebSurferAnswer:
        msg: Optional[str] = message

        while msg is not None:
            chat_result = self.websurfer.initiate_chat(
                self.assistant,
                clear_history=clear_history,
                message=msg,
            )
            msg = self._get_error_message(chat_result)
            clear_history = False

        return self._get_answer(chat_result)

    def _get_error_from_exception(self, task: str, e: Exception) -> str:
        answer = CustomWebSurferAnswer(
            task=task,
            is_successful=False,
            poi_details=f"unexpected error occurred: {e!s}",
            visited_links=[],
        )

        return self.create_final_reply(task, answer)

    def create_final_reply(self, task: str, message: CustomWebSurferAnswer) -> str:
        retval = (
            "We have successfully completed the task:\n\n"
            if message.is_successful
            else "We have failed to complete the task:\n\n"
        )
        retval += f"{task}\n\n"
        retval += f"poi_details: {message.poi_details}\n\n"
        retval += "Visited links:\n"
        for link in message.visited_links:
            retval += f"  - {link}\n"

        return retval

    @property
    def example_answer(self) -> CustomWebSurferAnswer:
        return CustomWebSurferAnswer.get_example_answer()
