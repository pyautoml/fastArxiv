from papers import Arxiv
from paper_builer import Query
from pyinstrument import Profiler

def main():
    profiler = Profiler()
    arxiv = Arxiv(logger=True, log_level="DEBUG", max_workers=100)
    profiler.start()
    arxiv.get_papers(
        queries=[
            Query(search_query="Transformers", max_results=5),
            Query(search_query="Agentic LLM", max_results=5),
            Query(search_query="LangChain", max_results=5),
        ]
    )
    profiler.stop()
    profiler.print()


if __name__ == "__main__":
    main()
