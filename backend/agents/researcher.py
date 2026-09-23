"""ResearcherAgent – executes web search and RAG retrieval for each sub-task."""



from __future__ import annotations



import json

import re

from typing import Any



from langchain_core.output_parsers import StrOutputParser

from langchain_core.prompts import (

    ChatPromptTemplate,

    HumanMessagePromptTemplate,

    SystemMessagePromptTemplate,

)

from langchain_openai import ChatOpenAI

from tenacity import retry, stop_after_attempt, wait_exponential



from backend.agents.base import BaseAgent

from backend.core.config import get_settings

from backend.models.state import ResearchState

from backend.tools.web_search import fetch_web_sources, sources_to_search_dicts



SYSTEM_PROMPT = """\

You are an expert research analyst. You are given a specific research \

sub-question and a collection of raw search results.



Your task:

1. Analyse the search results carefully.

2. Synthesise a concise, factual answer to the sub-question.

3. Cite the sources you relied on.



Return your output as a JSON object with exactly two keys:

  "findings" – a clear, well-structured paragraph answering the question.

  "sources" – a JSON array of objects, each with keys "url", "title", and \

               "relevance_score" (0.0–1.0).



Return ONLY valid JSON. No markdown fences, no extra text."""



HUMAN_PROMPT = """\

Sub-question: {sub_question}



Raw search results:

{search_results}"""



_DEPTH_MAX_RESULTS = {"quick": 4, "standard": 6, "deep": 8}





