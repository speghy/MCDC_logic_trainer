"""
Система тестовых случаев для анализа покрытия
"""
from typing import Dict, List, Optional
from dataclasses import dataclass
from .block import Circuit, BlockType


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


class TestSuite:
    """Набор тестовых случаев"""

    def __init__(self, circuit: Circuit):
        self.circuit = circuit
        self.test_cases: List[TestCase] = []
        self.current_case_index = -1
        self.results: Dict[str, bool] = {}  # case_id -> passed

    def add_test_case(self, name: str, inputs: Dict[str, bool],
                      expected_outputs: Dict[str, bool]) -> str:
        """Добавить тестовый случай"""
        import uuid
        case_id = str(uuid.uuid4())[:8]

        # Конвертируем имена блоков в ID если нужно
        actual_inputs = {}
        for block_ref, value in inputs.items():
            block_id = self._find_block_id(block_ref)
            if block_id:
                actual_inputs[block_id] = value

        actual_outputs = {}
        for block_ref, value in expected_outputs.items():
            block_id = self._find_block_id(block_ref)
            if block_id:
                actual_outputs[block_id] = value

        case = TestCase(case_id, name, actual_inputs, actual_outputs)
        self.test_cases.append(case)
        return case_id

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

    def check_results(self, simulator) -> Dict[str, bool]:
        """Проверить результаты выполнения"""
        case = self.get_current_case()
        if not case:
            return {}

        results = {}
        for block_id, expected_value in case.expected_outputs.items():
            block = self.circuit.blocks.get(block_id)
            if block:
                actual_value = block.value
                passed = (actual_value == expected_value)
                results[block_id] = passed

        all_passed = all(results.values())
        case.passed = all_passed
        self.results[case.id] = all_passed

        return results

    def generate_from_truth_table(self):
        """Сгенерировать тестовые случаи из таблицы истинности"""
        # Находим все INPUT блоки
        input_blocks = []
        for block_id, block in self.circuit.blocks.items():
            if block.type == BlockType.INPUT:
                input_blocks.append((block_id, block.name))

        # Находим все OUTPUT блоки
        output_blocks = []
        for block_id, block in self.circuit.blocks.items():
            if block.type == BlockType.OUTPUT:
                output_blocks.append((block_id, block.name))

        # Пока просто создадим несколько тестовых случаев
        # TODO: Генерация всех комбинаций
        if input_blocks and output_blocks:
            # Пример: все INPUT = False
            inputs = {block_id: False for block_id, _ in input_blocks}
            # Ожидаем что OUTPUT тоже False (нужно вычислить)
            self.add_test_case("Все False", inputs, {})

            # Пример: первый INPUT = True, остальные False
            if input_blocks:
                inputs = {block_id: (i == 0) for i, (block_id, _) in enumerate(input_blocks)}
                self.add_test_case("Первый True", inputs, {})

    # ========== НОВЫЕ МЕТОДЫ ==========

    def get_test_case_by_id(self, case_id: str) -> Optional[TestCase]:
        """Найти тестовый случай по ID"""
        for case in self.test_cases:
            if case.id == case_id:
                return case
        return None

    def update_test_case(self, case_id: str, name: str = None,
                         inputs: Dict[str, bool] = None,
                         expected_outputs: Dict[str, bool] = None) -> bool:
        """Обновить тестовый случай"""
        case = self.get_test_case_by_id(case_id)
        if not case:
            return False

        if name is not None:
            case.name = name

        if inputs is not None:
            # Конвертируем имена блоков в ID если нужно
            actual_inputs = {}
            for block_ref, value in inputs.items():
                block_id = self._find_block_id(block_ref)
                if block_id:
                    actual_inputs[block_id] = value
            case.inputs = actual_inputs

        if expected_outputs is not None:
            # Конвертируем имена блоков в ID если нужно
            actual_outputs = {}
            for block_ref, value in expected_outputs.items():
                block_id = self._find_block_id(block_ref)
                if block_id:
                    actual_outputs[block_id] = value
            case.expected_outputs = actual_outputs

        return True

    def delete_test_case(self, case_id: str) -> bool:
        """Удалить тестовый случай"""
        for i, case in enumerate(self.test_cases):
            if case.id == case_id:
                # Если удаляется текущий тест, сбрасываем текущий индекс
                if self.current_case_index == i:
                    self.current_case_index = -1
                elif self.current_case_index > i:
                    self.current_case_index -= 1

                # Удаляем из списка
                del self.test_cases[i]

                # Удаляем результат если есть
                if case_id in self.results:
                    del self.results[case_id]

                return True

        return False

    def get_test_case_index(self, case_id: str) -> Optional[int]:
        """Получить индекс тестового случая по ID"""
        for i, case in enumerate(self.test_cases):
            if case.id == case_id:
                return i
        return None

    def move_test_case_up(self, case_id: str) -> bool:
        """Переместить тестовый случай вверх в списке"""
        index = self.get_test_case_index(case_id)
        if index is None or index <= 0:
            return False

        # Меняем местами
        self.test_cases[index], self.test_cases[index - 1] = \
            self.test_cases[index - 1], self.test_cases[index]

        # Обновляем текущий индекс если нужно
        if self.current_case_index == index:
            self.current_case_index = index - 1
        elif self.current_case_index == index - 1:
            self.current_case_index = index

        return True

    def move_test_case_down(self, case_id: str) -> bool:
        """Переместить тестовый случай вниз в списке"""
        index = self.get_test_case_index(case_id)
        if index is None or index >= len(self.test_cases) - 1:
            return False

        # Меняем местами
        self.test_cases[index], self.test_cases[index + 1] = \
            self.test_cases[index + 1], self.test_cases[index]

        # Обновляем текущий индекс если нужно
        if self.current_case_index == index:
            self.current_case_index = index + 1
        elif self.current_case_index == index + 1:
            self.current_case_index = index

        return True

    def clear_test_cases(self):
        """Очистить все тестовые случаи"""
        self.test_cases.clear()
        self.current_case_index = -1
        self.results.clear()

    def get_statistics(self) -> Dict[str, any]:
        """Получить статистику тестового набора"""
        total = len(self.test_cases)
        passed = sum(1 for case in self.test_cases if case.passed is True)
        failed = sum(1 for case in self.test_cases if case.passed is False)
        not_run = total - passed - failed

        return {
            'total': total,
            'passed': passed,
            'failed': failed,
            'not_run': not_run,
            'pass_percentage': (passed / total * 100) if total > 0 else 0
        }

    def export_to_csv(self, filename: str):
        """Экспортировать тестовые случаи в CSV файл"""
        import csv

        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)

            # Заголовок
            headers = ['Test Case', 'Status', 'Inputs', 'Expected Outputs', 'Passed']
            writer.writerow(headers)

            # Данные
            for case in self.test_cases:
                # Форматируем входы
                inputs_str = ', '.join([f"{self._get_block_name(block_id)}={value}"
                                        for block_id, value in case.inputs.items()])

                # Форматируем выходы
                outputs_str = ', '.join([f"{self._get_block_name(block_id)}={value}"
                                         for block_id, value in case.expected_outputs.items()])

                status = "✓" if case.passed else "✗" if case.passed is False else "○"

                writer.writerow([
                    case.name,
                    status,
                    inputs_str,
                    outputs_str,
                    str(case.passed) if case.passed is not None else "Not Run"
                ])

    def _get_block_name(self, block_id: str) -> str:
        """Получить имя блока по ID"""
        block = self.circuit.blocks.get(block_id)
        if block:
            return block.name
        return f"ID:{block_id}"

    def import_from_csv(self, filename: str):
        """Импортировать тестовые случаи из CSV файла"""
        import csv

        try:
            with open(filename, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                next(reader)  # Пропускаем заголовок

                for row in reader:
                    if len(row) < 3:
                        continue

                    name = row[0]
                    inputs_str = row[2] if len(row) > 2 else ""
                    outputs_str = row[3] if len(row) > 3 else ""

                    # Парсинг входов (формат: "Вход_1=True, Вход_2=False")
                    inputs = {}
                    if inputs_str:
                        for item in inputs_str.split(','):
                            item = item.strip()
                            if '=' in item:
                                block_name, value_str = item.split('=', 1)
                                block_name = block_name.strip()
                                value = value_str.strip().lower() == 'true'

                                # Находим ID блока
                                block_id = self._find_block_id_by_name(block_name)
                                if block_id:
                                    inputs[block_id] = value

                    # Парсинг выходов
                    expected_outputs = {}
                    if outputs_str:
                        for item in outputs_str.split(','):
                            item = item.strip()
                            if '=' in item:
                                block_name, value_str = item.split('=', 1)
                                block_name = block_name.strip()
                                value = value_str.strip().lower() == 'true'

                                # Находим ID блока
                                block_id = self._find_block_id_by_name(block_name)
                                if block_id:
                                    expected_outputs[block_id] = value

                    self.add_test_case(name, inputs, expected_outputs)

            return True
        except Exception as e:
            print(f"Error importing CSV: {e}")
            return False

    def _find_block_id_by_name(self, block_name: str) -> Optional[str]:
        """Найти ID блока по имени"""
        for block_id, block in self.circuit.blocks.items():
            if block.name == block_name:
                return block_id
        return None