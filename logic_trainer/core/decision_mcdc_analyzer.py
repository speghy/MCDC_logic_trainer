"""
Анализатор MC/DC покрытия для веток (решений) по DO-178C Level A
"""
from typing import Dict, List, Set, Tuple, Optional, Any
from dataclasses import dataclass
from logic_trainer.core.block import Circuit, LogicBlock, BlockType
from logic_trainer.core.test_cases import TestSuite, TestCase


@dataclass
class MCDC_Pair:
    """Пара тестов, демонстрирующая MC/DC для входа блока"""
    test1_index: int
    test2_index: int
    test1_name: str
    test2_name: str
    changed_input: str  # ID входа, который изменился
    block_output_changed: bool  # Изменился ли выход блока
    circuit_output_changed: bool  # Изменился ли выход схемы
    changed_circuit_outputs: List[str]  # Какие выходы схемы изменились


@dataclass
class BlockMCDC_Status:
    """Статус MC/DC покрытия для блока"""
    block_id: str
    block_name: str
    block_type: BlockType

    # Для каждого входа блока
    input_status: Dict[str, bool]  # input_id -> покрыт ли MC/DC
    mcdc_pairs: Dict[str, List[MCDC_Pair]]  # input_id -> список MC/DC пар

    # Общий статус блока
    all_inputs_covered: bool  # Все ли входы покрыты MC/DC
    has_true_branch: bool  # Было ли значение True
    has_false_branch: bool  # Было ли значение False

    # Рекомендации
    missing_pairs: List[str]  # Описание недостающих пар


