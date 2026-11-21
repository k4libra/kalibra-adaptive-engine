from uuid import uuid4

import pytest
from httpx import AsyncClient

URL = "/api/v1/mastery-estimates"


@pytest.mark.anyio
async def test_first_answer_starts_from_base_and_returns_camel_case(client: AsyncClient) -> None:
    response = await client.post(
        URL,
        json={"studentId": str(uuid4()), "subtopicId": str(uuid4()), "outcome": "CORRECT"},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["prior"] == 0.30
    assert body["posterior"] == pytest.approx(0.646067, abs=1e-6)
    assert body["level"] == "MEDIUM"
    assert body["initializedFromBase"] is True


@pytest.mark.anyio
async def test_answer_with_history_uses_prior(client: AsyncClient) -> None:
    response = await client.post(
        URL,
        json={
            "studentId": str(uuid4()),
            "subtopicId": str(uuid4()),
            "priorProbability": 0.9,
            "outcome": "INCORRECT",
        },
    )

    body = response.json()
    assert response.status_code == 201
    assert body["initializedFromBase"] is False
    assert body["posterior"] < 0.9


@pytest.mark.anyio
async def test_prior_out_of_range_is_problem_details(client: AsyncClient) -> None:
    response = await client.post(
        URL,
        json={
            "studentId": str(uuid4()),
            "subtopicId": str(uuid4()),
            "priorProbability": 1.5,
            "outcome": "CORRECT",
        },
    )

    assert response.status_code == 422
    assert response.headers["content-type"] == "application/problem+json"


@pytest.mark.anyio
async def test_unknown_outcome_is_rejected(client: AsyncClient) -> None:
    response = await client.post(
        URL,
        json={"studentId": str(uuid4()), "subtopicId": str(uuid4()), "outcome": "MAYBE"},
    )

    assert response.status_code == 422
