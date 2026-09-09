"""
Логические блоки и соединения
"""
from enum import Enum
from dataclasses import dataclass
from typing import List, Optional, Dict, Tuple
import uuid


class BlockType(Enum):
    INPUT = "INPUT"
    OUTPUT = "OUTPUT"
    AND = "AND"
    OR = "OR"
    NOT = "NOT"
    XOR = "XOR"
    NAND = "NAND"
    NOR = "NOR"


@dataclass
class Connection:
    """Соединение между блоками"""
    id: str
    source_id: str
    target_id: str
    target_port: int = 0

    def __post_init__(self):
        if not self.id:
            self.id = str(uuid.uuid4())[:8]


class LogicBlock:
    """Один логический блок (AND, OR, INPUT и т.д.)"""

    def __init__(self, block_type: BlockType, name: str = None):
        self.id = str(uuid.uuid4())[:8]
        self.type = block_type

        # Используем русские названия
        type_names = {
            BlockType.INPUT: "Вход",
            BlockType.OUTPUT: "Выход",
            BlockType.AND: "И",
            BlockType.OR: "ИЛИ",
            BlockType.NOT: "НЕ",
            BlockType.XOR: "ИсклИЛИ",
            BlockType.NAND: "И-НЕ",
            BlockType.NOR: "ИЛИ-НЕ"
        }

        base_name = type_names.get(block_type, block_type.value)
        if name:
            self.name = name
        else:
            # Счетчик для каждого типа - гарантируем инициализацию
            if not hasattr(LogicBlock, '_counters'):
                LogicBlock._counters = {}

            # Инициализируем счетчик для типа если его нет
            if block_type not in LogicBlock._counters:
                LogicBlock._counters[block_type] = 0

            LogicBlock._counters[block_type] += 1
            self.name = f"{base_name}_{LogicBlock._counters[block_type]}"

        self.x = 0
        self.y = 0
        self.width = 80
        self.height = 50
        self.value: Optional[bool] = None

        # Каждый порт может иметь несколько соединений
        self.input_values: List[List[Optional[bool]]] = [[]]  # Список списков, начинаем с одного пустого порта
        self.input_connections: List[List[str]] = [[]]  # Список списков соединений
        self.output_connections: List[str] = []

        if self.type == BlockType.INPUT:
            # Для INPUT блока только одно значение
            self.value = False
            self.input_values = [[False]]

    def add_input_connection(self, conn_id: str, port: int = 0):
        """Добавить входное соединение на порт"""
        # Проверяем ограничения по количеству входов
        if self.type in [BlockType.NOT, BlockType.OUTPUT]:
            # Для NOT и OUTPUT можно только одно соединение
            if self.input_connections and any(len(port_conns) > 0 for port_conns in self.input_connections):
                print(f"  ERROR: {self.type.value} block {self.name} can have only ONE input connection")
                return False  # Не добавляем соединение

        # Расширяем списки если нужно
        while len(self.input_connections) <= port:
            self.input_connections.append([])
            self.input_values.append([])

        # Добавляем соединение если его еще нет
        if conn_id not in self.input_connections[port]:
            self.input_connections[port].append(conn_id)
            # Инициализируем values для порта если нужно
            if port >= len(self.input_values):
                self.input_values.append([])
            elif self.input_values[port] is None:
                self.input_values[port] = []

            # Добавляем место для значения
            self.input_values[port].append(None)

        return True  # Соединение успешно добавлено
    def add_output_connection(self, conn_id: str):
        """Добавить выходное соединение"""
        if conn_id not in self.output_connections:
            self.output_connections.append(conn_id)

    def remove_connection(self, conn_id: str):
        """Удалить соединение"""
        # Удаляем из выходных соединений
        if hasattr(self, 'output_connections') and conn_id in self.output_connections:
            self.output_connections.remove(conn_id)

        # Удаляем из входных соединений
        if hasattr(self, 'input_connections'):
            for port_idx, port_connections in enumerate(self.input_connections):
                if conn_id in port_connections:
                    index = port_connections.index(conn_id)
                    port_connections.remove(conn_id)

                    # Удаляем соответствующее значение
                    if (hasattr(self, 'input_values') and
                            port_idx < len(self.input_values) and
                            self.input_values[port_idx] is not None and
                            index < len(self.input_values[port_idx])):
                        del self.input_values[port_idx][index]

    def set_input_value(self, port: int, connection_index: int, value: bool):
        """Установить значение для конкретного соединения на порту"""
        # Убедимся что input_values существует и инициализирован
        if not hasattr(self, 'input_values') or self.input_values is None:
            self.input_values = [[]]

        # Расширяем до нужного порта
        while len(self.input_values) <= port:
            self.input_values.append([])

        # Получаем список значений для порта
        port_values = self.input_values[port]
        if port_values is None:
            port_values = []
            self.input_values[port] = port_values

        # Расширяем до нужного индекса
        while len(port_values) <= connection_index:
            port_values.append(None)

        port_values[connection_index] = value

    def compute(self) -> Optional[bool]:
        """Вычислить значение блока на основе всех входов"""
        if self.type == BlockType.INPUT:
            return self.value

        if self.type == BlockType.OUTPUT:
            # Для OUTPUT берем первое значение с первого порта
            if self.input_values and self.input_values[0]:
                return self.input_values[0][0] if self.input_values[0] else None
            return None

        # Собираем ВСЕ входные значения со ВСЕХ портов
        all_inputs = []
        for port_values in self.input_values:
            for val in port_values:
                if val is not None:
                    all_inputs.append(val)
                else:
                    # Если хоть одно значение неизвестно - результат неизвестен
                    return None

        # Если нет ни одного входа
        if not all_inputs:
            return None

        # Применяем логику
        if self.type == BlockType.AND:
            # AND всех значений
            return all(all_inputs)

        elif self.type == BlockType.OR:
            # OR всех значений
            return any(all_inputs)

        elif self.type == BlockType.NOT:
            # NOT от первого значения (должен быть только один вход)
            return not all_inputs[0] if all_inputs else None

        elif self.type == BlockType.XOR:
            # XOR: истинно если нечетное количество True
            true_count = sum(1 for v in all_inputs if v)
            return true_count % 2 == 1

        elif self.type == BlockType.NAND:
            # NAND: NOT(AND)
            return not all(all_inputs)

        elif self.type == BlockType.NOR:
            # NOR: NOT(OR)
            return not any(all_inputs)

        return None

    def get_input_port_position(self, port: int = 0) -> Tuple[int, int]:
        """Получить координаты входного порта"""
        if self.type == BlockType.INPUT:
            # У INPUT блоков входной порт слева
            return (self.x, self.y + self.height // 2)
        else:
            # У других блоков входные порты слева, распределенные по высоте
            num_ports = max(1, len(self.input_connections))
            spacing = self.height / (num_ports + 1)
            return (self.x, int(self.y + spacing * (port + 1)))

    def get_output_port_position(self) -> Tuple[int, int]:
        """Получить координаты выходного порта"""
        if self.type == BlockType.OUTPUT:
            # У OUTPUT блоков выходной порт справа
            return (self.x + self.width, self.y + self.height // 2)
        else:
            # У всех остальных выходной порт тоже справа
            return (self.x + self.width, int(self.y + self.height // 2))

    def is_inside(self, x: int, y: int) -> bool:
        """Проверить, находится ли точка внутри блока"""
        return (self.x <= x <= self.x + self.width and
                self.y <= y <= self.y + self.height)

    def get_port_at_position(self, x: int, y: int, is_input: bool) -> Optional[int]:
        """Найти порт по координатам"""
        if is_input:
            # Проверяем входные порты
            for i in range(max(1, len(self.input_connections))):
                px, py = self.get_input_port_position(i)
                if abs(px - x) <= 8 and abs(py - y) <= 8:
                    return i
        else:
            # Проверяем выходной порт
            px, py = self.get_output_port_position()
            if abs(px - x) <= 8 and abs(py - y) <= 8:
                return 0
        return None

    @classmethod
    def _create_from_saved_data(cls, block_type: BlockType, name: str, block_id: str,
                                x: int = 0, y: int = 0, width: int = 80,
                                height: int = 50, value=None) -> 'LogicBlock':
        """Создать блок из сохраненных данных с сохранением оригинального ID"""
        block = cls.__new__(cls)

        # Устанавливаем оригинальный ID
        block.id = block_id

        # Устанавливаем тип и имя
        block.type = block_type
        block.name = name

        # Устанавливаем геометрию
        block.x = x
        block.y = y
        block.width = width
        block.height = height

        # Устанавливаем значение
        block.value = value

        # Инициализируем списки соединений
        block.input_connections = []
        block.output_connections = []
        block.input_values = [[]]

        # Обновляем счетчик имен для этого типа
        if hasattr(cls, '_counters'):
            # Извлекаем базовое имя (без номера)
            base_name = name
            for suffix in ['_1', '_2', '_3', '_4', '_5', '_6', '_7', '_8', '_9', '_10']:
                if name.endswith(suffix):
                    base_name = name[:-len(suffix)]
                    try:
                        # Пробуем извлечь номер
                        num = int(suffix[1:])
                        # Обновляем счетчик если нужно
                        if block_type not in cls._counters or cls._counters[block_type] < num:
                            cls._counters[block_type] = num
                    except:
                        pass
                    break

        return block

    def __repr__(self):
        return f"LogicBlock(id={self.id}, name={self.name}, type={self.type.value})"


class Circuit:
    """Схема - коллекция блоков и соединений"""

    def __init__(self):
        self.blocks: Dict[str, LogicBlock] = {}
        self.connections: Dict[str, Connection] = {}

        # Инициализируем счетчики при создании первой схемы
        if not hasattr(LogicBlock, '_counters'):
            LogicBlock._counters = {}

    def add_block(self, block: LogicBlock) -> str:
        """Добавить блок в схему"""
        self.blocks[block.id] = block
        print(f"\n=== DEBUG Created block ===")
        print(f"Block ID: {block.id}")
        print(f"Block name: {block.name}")
        print(f"Block type: {block.type}")
        print("=======================\n")
        return block.id

    def remove_block(self, block_id: str):
        """Удалить блок и все связанные соединения"""
        if block_id in self.blocks:
            block = self.blocks[block_id]
            # Удаляем все соединения
            conn_ids = []

            # Выходные соединения
            conn_ids.extend(block.output_connections)

            # Входные соединения
            for port_connections in block.input_connections:
                conn_ids.extend(port_connections)

            for conn_id in conn_ids:
                if conn_id:
                    self.remove_connection(conn_id)
            del self.blocks[block_id]

    def add_connection(self, source_id: str, target_id: str, target_port: int = 0) -> Optional[str]:
        print(f"\n=== ADD_CONNECTION ===")
        print(f"  From: {source_id}")
        print(f"  To:   {target_id}:{target_port}")

        if source_id == target_id:
            print("  ERROR: Cannot connect block to itself")
            return None

        source_block = self.blocks.get(source_id)
        target_block = self.blocks.get(target_id)

        if not source_block:
            print(f"  ERROR: Source block {source_id} not found")
            return None

        if not target_block:
            print(f"  ERROR: Target block {target_id} not found")
            return None

        # Проверка ограничений для целевого блока
        if target_block.type in [BlockType.NOT, BlockType.OUTPUT]:
            # Подсчитываем общее количество входных соединений
            total_inputs = 0
            for port_connections in target_block.input_connections:
                total_inputs += len(port_connections)

            if total_inputs >= 1:
                print(
                    f"  ERROR: {target_block.type.value} block '{target_block.name}' can have only ONE input connection")
                return None

        print(f"  Source: {source_block.name} ({source_block.type}), value={source_block.value}")
        print(f"  Target: {target_block.name} ({target_block.type})")

        # Создаем соединение
        conn = Connection("", source_id, target_id, target_port)
        print(f"  Connection ID: {conn.id}")

        self.connections[conn.id] = conn

        # Обновляем блоки
        source_block.add_output_connection(conn.id)

        # Находим свободный индекс в порту
        if target_port >= len(target_block.input_connections):
            # Портов еще нет - добавляем как первый
            connection_index = 0
        else:
            # Уже есть соединения на этом порту - добавляем в конец
            connection_index = len(target_block.input_connections[target_port])

        target_block.add_input_connection(conn.id, target_port)

        print(f"  Added to port {target_port}, connection index {connection_index}")
        if target_port < len(target_block.input_connections):
            print(f"  Total connections on port {target_port}: {len(target_block.input_connections[target_port])}")
        print("=" * 30)

        return conn.id

    def remove_connection(self, conn_id: str):
        """Удалить соединение"""
        if conn_id in self.connections:
            conn = self.connections[conn_id]

            # Удаляем из блоков
            if conn.source_id in self.blocks:
                source_block = self.blocks[conn.source_id]
                if conn_id in source_block.output_connections:
                    source_block.output_connections.remove(conn_id)

            if conn.target_id in self.blocks:
                target_block = self.blocks[conn.target_id]
                # Ищем соединение во всех портах
                for port_connections in target_block.input_connections:
                    if conn_id in port_connections:
                        index = port_connections.index(conn_id)
                        port_connections.remove(conn_id)
                        # Удаляем соответствующее значение
                        port_index = target_block.input_connections.index(port_connections)
                        if port_index < len(target_block.input_values) and index < len(
                                target_block.input_values[port_index]):
                            del target_block.input_values[port_index][index]
                        break

            del self.connections[conn_id]

    def _would_create_cycle(self, source_id: str, target_id: str) -> bool:
        """Проверить, создаст ли соединение цикл (DFS)"""
        visited = set()

        def dfs(current_id: str) -> bool:
            if current_id == source_id:
                return True
            if current_id in visited:
                return False

            visited.add(current_id)
            block = self.blocks.get(current_id)
            if not block:
                return False

            for conn_id in block.output_connections:
                conn = self.connections.get(conn_id)
                if conn and dfs(conn.target_id):
                    return True
            return False

        return dfs(target_id)

    def get_block_at_position(self, x: int, y: int) -> Optional[LogicBlock]:
        """Найти блок по координатам"""
        for block in self.blocks.values():
            if block.is_inside(x, y):
                return block
        return None