class ResearcherAgent(BaseAgent):

    """Executes research for every sub-task in the plan."""



    name: str = "researcher"



    def __init__(

        self,

        llm: Any | None = None,

        tavily_tool: Any | None = None,

        rag_pipeline: Any | None = None,

    ) -> None:

        settings = get_settings()

        default_llm = llm or ChatOpenAI(

            model=settings.openai_model,

            temperature=0.1,

            api_key=settings.openai_api_key or "demo-key",

        )

        super().__init__(name="researcher", llm=default_llm)



        self.tavily_tool = tavily_tool

        self.rag_pipeline = rag_pipeline

        self._chain: Any | None = None



        self._prompt = ChatPromptTemplate.from_messages(

            [

                SystemMessagePromptTemplate.from_template(SYSTEM_PROMPT),

                HumanMessagePromptTemplate.from_template(HUMAN_PROMPT),

            ]

        )

        self._default_chain = self._prompt | self.llm | StrOutputParser()



    @staticmethod

    def _task_text(item: Any) -> str:

        if isinstance(item, dict):

            return str(item.get("task", item.get("query", str(item))))

        return str(item)



    @staticmethod

    def _max_results_for_depth(depth: str) -> int:

        return _DEPTH_MAX_RESULTS.get(depth, 6)



    async def _search_web(self, query: str, max_results: int) -> list[dict]:

        """Search the web via Tavily or DuckDuckGo."""

        if self.tavily_tool is not None:

            results = await self.tavily_tool.search(query)

            return [

                {

                    "title": r.title,

                    "url": r.url,

                    "content": r.content,

                    "score": r.score,

                }

                for r in results

            ]



        settings = get_settings()

        sources = await fetch_web_sources(

            query,

            max_results=max_results,

            settings=settings,

        )

        return sources_to_search_dicts(sources)



    async def _rag_retrieve(self, query: str) -> list[dict]:

        if self.rag_pipeline is None:

            return []

        try:

            rag_result = await self.rag_pipeline.query(query)

            return [

                {

                    "title": src.get("title", "RAG Document"),

                    "url": src.get("source_url", "rag_store"),

                    "content": rag_result.answer_context,

                    "score": src.get("score", 0.0),

                }

                for src in rag_result.sources

            ]

        except Exception as exc:

            self.logger.warning("rag_retrieval_failed", error=str(exc))

            return []



    @staticmethod

    def _first_sentences(text: str, max_sentences: int = 3) -> str:

        text = re.sub(r"\s+", " ", text.strip())

        if not text:

            return ""

        parts = re.split(r"(?<=[.!?])\s+", text)

        chunk = " ".join(parts[:max_sentences]).strip()

        if chunk and chunk[-1] not in ".!?":

            chunk += "."

        return chunk



    @classmethod

    def _synthesise_offline(

        cls, sub_question: str, raw_results: list[dict]

    ) -> dict[str, Any]:

        """Build findings from web snippets without an LLM."""

        if not raw_results:

            return {

                "findings": (

                    f"No web results were retrieved for '{sub_question}'. "

                    "Try rephrasing the question or check your network connection."

                ),

                "sources": [],

            }



        intro = (

            f"Based on current web sources, here is what relates to: {sub_question}"

        )

        body_parts: list[str] = []

        sources: list[dict] = []



        for r in raw_results[:5]:

            title = r.get("title", "Source")

            url = r.get("url", "")

            content = cls._first_sentences(r.get("content", ""), 4)

            if content:

                body_parts.append(content)

            score = float(r.get("score", 0.7))

            if url:

                sources.append(

                    {

                        "url": url,

                        "title": title,

                        "relevance_score": round(score, 2),

                    }

                )



        findings = intro + "\n\n" + "\n\n".join(body_parts)

        return {"findings": findings, "sources": sources}



    @retry(

        stop=stop_after_attempt(3),

        wait=wait_exponential(multiplier=1, min=2, max=30),

        reraise=True,

    )

    async def _synthesise(

        self, sub_question: str, raw_results: list[dict]

    ) -> dict:

        """Use the LLM to synthesise raw search results into findings."""

        formatted_results = "\n\n".join(

            f"- Title: {r.get('title', 'N/A')}\n"

            f"  URL: {r.get('url', 'N/A')}\n"

            f"  Content: {r.get('content', 'N/A')}"

            for r in raw_results

        )



        chain = self._chain or self._default_chain

        raw: str = await chain.ainvoke(

            {

                "sub_question": sub_question,

                "search_results": formatted_results or "(no results found)",

            }

        )

        cleaned = raw.strip()

        if cleaned.startswith("```"):

            cleaned = cleaned.split("\n", 1)[1]

            cleaned = cleaned.rsplit("```", 1)[0]

        return json.loads(cleaned)



    async def _research_subtask(

        self,

        sub_question: str,

        *,

        max_results: int,

        use_llm: bool,

    ) -> tuple[dict, list[dict]]:

        """Research a single sub-question."""

        search_results = await self._search_web(sub_question, max_results)

        if not search_results:

            search_results = await self._search_web(

                sub_question.split("?")[0][:120],

                max_results,

            )

        rag_results = await self._rag_retrieve(sub_question)

        combined = self._deduplicate(search_results + rag_results)



        if use_llm and combined:

            try:

                synthesised = await self._synthesise(sub_question, combined)

            except Exception as exc:

                self.logger.warning(

                    "llm_synthesis_failed_using_offline",

                    error=str(exc),

                )

                synthesised = self._synthesise_offline(sub_question, combined)

        else:

            synthesised = self._synthesise_offline(sub_question, combined)



        findings: str = synthesised.get("findings", "")

        sources: list[dict] = synthesised.get("sources", [])

        if not sources and combined:

            sources = [

                {

                    "url": r.get("url", ""),

                    "title": r.get("title", "Source"),

                    "relevance_score": float(r.get("score", 0.6)),

                }

                for r in combined[:5]

                if r.get("url")

            ]



        result = {

            "query": sub_question,

            "findings": findings,

            "sources": sources,

        }

        citations = [

            {

                "text": findings,

                "source_url": src.get("url", ""),

                "title": src.get("title", ""),

                "relevance_score": float(src.get("relevance_score", 0.0)),

            }

            for src in sources

        ]

        return result, citations



    def _deduplicate(self, items: list[dict]) -> list[dict]:

        seen: set[str] = set()

        unique: list[dict] = []

        for item in items:

            url = item.get("url", "")

            if url and url in seen:

                continue

            if url:

                seen.add(url)

            unique.append(item)

        return unique



    async def execute(self, state: ResearchState) -> dict[str, Any]:

        """Run research for every sub-task in *state['plan']*."""

        plan: list[Any] = state.get("plan", [])

        if not plan:

            raise ValueError("No research plan found. Run PlannerAgent first.")



        settings = get_settings()

        depth = (state.get("metadata") or {}).get("depth", "standard")

        max_results = self._max_results_for_depth(depth)

        use_llm = settings.has_openai and not settings.demo_mode



        self.logger.info(

            "research_started",

            num_sub_tasks=len(plan),

            use_llm=use_llm,

            max_results=max_results,

        )



        all_results: list[dict] = []

        all_citations: list[dict] = []



        for idx, item in enumerate(plan, 1):

            sub_question = self._task_text(item)

            self.logger.info(

                "researching_subtask",

                subtask_index=idx,

                total=len(plan),

                sub_question=sub_question,

            )

            try:

                result, citations = await self._research_subtask(

                    sub_question,

                    max_results=max_results,

                    use_llm=use_llm,

                )

                all_results.append(result)

                all_citations.extend(citations)

            except Exception as exc:

                self.logger.error(

                    "subtask_research_failed",

                    sub_question=sub_question,

                    error=str(exc),

                )

                all_results.append(

                    {

                        "query": sub_question,

                        "findings": f"Research failed: {exc}",

                        "sources": [],

                    }

                )



        self.logger.info(

            "research_completed",

            results_count=len(all_results),

            citations_count=len(all_citations),

        )

        return {

            "research_results": all_results,

            "citations": all_citations,

        }