class DecisionMCDC_Analyzer:
    """Анализатор MC/DC покрытия веток по DO-178C Level A"""

    def __init__(self, circuit: Circuit):
        self.circuit = circuit
        self.block_statuses: Dict[str, BlockMCDC_Status] = {}
        self.test_data: List[Dict] = []  # Данные по всем тестам

    def collect_test_data(self, test_suite: TestSuite, simulator) -> List[Dict]:
        """
        Собрать данные по всем тестам:
        - Значения всех блоков для каждого теста
        - Значения выходов схемы
        """
        print(f"\n{'=' * 60}")
        print("СБОР ДАННЫХ ДЛЯ MC/DC АНАЛИЗА ВЕТОК")
        print(f"{'=' * 60}")

        self.test_data.clear()
        original_states = {}

        # Сохраняем исходное состояние схемы
        for block_id, block in self.circuit.blocks.items():
            original_states[block_id] = block.value

        # Для каждого теста
        for i, test_case in enumerate(test_suite.test_cases):
            print(f"Тест {i + 1}/{len(test_suite.test_cases)}: '{test_case.name}'")

            # Сбрасываем симулятор
            simulator.reset()

            # Применяем тест
            test_suite.set_current_case(i)
            test_suite.apply_current_case()

            # Запускаем симуляцию до завершения
            simulator.active_frontier.clear()
            for block_id, block in self.circuit.blocks.items():
                if block.type == BlockType.INPUT and block.value is not None:
                    simulator.active_frontier.add(block_id)

            max_steps = 50
            for _ in range(max_steps):
                if not simulator.active_frontier:
                    break
                simulator.simulate_step()

            # Собираем данные
            block_states = {}
            for block_id, block in self.circuit.blocks.items():
                block_states[block_id] = block.value

            # Собираем выходы схемы
            circuit_outputs = {}
            for block_id, block in self.circuit.blocks.items():
                if block.type == BlockType.OUTPUT:
                    circuit_outputs[block_id] = block.value

            test_data = {
                'index': i,
                'name': test_case.name,
                'inputs': test_case.inputs.copy(),
                'expected_outputs': test_case.expected_outputs.copy(),
                'block_states': block_states,
                'circuit_outputs': circuit_outputs,
                'passed': test_case.passed
            }

            self.test_data.append(test_data)

            # Логируем для отладки
            print(f"  Входы: {len(test_case.inputs)}, Выходы: {len(circuit_outputs)}")
            print(f"  Значения блоков: {sum(1 for v in block_states.values() if v is not None)}")

        # Восстанавливаем исходное состояние
        simulator.reset()
        for block_id, value in original_states.items():
            block = self.circuit.blocks.get(block_id)
            if block:
                block.value = value

        print(f"Собрано данных для {len(self.test_data)} тестов")
        return self.test_data

    def analyze_decision_mcdc(self, test_suite: TestSuite, simulator) -> Dict[str, Any]:
        """
        Основной метод анализа MC/DC покрытия веток
        """
        print(f"\n{'=' * 60}")
        print("АНАЛИЗ MC/DC ПОКРЫТИЯ ВЕТОК (DO-178C Level A)")
        print(f"{'=' * 60}")

        # Шаг 1: Собрать данные тестов
        self.collect_test_data(test_suite, simulator)

        # Шаг 2: Инициализировать статусы блоков
        self._initialize_block_statuses()

        # Шаг 3: Анализировать MC/DC для каждого блока
        self._analyze_all_blocks()

        # Шаг 4: Рассчитать статистику
        statistics = self._calculate_statistics()

        # Шаг 5: Сгенерировать отчет
        report = self._generate_report()

        return {
            'block_statuses': self.block_statuses,
            'statistics': statistics,
            'report': report,
            'test_data': self.test_data
        }

    def _initialize_block_statuses(self):
        """Инициализировать статусы для всех не-входных блоков"""
        self.block_statuses.clear()

        for block_id, block in self.circuit.blocks.items():
            # Анализируем только логические блоки (не INPUT, не OUTPUT)
            if block.type not in [BlockType.INPUT, BlockType.OUTPUT]:
                # Получаем входные соединения
                input_blocks = []
                for port_connections in block.input_connections:
                    for conn_id in port_connections:
                        conn = self.circuit.connections.get(conn_id)
                        if conn:
                            input_blocks.append(conn.source_id)

                # Создаем статус
                status = BlockMCDC_Status(
                    block_id=block_id,
                    block_name=block.name,
                    block_type=block.type,
                    input_status={input_id: False for input_id in input_blocks},
                    mcdc_pairs={input_id: [] for input_id in input_blocks},
                    all_inputs_covered=False,
                    has_true_branch=False,
                    has_false_branch=False,
                    missing_pairs=[]
                )

                self.block_statuses[block_id] = status

                print(f"Инициализирован блок: {block.name} ({block.type.value})")
                print(f"  Входы: {len(input_blocks)}")

    def _analyze_all_blocks(self):
        """Анализировать MC/DC для всех блоков"""
        print(f"\nАнализ {len(self.block_statuses)} блоков...")

        for block_id, status in self.block_statuses.items():
            print(f"\nАнализ блока: {status.block_name} ({status.block_type.value})")
            self._analyze_block_mcdc(block_id, status)

    def _analyze_block_mcdc(self, block_id: str, status: BlockMCDC_Status):
        """Анализировать MC/DC для конкретного блока"""
        block = self.circuit.blocks.get(block_id)
        if not block:
            return

        # Шаг 1: Собираем входы блока
        input_sources = self._get_block_input_sources(block_id)

        # Шаг 2: Проверяем, были ли оба значения выхода (True/False)
        self._check_branch_values(block_id, status)

        # Шаг 3: Ищем MC/DC пары для каждого входа
        for input_id in input_sources:
            self._find_mcdc_pairs_for_input(block_id, input_id, status)

        # Шаг 4: Определяем общий статус блока
        status.all_inputs_covered = all(status.input_status.values())

        # Шаг 5: Генерируем рекомендации
        self._generate_recommendations(status)

    def _get_block_input_sources(self, block_id: str) -> List[str]:
        """Получить список ID блоков-источников для входов данного блока"""
        block = self.circuit.blocks.get(block_id)
        if not block:
            return []

        input_sources = []

        # Проходим по всем входным соединениям
        for port_connections in block.input_connections:
            for conn_id in port_connections:
                conn = self.circuit.connections.get(conn_id)
                if conn:
                    input_sources.append(conn.source_id)

        return input_sources

    def _check_branch_values(self, block_id: str, status: BlockMCDC_Status):
        """Проверить, были ли оба значения выхода блока (True/False) в тестах"""
        true_found = False
        false_found = False

        for test_data in self.test_data:
            block_value = test_data['block_states'].get(block_id)
            if block_value is True:
                true_found = True
            elif block_value is False:
                false_found = True

            if true_found and false_found:
                break

        status.has_true_branch = true_found
        status.has_false_branch = false_found

        if not true_found:
            status.missing_pairs.append(f"Нет теста, где {status.block_name} = TRUE")
        if not false_found:
            status.missing_pairs.append(f"Нет теста, где {status.block_name} = FALSE")

    def _find_mcdc_pairs_for_input(self, block_id: str, input_id: str, status: BlockMCDC_Status):
        """
        Найти MC/DC пары для конкретного входа блока

        Алгоритм:
        1. Найти все пары тестов (T1, T2), где:
           - Только этот вход изменился
           - Все другие входы блока одинаковы
           - Выход блока изменился
           - Выход схемы изменился
        2. Если найдена хотя бы одна пара - вход покрыт MC/DC
        """
        print(f"  Поиск MC/DC пар для входа {input_id}...")

        # Получаем все входы блока
        all_inputs = self._get_block_input_sources(block_id)

        # Проходим по всем парам тестов
        mcdc_pairs_found = []

        for i in range(len(self.test_data)):
            for j in range(i + 1, len(self.test_data)):
                test1 = self.test_data[i]
                test2 = self.test_data[j]

                # Проверяем критерии MC/DC
                is_mcdc_pair = self._check_mcdc_criteria(
                    block_id, input_id, all_inputs, test1, test2
                )

                if is_mcdc_pair:
                    # Создаем запись о паре
                    pair = MCDC_Pair(
                        test1_index=i,
                        test2_index=j,
                        test1_name=test1['name'],
                        test2_name=test2['name'],
                        changed_input=input_id,
                        block_output_changed=True,
                        circuit_output_changed=True,
                        changed_circuit_outputs=self._get_changed_outputs(test1, test2)
                    )

                    mcdc_pairs_found.append(pair)
                    print(f"    Найдена MC/DC пара: {test1['name']} ↔ {test2['name']}")

        # Обновляем статус
        if mcdc_pairs_found:
            status.input_status[input_id] = True
            status.mcdc_pairs[input_id] = mcdc_pairs_found
            print(f"    Вход {input_id} покрыт MC/DC ({len(mcdc_pairs_found)} пар)")
        else:
            status.input_status[input_id] = False
            status.missing_pairs.append(f"Нет MC/DC пар для входа {input_id}")
            print(f"    Вход {input_id} НЕ покрыт MC/DC")

    def _check_mcdc_criteria(self, block_id: str, target_input: str,
                             all_inputs: List[str], test1: Dict, test2: Dict) -> bool:
        """
        Проверить критерии MC/DC для пары тестов

        Возвращает True если:
        1. Только target_input изменился между тестами
        2. Все другие входы блока одинаковы
        3. Выход блока изменился
        4. Выход схемы изменился
        """
        # 1. Проверяем изменение target_input
        val1 = test1['block_states'].get(target_input)
        val2 = test2['block_states'].get(target_input)

        if val1 is None or val2 is None or val1 == val2:
            return False  # Целевой вход не изменился

        # 2. Проверяем, что все другие входы одинаковы
        for input_id in all_inputs:
            if input_id == target_input:
                continue

            v1 = test1['block_states'].get(input_id)
            v2 = test2['block_states'].get(input_id)

            # Если оба определены и различаются - это не MC/DC пара
            if v1 is not None and v2 is not None and v1 != v2:
                return False

        # 3. Проверяем изменение выхода блока
        block_val1 = test1['block_states'].get(block_id)
        block_val2 = test2['block_states'].get(block_id)

        if block_val1 is None or block_val2 is None or block_val1 == block_val2:
            return False  # Выход блока не изменился

        # 4. Проверяем изменение выхода схемы
        if not self._circuit_outputs_changed(test1, test2):
            return False  # Выход схемы не изменился

        return True

    def _circuit_outputs_changed(self, test1: Dict, test2: Dict) -> bool:
        """Проверить, изменился ли хотя бы один выход схемы"""
        outputs1 = test1['circuit_outputs']
        outputs2 = test2['circuit_outputs']

        # Находим общие выходы
        common_outputs = set(outputs1.keys()) & set(outputs2.keys())

        for output_id in common_outputs:
            val1 = outputs1.get(output_id)
            val2 = outputs2.get(output_id)

            if val1 is not None and val2 is not None and val1 != val2:
                return True

        return False

    def _get_changed_outputs(self, test1: Dict, test2: Dict) -> List[str]:
        """Получить список ID выходов, которые изменились"""
        changed = []
        outputs1 = test1['circuit_outputs']
        outputs2 = test2['circuit_outputs']

        common_outputs = set(outputs1.keys()) & set(outputs2.keys())

        for output_id in common_outputs:
            val1 = outputs1.get(output_id)
            val2 = outputs2.get(output_id)

            if val1 is not None and val2 is not None and val1 != val2:
                # Получаем имя блока
                block = self.circuit.blocks.get(output_id)
                if block:
                    changed.append(block.name)
                else:
                    changed.append(f"ID:{output_id}")

        return changed

    def _generate_recommendations(self, status: BlockMCDC_Status):
        """Сгенерировать рекомендации для блока"""
        recommendations = []

        # Проверяем ветки True/False
        if not status.has_true_branch:
            recommendations.append(f"Добавьте тест, где {status.block_name} = TRUE")
        if not status.has_false_branch:
            recommendations.append(f"Добавьте тест, где {status.block_name} = FALSE")

        # Проверяем непокрытые входы
        for input_id, covered in status.input_status.items():
            if not covered:
                # Пытаемся получить имя входного блока
                input_block = self.circuit.blocks.get(input_id)
                if input_block:
                    input_name = input_block.name
                else:
                    input_name = f"ID:{input_id}"

                recommendations.append(
                    f"Добавьте пару тестов, где меняется только {input_name}, "
                    f"и это меняет выход {status.block_name} и схемы"
                )

        status.missing_pairs.extend(recommendations)

    def _calculate_statistics(self) -> Dict[str, Any]:
        """Рассчитать статистику MC/DC покрытия"""
        total_blocks = len(self.block_statuses)

        # Блоки, соответствующие DO-178C Level A
        level_a_blocks = 0
        # Блоки с полным branch coverage (True и False)
        branch_coverage_blocks = 0
        # Блоки с хотя бы одним MC/DC покрытым входом
        partial_mcdc_blocks = 0

        for status in self.block_statuses.values():
            # Проверяем branch coverage
            if status.has_true_branch and status.has_false_branch:
                branch_coverage_blocks += 1

            # Проверяем наличие хотя бы одного MC/DC покрытого входа
            if any(status.input_status.values()):
                partial_mcdc_blocks += 1

            # Проверяем DO-178C Level A
            if (status.has_true_branch and status.has_false_branch and
                    status.all_inputs_covered):
                level_a_blocks += 1

        statistics = {
            'total_blocks': total_blocks,
            'level_a_blocks': level_a_blocks,
            'level_a_percentage': (level_a_blocks / total_blocks * 100) if total_blocks > 0 else 0,
            'branch_coverage_blocks': branch_coverage_blocks,
            'branch_coverage_percentage': (branch_coverage_blocks / total_blocks * 100) if total_blocks > 0 else 0,
            'partial_mcdc_blocks': partial_mcdc_blocks,
            'partial_mcdc_percentage': (partial_mcdc_blocks / total_blocks * 100) if total_blocks > 0 else 0,
            'non_mcdc_blocks': total_blocks - partial_mcdc_blocks
        }

        return statistics

    def _generate_report(self) -> str:
        """Сгенерировать текстовый отчет"""
        stats = self._calculate_statistics()

        report = [
            "=" * 70,
            "ОТЧЕТ ПО MC/DC ПОКРЫТИЮ ВЕТОК (DO-178C Level A)",
            "=" * 70,
            "",
            f"Всего анализируемых блоков: {stats['total_blocks']}",
            "",
            "СТАТИСТИКА ПОКРЫТИЯ:",
            f"• Соответствует DO-178C Level A: {stats['level_a_blocks']} блоков "
            f"({stats['level_a_percentage']:.1f}%)",
            f"• Branch coverage (True/False): {stats['branch_coverage_blocks']} блоков "
            f"({stats['branch_coverage_percentage']:.1f}%)",
            f"• Частичное MC/DC покрытие: {stats['partial_mcdc_blocks']} блоков "
            f"({stats['partial_mcdc_percentage']:.1f}%)",
            f"• Без MC/DC покрытия: {stats['non_mcdc_blocks']} блоков",
            "",
            "СТАТУС: " + ("СООТВЕТСТВУЕТ DO-178C Level A" if stats['level_a_percentage'] == 100
                          else "НЕ СООТВЕТСТВУЕТ DO-178C Level A"),
            ""
        ]

        # Детали по блокам
        if self.block_statuses:
            report.append("ДЕТАЛИ ПО БЛОКАМ:")
            for block_id, status in self.block_statuses.items():
                # Определяем статус
                if status.all_inputs_covered and status.has_true_branch and status.has_false_branch:
                    block_status = "✓ Level A"
                elif status.has_true_branch and status.has_false_branch:
                    block_status = "✓ Branch"
                elif any(status.input_status.values()):
                    block_status = "~ Partial"
                else:
                    block_status = "✗ None"

                # Считаем покрытые входы
                covered_inputs = sum(1 for covered in status.input_status.values() if covered)
                total_inputs = len(status.input_status)

                report.append(
                    f"  {block_status} {status.block_name} ({status.block_type.value}): "
                    f"MC/DC входов {covered_inputs}/{total_inputs}, "
                    f"ветки: {'T' if status.has_true_branch else '_'}"
                    f"{'F' if status.has_false_branch else '_'}"
                )

        # Непокрытые блоки
        non_level_a_blocks = [
            status for status in self.block_statuses.values()
            if not (status.all_inputs_covered and status.has_true_branch and status.has_false_branch)
        ]

        if non_level_a_blocks:
            report.append("")
            report.append("НЕПОКРЫТЫЕ ДО УРОВНЯ Level A:")
            for status in non_level_a_blocks[:10]:  # Показываем первые 10
                report.append(f"• {status.block_name} ({status.block_type.value}):")

                if not status.has_true_branch:
                    report.append(f"  - Нет теста, где выход = TRUE")
                if not status.has_false_branch:
                    report.append(f"  - Нет теста, где выход = FALSE")

                for input_id, covered in status.input_status.items():
                    if not covered:
                        input_block = self.circuit.blocks.get(input_id)
                        if input_block:
                            report.append(f"  - Вход {input_block.name} не покрыт MC/DC")

                if status.missing_pairs:
                    for rec in status.missing_pairs[:3]:  # Первые 3 рекомендации
                        report.append(f"  - {rec}")

            if len(non_level_a_blocks) > 10:
                report.append(f"  ... и еще {len(non_level_a_blocks) - 10} блоков")

        report.append("")
        report.append("=" * 70)

        return "\n".join(report)

    def get_suggested_tests(self) -> List[Dict]:
        """
        Предложить тесты для улучшения MC/DC покрытия

        Возвращает список предложений в формате:
        {
            'block_id': str,
            'block_name': str,
            'missing_coverage': str,  # Что именно не покрыто
            'suggested_inputs': Dict[str, bool],  # Пример входных значений
            'reason': str  # Объяснение
        }
        """
        suggestions = []

        for block_id, status in self.block_statuses.items():
            block = self.circuit.blocks.get(block_id)
            if not block:
                continue

            # Проверяем отсутствие веток True/False
            if not status.has_true_branch:
                suggestions.append({
                    'block_id': block_id,
                    'block_name': status.block_name,
                    'missing_coverage': 'TRUE ветка',
                    'suggested_inputs': self._suggest_inputs_for_value(block_id, True),
                    'reason': f'Нет теста, где {status.block_name} = TRUE'
                })

            if not status.has_false_branch:
                suggestions.append({
                    'block_id': block_id,
                    'block_name': status.block_name,
                    'missing_coverage': 'FALSE ветка',
                    'suggested_inputs': self._suggest_inputs_for_value(block_id, False),
                    'reason': f'Нет теста, где {status.block_name} = FALSE'
                })

            # Проверяем непокрытые входы
            for input_id, covered in status.input_status.items():
                if not covered:
                    input_block = self.circuit.blocks.get(input_id)
                    if input_block:
                        suggestions.append({
                            'block_id': block_id,
                            'block_name': status.block_name,
                            'missing_coverage': f'MC/DC для входа {input_block.name}',
                            'suggested_inputs': self._suggest_mcdc_pair(block_id, input_id),
                            'reason': f'Нет MC/DC пары для входа {input_block.name} блока {status.block_name}'
                        })

        return suggestions

    def _suggest_inputs_for_value(self, block_id: str, target_value: bool) -> Dict[str, bool]:
        """
        Предложить входные значения для достижения target_value на выходе блока

        Это упрощенная версия - в реальности нужна обратная трассировка
        """
        # Для простоты возвращаем пустой словарь
        # В реальной реализации здесь была бы логика обратной трассировки
        return {}

    def _suggest_mcdc_pair(self, block_id: str, input_id: str) -> Dict[str, bool]:
        """
        Предложить входные значения для MC/DC пары

        Это упрощенная версия - в реальности нужен более сложный анализ
        """
        # Для простоты возвращаем пустой словарь
        return {}