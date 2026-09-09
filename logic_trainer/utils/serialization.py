"""
Сериализация и десериализация схем - ИСПРАВЛЕННАЯ ВЕРСИЯ
"""
from typing import Dict, Any, Tuple, List
from logic_trainer.core.block import Circuit, LogicBlock, Connection, BlockType
from logic_trainer.core.test_cases import TestSuite
import json
import pickle
import os


class CircuitSerializer:
    """Исправленный сериализатор схем"""

    @staticmethod
    def save_to_file(circuit: Circuit, filename: str, test_suite: TestSuite = None):
        """Сохранить схему и тестовые случаи в файл"""
        data = {
            'version': '1.2',
            'blocks': [],
            'connections': [],
            'test_cases': [],
            'counters': {}  # <-- СОХРАНЯЕМ СЧЕТЧИКИ!
        }

        print(f"\n=== СОХРАНЕНИЕ СХЕМЫ ===")

        # Сохраняем счетчики имен блоков
        if hasattr(LogicBlock, '_counters'):
            data['counters'] = LogicBlock._counters.copy()
            print(f"Счетчики имен: {LogicBlock._counters}")

        # Сохраняем блоки
        for block in circuit.blocks.values():
            block_data = {
                'id': block.id,  # <-- СОХРАНЯЕМ ОРИГИНАЛЬНЫЙ ID
                'type': block.type.value,
                'name': block.name,
                'x': block.x,
                'y': block.y,
                'width': block.width,
                'height': block.height,
                'value': block.value,
                # Сохраняем входные и выходные соединения
                'input_connections': block.input_connections,
                'output_connections': block.output_connections
            }
            data['blocks'].append(block_data)

        # Сохраняем соединения
        for conn in circuit.connections.values():
            conn_data = {
                'id': conn.id,
                'source_id': conn.source_id,
                'target_id': conn.target_id,
                'target_port': conn.target_port
            }
            data['connections'].append(conn_data)

        # Сохраняем тестовые случаи
        if test_suite:
            for test_case in test_suite.test_cases:
                test_data = {
                    'id': test_case.id,
                    'name': test_case.name,
                    'inputs': test_case.inputs,
                    'expected_outputs': test_case.expected_outputs,
                    'passed': test_case.passed
                }
                data['test_cases'].append(test_data)

        # Сохраняем в файл
        try:
            if filename.lower().endswith('.json'):
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
            else:
                with open(filename, 'wb') as f:
                    pickle.dump(data, f)

            print(f"✅ Успешно сохранено:")
            print(f"   Блоков: {len(data['blocks'])}")
            print(f"   Соединений: {len(data['connections'])}")
            print(f"   Тестов: {len(data['test_cases'])}")
            print(f"   Счетчиков: {len(data['counters'])}")

        except Exception as e:
            raise Exception(f"Ошибка сохранения файла {filename}: {str(e)}")

    @staticmethod
    def load_from_file(filename: str) -> Tuple[Circuit, List[Dict]]:
        """Загрузить схему и тестовые случаи из файла"""

        print(f"\n=== ЗАГРУЗКА СХЕМЫ ИЗ {filename} ===")

        if not os.path.exists(filename):
            raise FileNotFoundError(f"Файл {filename} не найден")

        # Загружаем данные
        try:
            if filename.lower().endswith('.logic'):
                with open(filename, 'rb') as f:
                    data = pickle.load(f)
            else:
                with open(filename, 'r', encoding='utf-8') as f:
                    data = json.load(f)
        except Exception as e:
            raise Exception(f"Ошибка загрузки файла {filename}: {str(e)}")

        # Проверяем версию
        version = data.get('version', '1.0')
        print(f"Версия файла: {version}")

        # ВАЖНО: Сначала восстанавливаем счетчики!
        if 'counters' in data and data['counters']:
            print(f"Восстанавливаем счетчики имен: {data['counters']}")
            # Инициализируем счетчики если их нет
            if not hasattr(LogicBlock, '_counters'):
                LogicBlock._counters = {}
            # Обновляем счетчики
            LogicBlock._counters.update(data['counters'])
        else:
            print("⚠️ В файле нет счетчиков, сбрасываем")
            if hasattr(LogicBlock, '_counters'):
                LogicBlock._counters.clear()
            else:
                LogicBlock._counters = {}

        # Создаем схему
        circuit = Circuit()

        # Словарь для преобразования типов
        type_map = {
            'INPUT': BlockType.INPUT,
            'OUTPUT': BlockType.OUTPUT,
            'AND': BlockType.AND,
            'OR': BlockType.OR,
            'NOT': BlockType.NOT,
            'XOR': BlockType.XOR,
            'NAND': BlockType.NAND,
            'NOR': BlockType.NOR,
            'Вход': BlockType.INPUT,
            'Выход': BlockType.OUTPUT,
            'И': BlockType.AND,
            'ИЛИ': BlockType.OR,
            'НЕ': BlockType.NOT,
            'ИсклИЛИ': BlockType.XOR,
            'И-НЕ': BlockType.NAND,
            'ИЛИ-НЕ': BlockType.NOR
        }

        # Восстанавливаем блоки
        print(f"\nВосстановление {len(data.get('blocks', []))} блоков...")
        blocks_by_original_id = {}
        blocks_by_name = {}

        for block_data in data.get('blocks', []):
            # Получаем оригинальный ID из файла
            original_id = str(block_data['id'])
            block_name = str(block_data.get('name', ''))

            # Определяем тип блока
            block_type_str = str(block_data.get('type', 'INPUT'))
            if block_type_str in type_map:
                block_type = type_map[block_type_str]
            else:
                # Пытаемся определить по имени
                if block_name.startswith('Вход'):
                    block_type = BlockType.INPUT
                elif block_name.startswith('Выход'):
                    block_type = BlockType.OUTPUT
                elif block_name.startswith('И') and 'НЕ' not in block_name:
                    block_type = BlockType.AND
                elif block_name.startswith('ИЛИ'):
                    block_type = BlockType.OR
                elif block_name.startswith('НЕ'):
                    block_type = BlockType.NOT
                else:
                    block_type = BlockType.INPUT

            # СОЗДАЕМ БЛОК С ЯВНЫМ УКАЗАНИЕМ ID
            block = LogicBlock._create_from_saved_data(
                block_type=block_type,
                name=block_name,
                block_id=original_id,  # <-- ПЕРЕДАЕМ ОРИГИНАЛЬНЫЙ ID!
                x=block_data.get('x', 0),
                y=block_data.get('y', 0),
                width=block_data.get('width', 80),
                height=block_data.get('height', 50),
                value=block_data.get('value')
            )

            # Восстанавливаем соединения из данных
            block.input_connections = block_data.get('input_connections', [])
            block.output_connections = block_data.get('output_connections', [])

            # Инициализируем input_values
            block.input_values = []
            for port_connections in block.input_connections:
                block.input_values.append([None] * len(port_connections))

            circuit.blocks[block.id] = block
            blocks_by_original_id[original_id] = block
            blocks_by_name[block_name] = block

            print(f"  ✓ {block.name} ({block.type.value}) ID={block.id}")

        # Восстанавливаем соединения
        print(f"\nВосстановление {len(data.get('connections', []))} соединений...")
        for conn_data in data.get('connections', []):
            source_id = str(conn_data.get('source_id', ''))
            target_id = str(conn_data.get('target_id', ''))

            # Проверяем, что блоки существуют
            if source_id not in blocks_by_original_id or target_id not in blocks_by_original_id:
                print(f"  ⚠️ Пропускаем соединение {source_id}->{target_id} (блок не найден)")
                continue

            source_block = blocks_by_original_id[source_id]
            target_block = blocks_by_original_id[target_id]

            target_port = int(conn_data.get('target_port', 0))
            conn_id = str(conn_data.get('id', ''))

            # Создаем соединение
            if not conn_id:
                import uuid
                conn_id = str(uuid.uuid4())[:8]

            conn = Connection(conn_id, source_block.id, target_block.id, target_port)
            circuit.connections[conn.id] = conn

            # Обновляем связи (уже есть в методах add_connection)
            circuit.add_connection(source_block.id, target_block.id, target_port)

            print(f"  ✓ {source_block.name} -> {target_block.name}:{target_port}")

        # Возвращаем тестовые случаи
        test_cases_data = data.get('test_cases', [])

        # Важно: конвертируем ID блоков в новые ID если нужно
        for test_case in test_cases_data:
            # Конвертируем ID входов
            new_inputs = {}
            for old_block_id, value in test_case.get('inputs', {}).items():
                if old_block_id in blocks_by_original_id:
                    new_inputs[blocks_by_original_id[old_block_id].id] = value
                else:
                    print(f"  ⚠️ Пропускаем вход {old_block_id} в тесте {test_case.get('name')}")

            # Конвертируем ID выходов
            new_outputs = {}
            for old_block_id, value in test_case.get('expected_outputs', {}).items():
                if old_block_id in blocks_by_original_id:
                    new_outputs[blocks_by_original_id[old_block_id].id] = value
                else:
                    print(f"  ⚠️ Пропускаем выход {old_block_id} в тесте {test_case.get('name')}")

            test_case['inputs'] = new_inputs
            test_case['expected_outputs'] = new_outputs

        print(f"\n✅ Загрузка завершена:")
        print(f"   Блоков: {len(circuit.blocks)}")
        print(f"   Соединений: {len(circuit.connections)}")
        print(f"   Тестов: {len(test_cases_data)}")

        return circuit, test_cases_data