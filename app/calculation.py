"""Calculation objects and the factory that creates them."""

from datetime import datetime, timezone

from .operations import OperationFactory, OperationStrategy


class Calculation:
    """Store the operands and operation for one calculation."""

    def __init__(
        self,
        first_number: float,
        second_number: float,
        operator_symbol: str,
        operation: OperationStrategy,
    ):
        self.first_number = first_number
        self.second_number = second_number
        self.operator_symbol = operator_symbol
        self.operation = operation
        self.result = None
        self.timestamp = datetime.now(timezone.utc).isoformat()

    def perform(self) -> float:
        """Run the stored operation and return its result."""
        self.result = self.operation.execute(self.first_number, self.second_number)
        return self.result

    def __str__(self) -> str:
        """Format the calculation and its result for display."""
        result = self.perform()
        return (
            f"{self.first_number} {self.operator_symbol} "
            f"{self.second_number} = {result}"
        )


class CalculationFactory:
    """Select and create calculations based on an operator symbol."""

    @classmethod
    def supports(cls, operator: str) -> bool:
        """Return whether the operator is supported."""
        return OperationFactory.supports(operator)

    @classmethod
    def create(
        cls, operator: str, first_number: float, second_number: float
    ) -> Calculation:
        """Create a calculation instance, raising for unknown operators."""
        operation = OperationFactory.create(operator)
        return Calculation(first_number, second_number, operator, operation)