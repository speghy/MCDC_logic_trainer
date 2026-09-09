"""
Анализ покрытия веток с учетом MC/DC
"""
from typing import Dict, List, Set, Tuple, Optional, Any
from logic_trainer.core.block import Circuit, LogicBlock, BlockType
from logic_trainer.core.mcdc_analyzer import MCDCAnalyzer
from logic_trainer.core.decision_mcdc_analyzer import DecisionMCDC_Analyzer
from logic_trainer.core.test_cases import TestSuite, TestCase
from logic_trainer.core.simulator import Simulator


class CoverageAnalyzer:
    """Анализатор покрытия веток с учетом MC/DC"""

    def __init__(self, circuit: Circuit):
        self.circuit = circuit
        self.covered_branches: Set[Tuple[str, bool]] = set()
        self.mcdc_analyzer = MCDCAnalyzer(circuit)
        self.decision_mcdc_analyzer = DecisionMCDC_Analyzer(circuit)
        self.mcdc_results: Optional[Dict] = None
        self.decision_mcdc_results: Optional[Dict] = None
        self.analysis_results: Optional[Dict] = None

    # ========== ОСНОВНЫЕ МЕТОДЫ ДЛЯ ОБРАТНОЙ СОВМЕСТИМОСТИ ==========

    def calculate_current_coverage(self, block_states: Dict[str, Optional[bool]]) -> Set[Tuple[str, bool]]:
        """Рассчитать текущее покрытие на основе состояний блоков"""
        print(f"\n=== calculate_current_coverage() ===")
        coverage = set()

        for block_id, value in block_states.items():
            if value is not None:
                block = self.circuit.blocks.get(block_id)
                if block and block.type != BlockType.INPUT:
                    branch = (block_id, value)
                    coverage.add(branch)
                    print(f"  Добавлена ветка: {block.name} = {value}")

        # Обновляем общее покрытие
        self.covered_branches.update(coverage)

        print(f"Всего покрытых веток: {len(self.covered_branches)}")
        return coverage

    def calculate_total_branches(self) -> int:
        """Рассчитать общее количество веток в схеме"""
        total = 0
        for block in self.circuit.blocks.values():
            # Каждый не-входной блок имеет 2 ветки (True и False)
            if block.type != BlockType.INPUT:
                total += 2
        return total

    def get_coverage_percentage(self) -> float:
        """Получить процент покрытия веток"""
        total = self.calculate_total_branches()
        if total == 0:
            return 0.0
        covered = len(self.covered_branches)
        percentage = (covered / total) * 100
        print(f"get_coverage_percentage(): covered={covered}, total={total}, percentage={percentage:.1f}%")
        return percentage

    def get_covered_branches(self) -> Set[Tuple[str, bool]]:
        """Получить множество покрытых веток"""
        return self.covered_branches.copy()

    def get_uncovered_branches(self) -> List[Dict]:
        """Получить список непокрытых веток"""
        print(f"\n=== get_uncovered_branches() ===")
        uncovered = []

        # Все возможные ветки
        all_possible = set()
        for block in self.circuit.blocks.values():
            if block.type != BlockType.INPUT:
                all_possible.add((block.id, True))
                all_possible.add((block.id, False))

        print(f"Все возможные ветки: {len(all_possible)}")
        print(f"Сейчас покрыто: {len(self.covered_branches)}")

        # Находим непокрытые
        uncovered_set = all_possible - self.covered_branches
        print(f"Непокрыто: {len(uncovered_set)}")

        for block_id, value in uncovered_set:
            block = self.circuit.blocks.get(block_id)
            if block:
                uncovered.append({
                    'block_id': block_id,
                    'block_name': block.name,
                    'block_type': block.type.value,
                    'value': value,
                    'description': f"{block.name}: выход {'TRUE' if value else 'FALSE'} не активирован"
                })

        # Сортируем
        uncovered.sort(key=lambda x: (x['block_type'], x['block_name']))

        print(f"Возвращаем {len(uncovered)} непокрытых веток")
        return uncovered

    def debug_covered_branches(self):
        """Отладочный вывод покрытых веток"""
        print(f"\n{'=' * 50}")
        print("DEBUG: ПОКРЫТЫЕ ВЕТКИ")
        print(f"{'=' * 50}")
        print(f"Всего покрытых веток: {len(self.covered_branches)}")

        for block_id, value in self.covered_branches:
            block = self.circuit.blocks.get(block_id)
            if block:
                print(f"  - {block.name} = {value}")
            else:
                print(f"  - Блок {block_id} не найден!")

        print(f"{'=' * 50}")

    def update_circuit(self, circuit: Circuit):
        """Обновить ссылку на схему"""
        self.circuit = circuit
        self.mcdc_analyzer = MCDCAnalyzer(circuit)
        self.decision_mcdc_analyzer = DecisionMCDC_Analyzer(circuit)
        self.covered_branches.clear()
        self.mcdc_results = None
        self.decision_mcdc_results = None
        self.analysis_results = None

    # ========== МЕТОДЫ ДЛЯ ПОЛНОГО АНАЛИЗА ==========

    def analyze_all(self, test_suite: TestSuite, simulator: Simulator) -> Dict[str, Any]:
        """
        Выполнить полный анализ: MC/DC + Branch Coverage + Decision MC/DC
        """
        print(f"\n{'='*60}")
        print("ПОЛНЫЙ АНАЛИЗ: MC/DC + BRANCH COVERAGE + DECISION MC/DC")
        print(f"{'='*60}")

        # Очищаем предыдущие результаты
        self.covered_branches.clear()
        self.mcdc_results = None
        self.decision_mcdc_results = None
        self.analysis_results = None

        # Шаг 1: Выполняем MC/DC анализ для входов
        print("\n1. ВЫПОЛНЕНИЕ MC/DC АНАЛИЗА ДЛЯ ВХОДОВ...")
        mcdc_results = self.mcdc_analyzer.analyze(test_suite)
        self.mcdc_results = mcdc_results

        mcdc_stats = mcdc_results['statistics']
        print(f"   MC/DC покрытие входов: {mcdc_stats['coverage_percentage']:.1f}%")
        print(f"   Покрыто входов: {mcdc_stats['covered_inputs']}/{mcdc_stats['total_inputs']}")

        # Шаг 2: Выполняем Decision MC/DC анализ для веток
        print("\n2. ВЫПОЛНЕНИЕ DECISION MC/DC АНАЛИЗА (DO-178C Level A)...")
        try:
            decision_mcdc_results = self.decision_mcdc_analyzer.analyze_decision_mcdc(
                test_suite, simulator
            )
            self.decision_mcdc_results = decision_mcdc_results

            if decision_mcdc_results and 'statistics' in decision_mcdc_results:
                stats = decision_mcdc_results['statistics']
                print(f"   DO-178C Level A покрытие: {stats['level_a_percentage']:.1f}%")
                print(f"   Branch coverage: {stats['branch_coverage_percentage']:.1f}%")
                print(f"   Анализировано блоков: {stats['total_blocks']}")
            else:
                print("   Decision MC/DC анализ не вернул результаты")
        except Exception as e:
            print(f"   Ошибка при Decision MC/DC анализе: {e}")
            import traceback
            traceback.print_exc()
            self.decision_mcdc_results = None

        # Шаг 3: Анализируем branch coverage для влияющих блоков
        print("\n3. АНАЛИЗ BRANCH COVERAGE...")
        influential_blocks = self._get_influential_blocks()
        branch_results = self._analyze_branch_coverage(
            test_suite, simulator, influential_blocks
        )

        # Шаг 4: Рассчитываем объединенную статистику
        print("\n4. РАСЧЕТ ОБЪЕДИНЕННОЙ СТАТИСТИКИ...")
        combined_stats = self._calculate_combined_statistics(
            mcdc_results, branch_results, self.decision_mcdc_results
        )

        # Сохраняем результаты
        self.analysis_results = {
            'mcdc': mcdc_results,
            'decision_mcdc': self.decision_mcdc_results,
            'branch_coverage': branch_results,
            'combined': combined_stats,
            'influential_blocks': list(influential_blocks.keys())
        }

        print(f"\n{'='*60}")
        print("АНАЛИЗ ЗАВЕРШЕН")
        print(f"{'='*60}")

        return self.analysis_results

    def _get_influential_blocks(self) -> Dict[str, LogicBlock]:
        """Получить блоки, которые влияют на выходы (по MC/DC)"""
        influential = {}

        if not self.mcdc_results:
            return influential

        # 1. Все входные блоки с MC/DC покрытием
        for input_id, data in self.mcdc_results['per_input'].items():
            if data.get('covered', False):
                # Входной блок влияет
                block = self.circuit.blocks.get(input_id)
                if block:
                    influential[block.id] = block

                # 2. Находим путь от этого входа к выходам
                path_blocks = self._find_path_to_outputs(input_id)
                for block_id in path_blocks:
                    block = self.circuit.blocks.get(block_id)
                    if block:
                        influential[block_id] = block

        # 3. Также добавляем все выходные блоки
        for block_id, block in self.circuit.blocks.items():
            if block.type == BlockType.OUTPUT:
                influential[block_id] = block

        return influential

    def _find_path_to_outputs(self, start_block_id: str) -> List[str]:
        """Найти все блоки на пути от start_block_id к выходам"""
        visited = set()
        path_blocks = []

        def dfs(current_id: str):
            if current_id in visited:
                return
            visited.add(current_id)

            block = self.circuit.blocks.get(current_id)
            if not block:
                return

            # Если это выходной блок - добавляем в путь
            if block.type == BlockType.OUTPUT:
                path_blocks.append(current_id)
                return

            # Идем по всем выходным соединениям
            for conn_id in block.output_connections:
                conn = self.circuit.connections.get(conn_id)
                if conn:
                    # Добавляем текущий блок в путь
                    if current_id not in path_blocks:
                        path_blocks.append(current_id)
                    dfs(conn.target_id)

        dfs(start_block_id)
        return path_blocks

    def _analyze_branch_coverage(self, test_suite: TestSuite,
                                 simulator: Simulator,
                                 influential_blocks: Dict[str, LogicBlock]) -> Dict:
        """Анализировать branch coverage для влияющих блоков"""

        print(f"   Анализ {len(test_suite.test_cases)} тестовых случаев...")

        # Сохраняем исходное состояние схемы
        original_states = {}
        for block_id, block in self.circuit.blocks.items():
            original_states[block_id] = block.value

        total_influential_branches = 0
        covered_influential_branches = set()

        # Для каждого влияющего не-входного блока считаем 2 ветки
        for block_id, block in influential_blocks.items():
            if block.type != BlockType.INPUT:
                total_influential_branches += 2

        print(f"   Всего важных веток: {total_influential_branches}")

        # Запускаем каждый тест и собираем покрытие
        for i, test_case in enumerate(test_suite.test_cases):
            print(f"   Тест {i+1}: '{test_case.name}'...", end=" ")

            # Сбрасываем симулятор
            simulator.reset()

            # Устанавливаем значения входов
            for block_id, value in test_case.inputs.items():
                block = self.circuit.blocks.get(block_id)
                if block and block.type == BlockType.INPUT:
                    block.value = value

            # Запускаем симуляцию
            simulator.active_frontier.clear()
            for block_id, block in self.circuit.blocks.items():
                if block.type == BlockType.INPUT and block.value is not None:
                    simulator.active_frontier.add(block_id)

            # Выполняем до завершения
            max_steps = 50
            for _ in range(max_steps):
                if not simulator.active_frontier:
                    break
                simulator.simulate_step()

            # Собираем покрытие для влияющих блоков
            for block_id, block in influential_blocks.items():
                if block.type != BlockType.INPUT and block.value is not None:
                    branch = (block_id, block.value)
                    if branch not in covered_influential_branches:
                        covered_influential_branches.add(branch)

            print(f"покрыто {len(covered_influential_branches)} веток")

        # Восстанавливаем исходное состояние
        simulator.reset()
        for block_id, value in original_states.items():
            block = self.circuit.blocks.get(block_id)
            if block:
                block.value = value

        # Рассчитываем статистику
        covered_count = len(covered_influential_branches)
        coverage_percentage = (covered_count / total_influential_branches * 100) if total_influential_branches > 0 else 0

        # Детали по блокам
        block_details = []
        for block_id, block in influential_blocks.items():
            if block.type != BlockType.INPUT:
                covered_true = (block_id, True) in covered_influential_branches
                covered_false = (block_id, False) in covered_influential_branches

                status = "FULL" if covered_true and covered_false else \
                         "PARTIAL" if covered_true or covered_false else "NONE"

                block_details.append({
                    'block_id': block_id,
                    'block_name': block.name,
                    'block_type': block.type.value,
                    'covered_true': covered_true,
                    'covered_false': covered_false,
                    'status': status
                })

        return {
            'total_branches': total_influential_branches,
            'covered_branches': covered_count,
            'coverage_percentage': coverage_percentage,
            'block_details': block_details,
            'covered_branches_list': list(covered_influential_branches)
        }

    def _calculate_combined_statistics(self, mcdc_results: Dict,
                                       branch_results: Dict,
                                       decision_mcdc_results: Optional[Dict]) -> Dict:
        """Рассчитать объединенную статистику"""

        # Средневзвешенная оценка
        mcdc_percentage = mcdc_results['statistics']['coverage_percentage']
        branch_percentage = branch_results['coverage_percentage']

        # Если есть Decision MC/DC результаты, используем их
        if decision_mcdc_results and 'statistics' in decision_mcdc_results:
            decision_percentage = decision_mcdc_results['statistics']['level_a_percentage']
            # Веса: 40% MC/DC входов, 40% Decision MC/DC, 20% Branch Coverage
            mcdc_weight = 0.4
            decision_weight = 0.4
            branch_weight = 0.2
            combined_percentage = (mcdc_percentage * mcdc_weight +
                                  decision_percentage * decision_weight +
                                  branch_percentage * branch_weight)
        else:
            # Без Decision MC/DC: 60% MC/DC входов, 40% Branch Coverage
            mcdc_weight = 0.6
            branch_weight = 0.4
            combined_percentage = (mcdc_percentage * mcdc_weight +
                                  branch_percentage * branch_weight)

        # Оценка качества тестов
        quality = "ОТЛИЧНО"
        if combined_percentage >= 90:
            quality = "ОТЛИЧНО"
        elif combined_percentage >= 70:
            quality = "ХОРОШО"
        elif combined_percentage >= 50:
            quality = "УДОВЛЕТВОРИТЕЛЬНО"
        else:
            quality = "НЕДОСТАТОЧНО"

        # Непокрытые важные ветки
        uncovered_branches = []
        if 'block_details' in branch_results:
            for block_detail in branch_results['block_details']:
                if block_detail.get('status') != 'FULL':
                    block_name = block_detail['block_name']

                    if not block_detail.get('covered_true', False):
                        uncovered_branches.append(f"{block_name}: TRUE не покрыт")
                    if not block_detail.get('covered_false', False):
                        uncovered_branches.append(f"{block_name}: FALSE не покрыт")

        return {
            'combined_percentage': combined_percentage,
            'quality': quality,
            'mcdc_weight': mcdc_weight,
            'branch_weight': branch_weight,
            'uncovered_branches': uncovered_branches[:10],  # Первые 10
            'total_uncovered': len(uncovered_branches),
            'recommendations': self._generate_recommendations(
                mcdc_results, branch_results, decision_mcdc_results
            )
        }

    def _generate_recommendations(self, mcdc_results: Dict,
                                  branch_results: Dict,
                                  decision_mcdc_results: Optional[Dict]) -> List[str]:
        """Сгенерировать рекомендации по улучшению покрытия"""
        recommendations = []

        # Рекомендации по MC/DC
        mcdc_stats = mcdc_results['statistics']
        if mcdc_stats['coverage_percentage'] < 100:
            uncovered_inputs = [d for d in mcdc_stats.get('input_details', [])
                              if not d.get('covered', True)]
            if uncovered_inputs:
                input_names = [d.get('name', f"ID:{d.get('id', 'unknown')}")
                             for d in uncovered_inputs[:3]]
                recommendations.append(
                    f"Добавьте тесты для входов: {', '.join(input_names)}"
                )
                recommendations.append(
                    "Для MC/DC нужны пары тестов, отличающиеся только одним входом"
                )

        # Рекомендации по Branch Coverage
        if branch_results['coverage_percentage'] < 100:
            partial_blocks = [d for d in branch_results.get('block_details', [])
                            if d.get('status') == 'PARTIAL']
            if partial_blocks:
                for block in partial_blocks[:3]:  # Первые 3
                    block_name = block.get('block_name', 'Unknown')
                    if not block.get('covered_true', False):
                        recommendations.append(f"Добавьте тест где {block_name} = TRUE")
                    if not block.get('covered_false', False):
                        recommendations.append(f"Добавьте тест где {block_name} = FALSE")

        # Рекомендации по Decision MC/DC (DO-178C Level A)
        if decision_mcdc_results and 'statistics' in decision_mcdc_results:
            stats = decision_mcdc_results['statistics']
            if stats['level_a_percentage'] < 100:
                recommendations.append(f"Только {stats['level_a_percentage']:.1f}% блоков соответствуют DO-178C Level A")
                recommendations.append("Для Level A каждый вход каждого блока должен иметь MC/DC пару")

        # Общие рекомендации
        if not recommendations:
            recommendations.append("Отличное покрытие! Тесты полностью покрывают важные ветки схемы.")

        return recommendations

    def get_combined_report(self) -> str:
        """Получить объединенный отчет"""
        if not self.analysis_results:
            return "Анализ не выполнен"

        results = self.analysis_results
        mcdc = results['mcdc']
        branch = results['branch_coverage']
        decision_mcdc = results['decision_mcdc']
        combined = results['combined']

        report = [
            "=" * 60,
            "ОБЪЕДИНЕННЫЙ ОТЧЕТ: MC/DC + BRANCH COVERAGE + DECISION MC/DC",
            "=" * 60,
            "",
            "1. MC/DC ПОКРЫТИЕ ВХОДОВ:",
            f"   • Покрыто входов: {mcdc['statistics']['covered_inputs']}/{mcdc['statistics']['total_inputs']}",
            f"   • Процент MC/DC: {mcdc['statistics']['coverage_percentage']:.1f}%",
        ]

        # Добавляем Decision MC/DC если есть
        if decision_mcdc and 'statistics' in decision_mcdc:
            stats = decision_mcdc['statistics']
            report.append("")
            report.append("2. DECISION MC/DC (DO-178C Level A):")
            report.append(f"   • Анализировано блоков: {stats['total_blocks']}")
            report.append(f"   • Соответствует Level A: {stats['level_a_percentage']:.1f}%")
            report.append(f"   • Branch coverage: {stats['branch_coverage_percentage']:.1f}%")

        report.append("")
        report.append("3. BRANCH COVERAGE (важные ветки):")
        report.append(f"   • Покрыто веток: {branch['covered_branches']}/{branch['total_branches']}")
        report.append(f"   • Процент покрытия: {branch['coverage_percentage']:.1f}%")

        report.append("")
        report.append("4. ОБЩАЯ ОЦЕНКА:")
        report.append(f"   • Общий процент: {combined['combined_percentage']:.1f}%")
        report.append(f"   • Качество тестов: {combined['quality']}")

        # Рекомендации
        if combined.get('recommendations'):
            report.append("")
            report.append("5. РЕКОМЕНДАЦИИ:")
            for i, rec in enumerate(combined['recommendations'], 1):
                report.append(f"   {i}. {rec}")

        # Непокрытые ветки
        if combined.get('uncovered_branches'):
            report.append("")
            report.append("6. НЕПОКРЫТЫЕ ВАЖНЫЕ ВЕТКИ:")
            for i, branch_desc in enumerate(combined['uncovered_branches'][:5], 1):
                report.append(f"   {i}. {branch_desc}")
            if combined.get('total_uncovered', 0) > 5:
                report.append(f"   ... и еще {combined['total_uncovered'] - 5} веток")

        report.append("")
        report.append("=" * 60)

        return "\n".join(report)

    # ========== МЕТОДЫ ДЛЯ DO-178C ==========

    def get_decision_mcdc_report(self) -> str:
        """Получить отчет по Decision MC/DC анализу"""
        if self.decision_mcdc_results:
            return self.decision_mcdc_results.get('report', 'Отчет не доступен')
        return "Decision MC/DC анализ не выполнен"

    def get_level_a_status(self) -> Dict[str, any]:
        """Получить статус соответствия DO-178C Level A"""
        if not self.decision_mcdc_results:
            return {'compliant': False, 'percentage': 0, 'message': 'Анализ не выполнен'}

        stats = self.decision_mcdc_results.get('statistics', {})
        level_a_percentage = stats.get('level_a_percentage', 0)
        compliant = level_a_percentage == 100

        return {
            'compliant': compliant,
            'percentage': level_a_percentage,
            'blocks_total': stats.get('total_blocks', 0),
            'blocks_level_a': stats.get('level_a_blocks', 0),
            'message': 'Соответствует DO-178C Level A' if compliant else 'Не соответствует DO-178C Level A'
        }

    def run_level_a_analysis(self, test_suite: TestSuite, simulator: Simulator) -> Dict:
        """Запустить анализ DO-178C Level A"""
        print(f"\n{'='*60}")
        print("ЗАПУСК АНАЛИЗА DO-178C Level A")
        print(f"{'='*60}")

        if not self.decision_mcdc_analyzer:
            self.decision_mcdc_analyzer = DecisionMCDC_Analyzer(self.circuit)

        results = self.decision_mcdc_analyzer.analyze_decision_mcdc(test_suite, simulator)
        self.decision_mcdc_results = results
        # print("DEBUGEN TOTALEN")
        # print(self.decision_mcdc_results)
        return results