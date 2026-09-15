from functools import lru_cache

from fastapi import APIRouter, Body

from centinela.agents.transactions import TransactionAgent, TransactionInput
from centinela.schemas.common import Decision

router = APIRouter(prefix="/transactions", tags=["transactions"])


@lru_cache
def get_agent() -> TransactionAgent:
    return TransactionAgent()


@router.post("/evaluate", response_model=Decision)
def evaluate_transaction(transaction: TransactionInput) -> Decision:
    return get_agent().evaluate(transaction)


@router.post("/evaluate/batch", response_model=list[Decision])
def evaluate_batch(transactions: list[TransactionInput] = Body(max_length=200)) -> list[Decision]:
    if len(transactions) > 200:
        from fastapi import HTTPException
        raise HTTPException(422, "El lote admite un máximo de 200 transacciones")
    agent = get_agent()
    return [agent.evaluate(transaction) for transaction in transactions]

