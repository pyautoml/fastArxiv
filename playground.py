from papers import Arxiv
from paper_builer import Query
from pyinstrument import Profiler

def main():
    profiler = Profiler()
    arxiv = Arxiv(max_workers=100)
    profiler.start()
    arxiv.papers_save(
        queries=[
            Query(search_query="Transformers", max_results=100),
            Query(search_query="Agentic LLM", max_results=100),
            Query(search_query="LangChain", max_results=100),
        ]
    )
    profiler.stop()
    profiler.print()


if __name__ == "__main__":
    main()
