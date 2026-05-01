"""Source target configuration for web monitoring.

Defines the schema for monitored source targets with strict allowlists
and safety controls.
"""

from urllib.parse import urlparse

from pydantic import BaseModel, Field, field_validator


class WebMonitorTarget(BaseModel):
    """Configuration for a monitored web source target.

    All targets are disabled by default and require explicit admin enablement.
    Strict allowlist enforcement prevents open-ended crawling.
    """

    name: str = Field(..., description="Human-readable target name")
    source_type: str = Field(
        ...,
        description="Source classification (e.g., official_police_media, court_news)",
    )
    base_url: str = Field(..., description="Base URL of the source")
    allowed_domains: list[str] = Field(
        ...,
        description="Strict allowlist of domains (e.g., ['saskatoonpolice.ca'])",
    )
    start_urls: list[str] = Field(
        ...,
        description="Starting URLs for the monitor",
    )
    max_depth: int = Field(
        default=1,
        ge=0,
        le=3,
        description="Maximum crawl depth (0=start_urls only, max 3)",
    )
    max_requests: int = Field(
        default=25,
        ge=1,
        le=100,
        description="Maximum requests per run (enforced)",
    )
    concurrency: int = Field(
        default=2,
        ge=1,
        le=5,
        description="Concurrent requests (low by default)",
    )
    crawl_interval_hours: int = Field(
        default=24,
        ge=1,
        le=168,
        description="Hours between scheduled crawls",
    )
    source_tier: str = Field(
        default="news_only_context",
        description="Trust tier: news_only_context, official_police_open_data, etc.",
    )
    enabled: bool = Field(
        default=False,
        description="Whether this target is enabled (disabled by default)",
    )
    extractor_type: str = Field(
        ...,
        description="Extractor to use: police_release_index, court_news_index, etc.",
    )
    robots_txt_obey: bool = Field(
        default=True,
        description="Respect robots.txt",
    )

    @field_validator("allowed_domains")
    @classmethod
    def validate_domains_not_empty(cls, v):
        """Ensure allowlist is not empty."""
        if not v:
            raise ValueError("allowed_domains cannot be empty")
        return v

    @field_validator("start_urls")
    @classmethod
    def validate_start_urls_in_allowlist(cls, v, info):
        """Ensure all start URLs match allowed domains."""
        allowed_domains = info.data.get("allowed_domains", [])
        for url in v:
            domain = urlparse(url).netloc
            # Remove port if present
            if ":" in domain:
                domain = domain.split(":")[0]
            # Check if domain or its parent is in allowlist
            if not any(
                domain == allowed or domain.endswith(f".{allowed}")
                for allowed in allowed_domains
            ):
                raise ValueError(
                    f"Start URL {url} domain {domain} not in allowed_domains"
                )
        return v

    def is_url_allowed(self, url: str) -> bool:
        """Check if a URL is in the allowed domains list.

        Args:
            url: URL to check

        Returns:
            True if URL domain is in allowlist, False otherwise
        """
        domain = urlparse(url).netloc
        # Remove port if present
        if ":" in domain:
            domain = domain.split(":")[0]

        # Check exact match or subdomain
        return any(
            domain == allowed or domain.endswith(f".{allowed}")
            for allowed in self.allowed_domains
        )

    def get_crawlee_config(self) -> dict:
        """Get Crawlee crawler configuration from this target.

        Returns:
            Dictionary of Crawlee configuration options
        """
        return {
            "max_requests_per_crawl": self.max_requests,
            "max_crawl_depth": self.max_depth,
            "max_concurrency": self.concurrency,
        }


# Example target configurations (disabled by default)
# These are templates that can be enabled in admin panel

SASKATOON_POLICE_NEWS_TARGET = WebMonitorTarget(
    name="Saskatoon Police News Releases",
    source_type="official_police_media",
    base_url="https://saskatoonpolice.ca",
    allowed_domains=["saskatoonpolice.ca"],
    start_urls=["https://saskatoonpolice.ca/news/"],
    max_depth=1,
    max_requests=25,
    concurrency=2,
    source_tier="official_police_open_data",
    enabled=False,  # Disabled by default - must be enabled by admin
    extractor_type="police_release_index",
    robots_txt_obey=True,
)

# Additional example targets (all disabled)
COURT_NEWS_EXAMPLE_TARGET = WebMonitorTarget(
    name="Example Court News Page",
    source_type="court_news",
    base_url="https://example-court.gov",
    allowed_domains=["example-court.gov"],
    start_urls=["https://example-court.gov/news/"],
    max_depth=1,
    max_requests=15,
    concurrency=1,
    source_tier="news_only_context",
    enabled=False,
    extractor_type="court_news_index",
    robots_txt_obey=True,
)

CITY_OPEN_DATA_EXAMPLE_TARGET = WebMonitorTarget(
    name="Example City Open Data",
    source_type="city_open_data",
    base_url="https://data.examplecity.gov",
    allowed_domains=["data.examplecity.gov"],
    start_urls=["https://data.examplecity.gov/datasets/"],
    max_depth=1,
    max_requests=20,
    concurrency=2,
    source_tier="official_government_statistics",
    enabled=False,
    extractor_type="city_open_data_landing_page",
    robots_txt_obey=True,
)


# Registry of available targets (all disabled by default)
EXAMPLE_TARGETS = {
    "saskatoon_police_news": SASKATOON_POLICE_NEWS_TARGET,
    "court_news_example": COURT_NEWS_EXAMPLE_TARGET,
    "city_open_data_example": CITY_OPEN_DATA_EXAMPLE_TARGET,
}
