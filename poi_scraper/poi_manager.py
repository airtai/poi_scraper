from queue import PriorityQueue
from typing import List, Optional, Set, Tuple, Union
from urllib.parse import urlparse

from poi_scraper.poi_types import (
    PoiData,
    ScoredURL,
    ScraperFactoryProtocol,
    ValidatePoiAgentProtocol,
)


class PoiManager:
    def __init__(self, base_url: str, poi_validator: ValidatePoiAgentProtocol):
        """Initialize the POIManager with a base URL.

        This constructor sets up the initial state of the POIManager, including
        the base URL, domain, visited URLs set, URL priority queue, POI list,
        and lists for storing links with scores.

        Args:
            base_url (str): The base URL to start managing points of interest from.
            poi_validator (ValidatePoiAgentProtocol): The agent to validate points of interest.
        """
        self.base_url = base_url
        self.poi_validator = poi_validator
        self.base_domain = urlparse(base_url).netloc
        self.visited_urls: Set[str] = set()
        self.url_queue: PriorityQueue[ScoredURL] = PriorityQueue()
        self.poi_list: dict[str, dict[str, Union[str, Optional[str]]]] = {}
        self.all_links_with_scores: List[Tuple[str, float]] = []
        self._current_url_links_with_scores: List[Tuple[str, float]] = []

    def register_poi(self, poi: PoiData) -> str:
        """Register a new Point of Interest (POI)."""
        poi_validation_result = self.poi_validator.validate(
            poi.name, poi.description, poi.category, poi.location
        )

        if not poi_validation_result.is_valid:
            return f"POI validation failed for: {poi.name, poi.description}"

        self.poi_list[poi.name] = {
            "description": poi.description,
            "category": poi.category,
            "location": poi.location,
        }
        return f"POI registered: {poi.name}, Category: {poi.category}, Location: {poi.location}"

    def register_link(self, url: str, score: float) -> str:
        self.all_links_with_scores.append((url, score))
        return f"Link registered: {url}, AI score: {score}"

    def process(
        self, scraper_factory: ScraperFactoryProtocol
    ) -> dict[str, dict[str, Union[str, Optional[str]]]]:
        # Create scraper function
        scraper = scraper_factory.create_scraper(self)

        # Initialize with base URL
        self._add_to_queue(self.base_url, 1.0)

        while not self.url_queue.empty():
            current_url = self.url_queue.get().url

            if current_url in self.visited_urls:
                continue

            try:
                # Process URL using AI
                scraper(current_url)

                # Process only new URLs
                self._current_url_links_with_scores = list(
                    set(self.all_links_with_scores)
                    - set(self._current_url_links_with_scores)
                )
                self._process_new_urls()

                # Mark URL as visited
                self.visited_urls.add(current_url)

            except Exception:  # nosec
                # print(f"Error processing URL: {current_url}")
                # print(e)
                continue

        return self.poi_list

    def _process_new_urls(self) -> None:
        """Process new URLs and add them to queue."""
        for url, ai_score in self._current_url_links_with_scores:
            if ai_score < 0.5:
                continue
            if self._should_process_url(url):
                depth_score = self._calculate_depth_score(url)
                final_score = self._calculate_final_score(ai_score, depth_score)
                self._add_to_queue(url, final_score)

    def _should_process_url(self, url: str) -> bool:
        """Check if URL should be processed."""
        if url in self.visited_urls:
            return False

        domain = urlparse(url).netloc
        return domain == self.base_domain

    def _calculate_depth_score(self, url: str) -> float:
        """Calculate depth score based on URL path."""
        depth = len(urlparse(url).path.split("/")) - 1
        if depth == 0:
            return 0.0
        if depth == 1:
            return 0.3
        if depth == 2:
            return 0.5
        if depth == 3:
            return 0.7
        return 0.9

    def _calculate_final_score(self, ai_score: float, depth_score: float) -> float:
        """Calculate final score combining AI and depth scores."""
        return (ai_score * 0.4) + (depth_score * 0.6)

    def _add_to_queue(self, url: str, score: float) -> None:
        """Add URL to priority queue."""
        self.url_queue.put(ScoredURL(url, score))
