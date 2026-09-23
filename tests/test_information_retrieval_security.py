from src.security.student_4_information_retrieval import RetrievalQualityChecker, evaluate_retrieval_cases


def test_retrieval_accuracy_requires_expected_relevance():
    checker = RetrievalQualityChecker()
    report = checker.evaluate_case(
        {
            "id": "ir-01",
            "query": "Apple revenue growth and margins",
            "results": [
                {"title": "Apple quarterly revenue rises as services gains expand margins", "snippet": "Apple reported stronger revenue growth with improving operating margins."},
                {"title": "Tesla recalls some vehicles in Europe", "snippet": "Electric vehicle company issues recall for software issue."},
            ],
            "expected_keywords": ["apple", "revenue", "growth", "margins"],
        }
    )

    assert report["passed"] is True
    assert report["relevance_score"] >= 0.6


def test_evaluator_reports_accuracy_summary():
    cases = [
        {
            "id": "ir-01",
            "query": "Nvidia chip demand outlook",
            "results": [
                {"title": "NVIDIA AI chip demand remains strong", "snippet": "Analysts expect robust demand for AI accelerators."},
                {"title": "Oil prices rise after supply news", "snippet": "Crude markets move sharply after supply disruption."},
            ],
            "expected_keywords": ["nvidia", "chip", "demand", "ai"],
        },
        {
            "id": "ir-02",
            "query": "Banking sector stress",
            "results": [
                {"title": "Government debt yields move lower", "snippet": "Treasury yields fell as investors sought safety."},
                {"title": "Consumer spending picks up", "snippet": "Retail sales improve as household demand improves."},
            ],
            "expected_keywords": ["banking", "stress", "credit"],
        },
    ]

    report = evaluate_retrieval_cases(cases)
    assert report["total"] == 2
    assert report["failed"] == 1
    assert report["pass_rate"] < 1.0
