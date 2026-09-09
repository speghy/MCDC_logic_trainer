"""
Система тестовых случаев для анализа покрытия
"""
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime
from logic_trainer.core.block import Circuit, BlockType


@dataclass
class TestCase:
    """Один тестовый случай"""
    id: str
    name: str
    inputs: Dict[str, bool]  # {block_id: value}
    expected_outputs: Dict[str, bool]  # {block_id: value}
    passed: Optional[bool] = None  # None = не запущен, True/False = результат

    def __str__(self):
        status = "✓" if self.passed else "✗" if self.passed is False else "○"
        return f"{status} {self.name}"

    def update(self, name: str = None, inputs: Dict[str, bool] = None,
               expected_outputs: Dict[str, bool] = None):
        """Обновить тестовый случай"""
        if name:
            self.name = name
        if inputs:
            self.inputs = inputs
        if expected_outputs:
            self.expected_outputs = expected_outputs
        self.passed = None  # Сбрасываем результат при обновлении


class TestSuite:
    """Набор тестовых случаев"""

    def __init__(self, circuit: Circuit):
        self.circuit = circuit
        self.test_cases: List[TestCase] = []
        self.current_case_index = -1

    def add_test_case(self, name: str, inputs: Dict[str, bool],
                      expected_outputs: Dict[str, bool]) -> str:
        """Добавить тестовый случай"""
        import uuid

        case_id = str(uuid.uuid4())[:8]

        # Конвертируем имена блоков в ID если нужно
        actual_inputs = self._normalize_block_dict(inputs)
        actual_outputs = self._normalize_block_dict(expected_outputs)

        case = TestCase(case_id, name, actual_inputs, actual_outputs)
        self.test_cases.append(case)
        return case_id

    def update_test_case(self, case_id: str, **kwargs):
        """Обновить существующий тестовый случай"""
        for case in self.test_cases:
            if case.id == case_id:
                if 'inputs' in kwargs:
                    kwargs['inputs'] = self._normalize_block_dict(kwargs['inputs'])
                if 'expected_outputs' in kwargs:
                    kwargs['expected_outputs'] = self._normalize_block_dict(kwargs['expected_outputs'])
                case.update(**kwargs)
                break

    def delete_test_case(self, case_id: str):
        """Удалить тестовый случай"""
        self.test_cases = [case for case in self.test_cases if case.id != case_id]
        # Корректируем текущий индекс
        if self.current_case_index >= len(self.test_cases):
            self.current_case_index = max(-1, len(self.test_cases) - 1)

    def _normalize_block_dict(self, block_dict: Dict[str, bool]) -> Dict[str, bool]:
        """Нормализовать словарь блоков (конвертировать имена в ID)"""
        normalized = {}
        for block_ref, value in block_dict.items():
            block_id = self._find_block_id(block_ref)
            if block_id:
                normalized[block_id] = value
        return normalized

    def _find_block_id(self, block_ref: str) -> Optional[str]:
        """Найти ID блока по имени или ID"""
        # Пробуем как ID
        if block_ref in self.circuit.blocks:
            return block_ref

        # Ищем по имени
        for block_id, block in self.circuit.blocks.items():
            if block.name == block_ref:
                return block_id

        return None

    def get_current_case(self) -> Optional[TestCase]:
        """Получить текущий тестовый случай"""
        if 0 <= self.current_case_index < len(self.test_cases):
            return self.test_cases[self.current_case_index]
        return None

    def set_current_case(self, index: int):
        """Установить текущий тестовый случай"""
        if 0 <= index < len(self.test_cases):
            self.current_case_index = index

    def apply_current_case(self):
        """Применить текущий тестовый случай к схеме"""
        case = self.get_current_case()
        if not case:
            return

        # Сбрасываем схему
        for block in self.circuit.blocks.values():
            block.value = None
            block.input_values = [None] * len(block.input_connections)

        # Устанавливаем значения INPUT блоков
        for block_id, value in case.inputs.items():
            block = self.circuit.blocks.get(block_id)
            if block and block.type == BlockType.INPUT:
                block.value = value

    def check_results(self, simulator) -> Dict[str, Dict]:
        """Проверить результаты выполнения"""
        case = self.get_current_case()
        if not case:
            return {}

        results = {}
        total_passed = True

        for block_id, expected_value in case.expected_outputs.items():
            block = self.circuit.blocks.get(block_id)
            if block:
                actual_value = block.value
                passed = (actual_value == expected_value)

                if not passed:
                    total_passed = False

                results[block_id] = {
                    'expected': expected_value,
                    'actual': actual_value,
                    'passed': passed,
                    'block_name': block.name
                }

        case.passed = total_passed
        return results