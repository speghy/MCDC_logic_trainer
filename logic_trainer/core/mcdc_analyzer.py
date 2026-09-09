"""
Анализатор MC/DC покрытия
"""
from typing import Dict, List, Tuple, Optional, Set
from logic_trainer.core.test_cases import TestSuite, TestCase
from logic_trainer.core.block import Circuit, BlockType, LogicBlock


class MCDCAnalyzer:
    """Анализатор MC/DC покрытия"""

    def __init__(self, circuit: Circuit):
        self.circuit = circuit
        self.results: Dict[str, Dict] = {}

    def analyze(self, test_suite: TestSuite) -> Dict:
        """
        Проанализировать MC/DC покрытие на основе тестовых случаев

        Алгоритм:
        1. Для каждого входного блока найти все пары тестов, отличающиеся только этим входом
        2. Если найдена хотя бы одна пара с разными выходами - вход покрыт MC/DC
        3. Рассчитать процент входов с MC/DC покрытием
        """

        # Получаем все входные блоки
        input_blocks = self._get_input_blocks()

        # Собираем все тестовые случаи с результатами
        test_cases = test_suite.test_cases

        # Инициализируем результаты
        for input_id, input_block in input_blocks.items():
            self.results[input_id] = {
                'block_name': input_block.name,
                'covered': False,
                'pairs': [],  # Пары тестов демонстрирующие влияние
                'test_pair_details': [],  # Детали пар тестов для UI
                'influences_outputs': set(),  # На какие выходы влияет
                'note': ''
            }

        # Проходим по всем парам тестовых случаев
        print(f"\n=== MC/DC АНАЛИЗ ===")
        print(f"Всего тестовых случаев: {len(test_cases)}")
        print(f"Всего входных блоков: {len(input_blocks)}")

        for i in range(len(test_cases)):
            for j in range(i + 1, len(test_cases)):
                test1 = test_cases[i]
                test2 = test_cases[j]

                # ПРОВЕРЯЕМ что отличаются ТОЛЬКО одним входом
                differs, diff_input_id = self._inputs_differ_by_one_only(
                    test1.inputs, test2.inputs
                )

                if not differs:
                    continue  # Пропускаем если отличается больше чем 1 вход

                # Проверяем изменение выходов ЭТОГО КОНКРЕТНОГО ТЕСТА
                changed_outputs = self._find_changed_outputs(
                    test1.expected_outputs,
                    test2.expected_outputs
                )

                # Если выходы изменились
                if changed_outputs:
                    input_id = diff_input_id  # Это тот самый единственный различающийся вход

                    if not self.results[input_id]['covered']:
                        self.results[input_id]['covered'] = True

                    # Преобразуем ID выходов в имена
                    output_names = self._output_ids_to_names(changed_outputs)

                    # Сохраняем пару тестов
                    pair_info = {
                        'test1_index': i,
                        'test1_name': test1.name,
                        'test2_index': j,
                        'test2_name': test2.name,
                        'changed_outputs': list(changed_outputs),
                        'changed_output_names': output_names
                    }
                    self.results[input_id]['pairs'].append(pair_info)

                    # Детали для UI - с именами выходов
                    self.results[input_id]['test_pair_details'].append({
                        'pair': f"'{test1.name}' ↔ '{test2.name}'",
                        'test1': f"'{test1.name}' (тест {i+1})",
                        'test2': f"'{test2.name}' (тест {j+1})",
                        'outputs': ", ".join(output_names)
                    })

                    self.results[input_id]['influences_outputs'].update(changed_outputs)

                    print(f"  Найдена MC/DC пара для {input_blocks[input_id].name}:")
                    print(f"    Тест '{test1.name}' ↔ '{test2.name}'")
                    print(f"    Изменились выходы: {output_names}")

        # Рассчитываем статистику
        stats = self._calculate_statistics(input_blocks)

        return {
            'per_input': self.results,
            'statistics': stats
        }

    def _get_input_blocks(self) -> Dict[str, LogicBlock]:
        """Получить все входные блоки схемы"""
        input_blocks = {}

        for block_id, block in self.circuit.blocks.items():
            if block.type == BlockType.INPUT:
                input_blocks[block_id] = block

        return input_blocks

    def _get_output_blocks(self) -> Dict[str, LogicBlock]:
        """Получить все выходные блоки схемы"""
        output_blocks = {}
        for block_id, block in self.circuit.blocks.items():
            if block.type == BlockType.OUTPUT:
                output_blocks[block_id] = block
        return output_blocks

    def _output_ids_to_names(self, output_ids: Set[str]) -> List[str]:
        """Преобразовать ID выходов в имена"""
        output_names = []
        for output_id in output_ids:
            block = self.circuit.blocks.get(output_id)
            if block:
                output_names.append(block.name)
            else:
                output_names.append(f"ID:{output_id}")
        return output_names

    def _inputs_differ_by_one_only(self, inputs1: Dict[str, bool],
                                   inputs2: Dict[str, bool]) -> Tuple[bool, Optional[str]]:
        """
        Проверить что входы отличаются только одним значением

        Возвращает: (отличается_ли_только_один, id_различающегося_входа)
        """
        diff = []
        all_inputs = set(inputs1.keys()) | set(inputs2.keys())

        for input_id in all_inputs:
            val1 = inputs1.get(input_id)
            val2 = inputs2.get(input_id)

            # Если оба значения определены и отличаются
            if val1 is not None and val2 is not None and val1 != val2:
                diff.append(input_id)
            # Если одно значение отсутствует (тоже считается различием)
            elif (val1 is None) != (val2 is None):
                diff.append(input_id)

        if len(diff) == 1:
            return True, diff[0]
        else:
            return False, None

    def _find_changed_outputs(self, outputs1: Dict[str, bool],
                              outputs2: Dict[str, bool]) -> Set[str]:
        """Найти выходы с разными значениями в двух тестах"""
        changed = set()

        # Находим общие выходы (те что есть в ОБОИХ тестах)
        common_outputs = set(outputs1.keys()) & set(outputs2.keys())

        for output_id in common_outputs:
            val1 = outputs1[output_id]
            val2 = outputs2[output_id]

            # Если значения определены и отличаются
            if val1 is not None and val2 is not None and val1 != val2:
                changed.add(output_id)

        return changed

    def _calculate_statistics(self, input_blocks: Dict) -> Dict:
        """Рассчитать статистику MC/DC покрытия"""
        total_inputs = len(input_blocks)
        covered_inputs = sum(1 for data in self.results.values() if data['covered'])

        coverage_percentage = (covered_inputs / total_inputs * 100) if total_inputs > 0 else 0

        # Для каждого входа подсчитываем количество доказанных влияний
        input_details = []
        for input_id, data in self.results.items():
            block_name = input_blocks[input_id].name if input_id in input_blocks else input_id

            # Преобразуем ID выходов в имена
            output_ids = data['influences_outputs']
            output_names = self._output_ids_to_names(output_ids)

            input_details.append({
                'id': input_id,
                'name': block_name,
                'covered': data['covered'],
                'pair_count': len(data['pairs']),
                'test_pair_details': data.get('test_pair_details', []),
                'influences_outputs': output_names
            })

        return {
            'total_inputs': total_inputs,
            'covered_inputs': covered_inputs,
            'coverage_percentage': coverage_percentage,
            'input_details': input_details
        }

    def get_mcdc_report(self) -> str:
        """Получить текстовый отчет о MC/DC покрытии"""
        if not self.results:
            return "MC/DC анализ не выполнен"

        stats = self._calculate_statistics(self._get_input_blocks())

        report = [
            "=" * 50,
            "ОТЧЕТ О MC/DC ПОКРЫТИИ",
            "=" * 50,
            f"Всего входов: {stats['total_inputs']}",
            f"Входов с MC/DC покрытием: {stats['covered_inputs']}",
            f"Процент MC/DC покрытия: {stats['coverage_percentage']:.1f}%",
            ""
        ]

        # Детали по каждому входу
        report.append("ДЕТАЛИ ПО ВХОДАМ:")
        for detail in stats['input_details']:
            status = "✓" if detail['covered'] else "✗"
            output_names = ", ".join(detail['influences_outputs']) if detail['influences_outputs'] else "нет данных"

            # Добавляем пары тестов если есть
            pair_info = ""
            if detail['test_pair_details']:
                pairs = detail['test_pair_details'][:2]  # Показываем первые 2 пары
                pair_info = " (" + "; ".join([p['pair'] for p in pairs]) + ")"
                if len(detail['test_pair_details']) > 2:
                    pair_info += f" ... и ещё {len(detail['test_pair_details']) - 2} пар"

            report.append(f"  {status} {detail['name']}: "
                          f"{detail['pair_count']} пар{pair_info}, "
                          f"влияет на выходы: {output_names}")

        # Непокрытые входы
        uncovered = [d for d in stats['input_details'] if not d['covered']]
        if uncovered:
            report.append("")
            report.append("НЕПОКРЫТЫЕ MC/DC ВХОДЫ:")
            for detail in uncovered:
                report.append(f"  • {detail['name']}")

        # Рекомендации
        report.append("")
        report.append("РЕКОМЕНДАЦИИ:")
        if stats['coverage_percentage'] < 100:
            report.append("  • Добавьте тестовые случаи, отличающиеся только одним входом")
            report.append("  • Убедитесь что изменение входа приводит к изменению выхода")
        else:
            report.append("  • Отличное MC/DC покрытие!")

        return "\n".join(report)

    def suggest_missing_tests(self, test_suite: TestSuite) -> List[Dict]:
        """
        Предложить недостающие тесты для улучшения MC/DC покрытия

        Для каждого непокрытого входа:
        1. Найти существующий тест
        2. Создать его копию с измененным значением этого входа
        3. Проверить изменится ли выход
        """
        suggestions = []

        # Проверяем что есть тестовые случаи
        if not test_suite or not test_suite.test_cases:
            print("  No test cases available for suggestions")
            return suggestions

        # Получаем входные блоки
        input_blocks = self._get_input_blocks()

        print(f"\n=== SUGGEST MISSING TESTS ===")
        print(f"Input blocks: {len(input_blocks)}")
        print(f"Test cases: {len(test_suite.test_cases)}")
        print(f"Results items: {len(self.results)}")

        for input_id, data in self.results.items():
            if not data.get('covered', False):
                # Берем первый тест как основу
                base_test = test_suite.test_cases[0]

                # Создаем новый тест с измененным входом
                new_inputs = base_test.inputs.copy()

                if input_id in new_inputs:
                    new_inputs[input_id] = not new_inputs[input_id]
                    change_type = "инвертировать"
                else:
                    new_inputs[input_id] = True
                    change_type = "установить в True"

                # Получаем имя входного блока
                input_block = input_blocks.get(input_id)
                if input_block:
                    input_name = input_block.name
                else:
                    input_name = f"ID:{input_id}"

                suggestion = {
                    'for_input': input_id,
                    'input_name': input_name,
                    'base_test': base_test.name,
                    'suggested_inputs': new_inputs,
                    'change_type': change_type,
                    'reason': f"Для демонстрации влияния входа '{input_name}' ({change_type})"
                }

                suggestions.append(suggestion)

        return suggestions