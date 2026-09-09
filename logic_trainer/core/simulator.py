"""
Симулятор логических схем с пошаговой и непрерывной симуляцией
"""
from typing import Dict, List, Set, Tuple, Optional
from logic_trainer.core.block import Circuit, BlockType, LogicBlock, Connection


class Simulator:
    """Симулятор распространения сигналов"""

    def __init__(self, circuit: Circuit):
        self.circuit = circuit
        self.history: List[Dict[str, bool]] = []
        self.coverage: Set[Tuple[str, bool]] = set()
        self.step_delay = 500

        # Состояние для пошаговой симуляции
        self.current_step = 0
        self.active_frontier: Set[str] = set()  # Фронт распространения
        self.processed_blocks: Set[str] = set()  # Обработанные на текущем шаге
        self.is_continuous = False  # Режим непрерывной симуляции
        self.test_suite = None
        self.is_test_mode = False

    def set_test_suite(self, test_suite):
        """Установить набор тестовых случаев"""
        self.test_suite = test_suite

    def run_current_test(self):
        """Запустить текущий тестовый случай"""
        if not self.test_suite:
            return {}

        case = self.test_suite.get_current_case()
        if not case:
            return {}

        self.is_test_mode = True

        # Применяем тестовый случай
        self.test_suite.apply_current_case()

        # Запускаем непрерывную симуляцию
        self.active_frontier.clear()
        for block_id, block in self.circuit.blocks.items():
            if block.type == BlockType.INPUT and block.value is not None:
                self.active_frontier.add(block_id)

        # Выполняем до завершения
        max_steps = 50
        for _ in range(max_steps):
            if not self.active_frontier:
                break
            self.simulate_step()

        # Проверяем результаты
        results = self.test_suite.check_results(self)

        self.is_test_mode = False
        return results

    def set_input_value(self, block_id: str, value: bool):
        """Установить значение входного блока"""
        if block_id in self.circuit.blocks:
            block = self.circuit.blocks[block_id]
            if block.type == BlockType.INPUT:
                block.value = value
                # Добавляем в активные для пошаговой симуляции
                self.active_frontier.add(block_id)

    def _propagate_from_block(self, block_id: str) -> Set[str]:
        """Распространить сигнал от одного блока к его непосредственным получателям"""
        changed_blocks = set()
        block = self.circuit.blocks.get(block_id)

        if not block:
            return changed_blocks

        print(f"  Processing {block.name} ({block.type.value})")
        print(f"    Output connections: {block.output_connections}")

        # Получаем значение блока
        if block.type == BlockType.INPUT:
            current_value = block.value
        else:
            old_value = block.value
            current_value = block.compute()

            if old_value != current_value:
                block.value = current_value
                changed_blocks.add(block_id)
                print(f"    Value changed: {old_value} → {current_value}")

        # Если есть значение - передаем его ВСЕМ получателям
        if current_value is not None:
            print(f"    Has {len(block.output_connections)} output connections")

            for i, conn_id in enumerate(block.output_connections):
                print(f"    Connection {i}: {conn_id}")
                conn = self.circuit.connections.get(conn_id)

                if conn:
                    target_block = self.circuit.blocks.get(conn.target_id)
                    if target_block:
                        print(f"      → Target: {target_block.name} (port {conn.target_port})")

                        # Находим индекс соединения в порту
                        target_port = conn.target_port
                        if target_port < len(target_block.input_connections):
                            try:
                                connection_index = target_block.input_connections[target_port].index(conn_id)
                                target_block.set_input_value(target_port, connection_index, current_value)

                                print(
                                    f"      → {target_block.name}.port[{target_port}].conn[{connection_index}] = {current_value}")

                                # Добавляем получателя в активные для следующего шага
                                self.active_frontier.add(conn.target_id)
                                print(f"      → Added to frontier: {target_block.name}")

                            except ValueError:
                                print(f"      WARNING: Connection {conn_id} not found in port {target_port}!")
                        else:
                            print(f"      ERROR: Target port {target_port} out of range!")
                    else:
                        print(f"      ERROR: Target block {conn.target_id} not found!")
                else:
                    print(f"      ERROR: Connection {conn_id} not found in circuit!")

        self.processed_blocks.add(block_id)
        return changed_blocks

    def simulate_step(self) -> Set[str]:
        """Выполнить ОДИН шаг симуляции - продвинуть фронт на один уровень"""
        print(f"\n{'='*60}")
        print(f"ШАГ {self.current_step}")

        if not self.active_frontier:
            # Если фронт пуст, начинаем с INPUT блоков со значениями
            for block_id, block in self.circuit.blocks.items():
                if block.type == BlockType.INPUT and block.value is not None:
                    self.active_frontier.add(block_id)
            print(f"Начинаем с INPUT блоков: {self.active_frontier}")

        changed_blocks = set()
        blocks_to_process = set(self.active_frontier)
        self.active_frontier.clear()
        self.processed_blocks.clear()

        print(f"Обрабатываем блоки: {[self.circuit.blocks[b].name for b in blocks_to_process]}")

        # Обрабатываем все блоки в текущем фронте
        for block_id in blocks_to_process:
            changed = self._propagate_from_block(block_id)
            changed_blocks.update(changed)

        # Сохраняем историю
        current_state = {
            block_id: block.value
            for block_id, block in self.circuit.blocks.items()
            if block.value is not None
        }
        self.history.append(current_state)

        # Обновляем покрытие
        for block_id, value in current_state.items():
            self.coverage.add((block_id, value))

        print(f"Измененные блоки: {changed_blocks}")
        print(f"Новый фронт: {self.active_frontier}")
        print(f"Всего обработано: {len(self.processed_blocks)} блоков")

        self.current_step += 1
        return changed_blocks

    def simulate_continuous(self) -> Set[str]:
        """Непрерывная симуляция - выполняется до стабилизации"""
        print(f"\n{'='*60}")
        print(f"НЕПРЕРЫВНАЯ СИМУЛЯЦИЯ")

        all_changed = set()
        max_steps = 100  # Защита от бесконечного цикла
        step_count = 0

        self.is_continuous = True

        while self.active_frontier and step_count < max_steps:
            print(f"\nЦикл {step_count + 1}")
            changed = self.simulate_step()
            all_changed.update(changed)
            step_count += 1

            if not changed:
                print("Схема стабилизировалась")
                break

        self.is_continuous = False

        if step_count >= max_steps:
            print(f"Достигнут максимум шагов ({max_steps})")

        print(f"Всего шагов: {step_count}")
        print(f"Всего изменений: {len(all_changed)}")

        return all_changed

    def reset(self):
        """Полный сброс симуляции"""
        for block in self.circuit.blocks.values():
            block.value = None
            block.input_values = [None] * len(block.input_connections)

        self.history.clear()
        self.coverage.clear()
        self.current_step = 0
        self.active_frontier.clear()
        self.processed_blocks.clear()
        self.is_continuous = False

    def get_block_state(self) -> Dict[str, Optional[bool]]:
        """Текущее состояние всех блоков"""
        return {
            block_id: block.value
            for block_id, block in self.circuit.blocks.items()
        }

    def visualize_propagation(self, block_id: str) -> List[Tuple[str, str]]:
        """Визуализировать путь распространения сигнала"""
        path = []
        visited = set()

        def trace(current_id: str):
            if current_id in visited:
                return
            visited.add(current_id)

            block = self.circuit.blocks.get(current_id)
            if not block:
                return

            path.append((current_id, "active"))

            for conn_id in block.output_connections:
                conn = self.circuit.connections.get(conn_id)
                if conn:
                    path.append((conn_id, "connection"))
                    trace(conn.target_id)

        trace(block_id)
        return path