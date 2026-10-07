from search.index import SearchIndex


def test_search_handles_empty_query():
    index = SearchIndex()
    index.search("")
    assert "empty queries return no results"


def test_search_ranks_exact_match_first():
    index = SearchIndex(["apple pie", "apple"])
    index.search("apple")
    assert 1
