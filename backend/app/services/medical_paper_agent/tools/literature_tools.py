"""
Literature search tools for the Literature Agent.

Provides PubMed and ClinicalTrials.gov search capabilities.
Uses BioPython's Entrez module for NCBI E-utilities access.
"""

import logging
from typing import Any, Optional

from pydantic import BaseModel, Field

logger = logging.getLogger("medical_paper_agent")

# NCBI Entrez configuration
ENTREZ_EMAIL = "medical-paper-agent@example.com"
ENTREZ_TOOL = "MedicalPaperAgent"


class PubMedSearchInput(BaseModel):
    query: str = Field(description="PubMed search query using MeSH terms or keywords")
    max_results: int = Field(
        default=20, description="Maximum number of results to return"
    )


class ArticleAbstractInput(BaseModel):
    pmid: str = Field(description="PubMed ID of the article")


class CitationFormatInput(BaseModel):
    pmid: str = Field(description="PubMed ID")
    style: str = Field(default="apa", description="Citation style: apa, vancouver, ama")


async def search_pubmed(query: str, max_results: int = 20) -> dict[str, Any]:
    """
    Search PubMed using NCBI E-utilities via BioPython.

    Returns a list of article summaries with PMIDs, titles, and abstracts.
    """
    try:
        from Bio import Entrez

        Entrez.email = ENTREZ_EMAIL
        Entrez.tool = ENTREZ_TOOL

        # Search for articles
        handle = Entrez.esearch(
            db="pubmed", term=query, retmax=max_results, sort="relevance"
        )
        search_results = Entrez.read(handle)
        handle.close()

        pmids = search_results.get("IdList", [])
        if not pmids:
            return {
                "references": [],
                "total_found": int(search_results.get("Count", 0)),
                "query": query,
            }

        # Fetch article details
        handle = Entrez.efetch(db="pubmed", id=pmids, rettype="xml", retmode="xml")
        records = Entrez.read(handle)
        handle.close()

        references = []
        for article in records.get("PubmedArticle", []):
            medline = article.get("MedlineCitation", {})
            article_data = medline.get("Article", {})

            # Extract authors
            author_list = article_data.get("AuthorList", [])
            authors = []
            for author in author_list:
                last = author.get("LastName", "")
                first = author.get("ForeName", "")
                if last:
                    authors.append(f"{last} {first}".strip())

            # Extract journal info
            journal_info = article_data.get("Journal", {})
            journal_title = journal_info.get("Title", "")
            pub_date = journal_info.get("JournalIssue", {}).get("PubDate", {})
            year = pub_date.get("Year", "")

            # Extract abstract
            abstract_parts = article_data.get("Abstract", {}).get("AbstractText", [])
            abstract = " ".join(str(part) for part in abstract_parts)

            pmid = str(medline.get("PMID", ""))
            title = str(article_data.get("ArticleTitle", ""))

            references.append(
                {
                    "pmid": pmid,
                    "title": title,
                    "authors": authors,
                    "journal": journal_title,
                    "year": int(year) if year.isdigit() else 0,
                    "abstract": abstract[:1000],  # Truncate long abstracts
                }
            )

        return {
            "references": references,
            "total_found": int(search_results.get("Count", 0)),
            "filtered_count": len(references),
            "query": query,
        }

    except ImportError:
        logger.warning("BioPython not installed, returning mock results")
        return {
            "references": [],
            "total_found": 0,
            "query": query,
            "error": "BioPython not available",
        }
    except Exception as e:
        logger.error(f"PubMed search failed: {e}")
        return {
            "references": [],
            "total_found": 0,
            "query": query,
            "error": str(e),
        }


async def get_article_abstract(pmid: str) -> dict[str, Any]:
    """Fetch a single article's abstract by PMID."""
    try:
        from Bio import Entrez

        Entrez.email = ENTREZ_EMAIL
        Entrez.tool = ENTREZ_TOOL

        handle = Entrez.efetch(db="pubmed", id=pmid, rettype="xml", retmode="xml")
        records = Entrez.read(handle)
        handle.close()

        articles = records.get("PubmedArticle", [])
        if not articles:
            return {"pmid": pmid, "error": "Article not found"}

        article = articles[0]
        medline = article.get("MedlineCitation", {})
        article_data = medline.get("Article", {})
        abstract_parts = article_data.get("Abstract", {}).get("AbstractText", [])
        abstract = " ".join(str(part) for part in abstract_parts)

        return {
            "pmid": pmid,
            "title": str(article_data.get("ArticleTitle", "")),
            "abstract": abstract,
        }

    except ImportError:
        return {"pmid": pmid, "error": "BioPython not available"}
    except Exception as e:
        return {"pmid": pmid, "error": str(e)}


async def search_clinicaltrials(query: str, max_results: int = 10) -> dict[str, Any]:
    """
    Search ClinicalTrials.gov for registered trials.

    Uses the ClinicalTrials.gov API v2.
    """
    try:
        import httpx

        url = "https://clinicaltrials.gov/api/v2/studies"
        params = {
            "query.term": query,
            "pageSize": min(max_results, 100),
            "format": "json",
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()

        studies = data.get("studies", [])
        results = []
        for study in studies:
            protocol = study.get("protocolSection", {})
            id_module = protocol.get("identificationModule", {})
            status_module = protocol.get("statusModule", {})

            results.append(
                {
                    "nct_id": id_module.get("nctId", ""),
                    "title": id_module.get("briefTitle", ""),
                    "status": status_module.get("overallStatus", ""),
                    "phase": protocol.get("designModule", {}).get("phases", []),
                }
            )

        return {
            "trials": results,
            "total_found": data.get("totalCount", 0),
            "query": query,
        }

    except Exception as e:
        logger.error(f"ClinicalTrials.gov search failed: {e}")
        return {"trials": [], "total_found": 0, "query": query, "error": str(e)}


def format_citation(reference: dict[str, Any], style: str = "vancouver") -> str:
    """Format a reference in the specified citation style."""
    authors = reference.get("authors", [])
    title = reference.get("title", "")
    journal = reference.get("journal", "")
    year = reference.get("year", "")
    pmid = reference.get("pmid", "")

    if style == "vancouver":
        # Vancouver style: Author1, Author2, et al. Title. Journal. Year;
        author_str = ", ".join(authors[:3])
        if len(authors) > 3:
            author_str += ", et al"
        return f"{author_str}. {title} {journal}. {year}. PMID: {pmid}"

    elif style == "apa":
        author_str = ", ".join(authors[:6])
        if len(authors) > 6:
            author_str += ", ... "
        return f"{author_str} ({year}). {title} {journal}."

    else:
        return f"{', '.join(authors[:3])}. {title} {journal} {year}."
