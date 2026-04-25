from .fda import FDAScraper
from .moh_il import MOHIsraelScraper
from .generic import GenericListScraper
from .rss import RSSScraper

AI_KW = [
    "artificial intelligence", "machine learning", "ai/ml", "ai-enabled",
    "deep learning", "algorithm", "predictive model", "clinical decision support",
    "samd", "software as a medical device", "digital health", "validation",
    "post-market", "monitoring", "drift", "bias", "fairness",
    " ai ", "ai)", "(ai", " ml ",
]

WHOScraper = GenericListScraper(
    source="who",
    region="Global",
    base_domain="who.int",
    seed_urls=[
        "https://www.who.int/teams/digital-health-and-innovation/artificial-intelligence",
        "https://www.who.int/news-room/feature-stories/detail/who-issues-first-global-report-on-artificial-intelligence-(ai)-in-health-and-six-guiding-principles-for-its-design-and-use",
        "https://www.who.int/publications/i/item/9789240029200",
    ],
    keywords=AI_KW,
)

MHRAScraper = GenericListScraper(
    source="mhra",
    region="UK",
    base_domain="gov.uk",
    seed_urls=[
        "https://www.gov.uk/government/publications/software-and-ai-as-a-medical-device-change-programme",
        "https://www.gov.uk/government/collections/software-and-artificial-intelligence-ai-as-a-medical-device",
    ],
    keywords=AI_KW,
)

EMAScraper = GenericListScraper(
    source="ema",
    region="EU",
    base_domain="ema.europa.eu",
    seed_urls=[
        "https://www.ema.europa.eu/en/about-us/how-we-work/data-regulation-big-data-other-sources",
        "https://www.ema.europa.eu/en/news?search_api_fulltext=artificial+intelligence",
    ],
    keywords=AI_KW,
)

StanfordAIMIScraper = GenericListScraper(
    source="stanford_aimi",
    region="US",
    base_domain="stanford.edu",
    seed_urls=[
        "https://aimi.stanford.edu/recent-news",
        "https://aimi.stanford.edu/research/publications",
    ],
    keywords=None,  # whole site is about clinical AI
)

MGBAimScraper = GenericListScraper(
    source="mgb_aim",
    region="US",
    base_domain="mgh.harvard.edu",
    seed_urls=[
        "https://aim.mgh.harvard.edu/",
        "https://aim.mgh.harvard.edu/news/",
    ],
    keywords=None,
)

ALL_SCRAPERS = [
    FDAScraper(),
    MOHIsraelScraper(),  # currently 403; left in so it's auto-fixed when Apify version lands
    WHOScraper,
    MHRAScraper,
    EMAScraper,
    StanfordAIMIScraper,
    MGBAimScraper,
    # Journal RSS feeds — filtered to AI-relevant items via title/summary keywords
    RSSScraper("nejm",            "Global", "https://www.nejm.org/action/showFeed?type=etoc&feed=rss&jc=nejm"),
    RSSScraper("jama",            "Global", "https://jamanetwork.com/rss/site_3/67.xml"),
    RSSScraper("lancet_digital",  "Global", "https://www.thelancet.com/rssfeed/landig_current.xml", keyword_filter=False),  # whole journal is digital health
    RSSScraper("lancet",          "Global", "https://www.thelancet.com/rssfeed/lancet_current.xml"),
    RSSScraper("npj_digital_med", "Global", "https://www.nature.com/npjdigitalmed.rss", keyword_filter=False),  # whole journal is digital medicine
    RSSScraper("health_affairs",  "US",     "https://www.healthaffairs.org/action/showFeed?type=etoc&feed=rss&jc=hlthaff"),
]
