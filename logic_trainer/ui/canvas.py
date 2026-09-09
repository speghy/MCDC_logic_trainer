"""
Графический холст для отрисовки схем
"""
import tkinter as tk
from typing import Optional, Tuple
from logic_trainer.core import Circuit, LogicBlock, Connection, BlockType
from logic_trainer.core import Simulator
from tkinter import messagebox

class LogicCanvas(tk.Canvas):
    """Холст для отрисовки логических схем"""

    def __init__(self, parent, circuit: Circuit, simulator: Simulator, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.parent = parent
        self.circuit = circuit
        self.simulator = simulator

        self.configure(bg='white', highlightthickness=1, highlightbackground='#cccccc')

        # Состояние
        self.selected_block: Optional[LogicBlock] = None
        self.dragging = False
        self.drag_start = (0, 0)
        self.creating_connection = False
        self.connection_source: Optional[str] = None
        self.temp_line = None
        self.last_click_time = 0

        # Цвета
        self.colors = {
            'background': 'white',
            'block_default': '#f0f0f0',
            'block_selected': '#d0e0ff',
            'block_active_true': '#90EE90',  # Светло-зеленый
            'block_active_false': '#FFB6C1',  # Светло-красный
            'connection': '#666666',
            'connection_active': '#4CAF50',  # ← ДОБАВЬ ЭТО! Или используй:
            'connection_active_true': '#4CAF50',  # Зеленый
            'connection_active_false': '#FF5722',  # Красный
            'port_input': '#2196F3',
            'port_output': '#FF9800',
            'text': '#000000',
            'grid': '#e0e0e0'
        }

        # Размеры - ДОБАВЬ ЭТО!
        self.block_width = 80
        self.block_height = 50
        self.port_radius = 5  # ← ВОТ ЭТО ДОБАВЬ!

        # Привязка событий
        self.bind_events()

        # Инициализируем отрисовку
        self.after(100, self.redraw)

    def _extract_block_id_from_tags(self, tags):
        """Извлечь ID блока из списка тегов"""
        for tag in tags:
            # Пропускаем системные теги
            if tag in ['current', 'block', 'output_port', 'input_port', 'port', 'block_text']:
                continue

            # Пропускаем теги портов
            if tag.startswith('port_'):
                continue

            # Пропускаем составные теги типа input_port_X_Y
            if tag.startswith('input_port_') or tag.startswith('output_port_'):
                parts = tag.split('_')
                if len(parts) >= 3:
                    # Возвращаем ID (третий элемент)
                    return parts[2]
                continue

            # Если тег похож на ID (8 hex символов)
            if len(tag) == 8 and all(c in '0123456789abcdef' for c in tag):
                return tag

        return None

    def _extract_port_index_from_tags(self, tags):
        """Извлечь индекс порта из списка тегов"""
        for tag in tags:
            if tag.startswith('port_'):
                try:
                    return int(tag.split('_')[1])
                except:
                    pass
        return 0

    def bind_events(self):
        """Привязать события мыши и клавиатуры"""
        self.bind("<Button-1>", self.on_mouse_down)
        self.bind("<B1-Motion>", self.on_mouse_drag)
        self.bind("<ButtonRelease-1>", self.on_mouse_up)
        self.bind("<Double-Button-1>", self.on_double_click)
        self.bind("<Delete>", self.on_delete)
        self.bind("<Configure>", self.on_resize)

    def redraw(self):
        """Перерисовать всю схему"""
        self.delete("all")

        # Рисуем соединения
        for conn in self.circuit.connections.values():
            self.draw_connection(conn)

        # Рисуем блоки поверх соединений
        for block in self.circuit.blocks.values():
            self.draw_block(block)

    def draw_block(self, block: LogicBlock):
        """Нарисовать блок на холсте"""
        # Цвет блока
        if block == self.selected_block:
            fill_color = self.colors['block_selected']
        elif block.value is True:
            fill_color = self.colors['block_active_true']
        elif block.value is False:
            fill_color = self.colors['block_active_false']
        else:
            fill_color = self.colors['block_default']

        # Основной прямоугольник
        rect = self.create_rectangle(
            block.x, block.y,
            block.x + block.width, block.y + block.height,
            fill=fill_color,
            outline='black',
            width=2,
            tags=('block', block.id)
        )

        # Текст
        if block.type == BlockType.INPUT:
            # Для INPUT: "Вход\n0/1"
            value_text = "1" if block.value else "0"
            text = f"Вход\n{value_text}"
        elif block.type == BlockType.OUTPUT:
            # Для OUTPUT: "Выход\n0/1" или "Выход\n-"
            value_text = "1" if block.value else "0" if block.value is not None else "-"
            text = f"Выход\n{value_text}"
        else:
            # Для логических блоков: "AND\n0/1" или "AND\n-"
            value_text = "1" if block.value else "0" if block.value is not None else "-"
            text = f"{block.type.value}\n{value_text}"

        text_id = self.create_text(
            block.x + block.width // 2,
            block.y + block.height // 2,
            text=text,
            font=('Arial', 9),
            fill=self.colors['text'],
            tags=('block_text', block.id)
        )

        # Порты
        self.draw_block_ports(block)

    def draw_block_ports(self, block: LogicBlock):
        """Нарисовать порты блока"""
        # Входные порты
        if block.type != BlockType.INPUT:
            num_ports = max(1, len(block.input_connections))
            spacing = block.height / (num_ports + 1)

            for port in range(num_ports):
                x, y = block.x, block.y + spacing * (port + 1)

                # Рисуем порт
                port_circle = self.create_oval(
                    x - self.port_radius, y - self.port_radius,
                    x + self.port_radius, y + self.port_radius,
                    fill=self.colors['port_input'],
                    outline='black',
                    width=1,
                    tags=(f'input_port_{block.id}_{port}', 'input_port', block.id)
                )

                # Если есть соединения - показываем количество
                if port < len(block.input_connections) and block.input_connections[port]:
                    count = len(block.input_connections[port])
                    self.create_text(
                        x - 10, y,
                        text=f"({count})",
                        font=('Arial', 7),
                        fill='red',
                        tags=(f'port_count_{block.id}_{port}', 'port_count')
                    )

        # Выходной порт
        if block.type != BlockType.OUTPUT:
            x, y = block.x + block.width, block.y + block.height // 2
            self.create_oval(
                x - self.port_radius, y - self.port_radius,
                x + self.port_radius, y + self.port_radius,
                fill=self.colors['port_output'],
                outline='black',
                width=1,
                tags=(f'output_port_{block.id}', 'output_port', block.id)
            )

    def draw_connection(self, conn: Connection):
        """Нарисовать соединение"""
        source = self.circuit.blocks.get(conn.source_id)
        target = self.circuit.blocks.get(conn.target_id)

        if not source or not target:
            return

        # Координаты
        x1, y1 = source.get_output_port_position()
        x2, y2 = target.get_input_port_position(conn.target_port)

        # Цвет соединения
        color = self.colors['connection']
        if source.value is not None:
            color = self.colors['connection_active'] if source.value else '#ff6b6b'

        # Создаем плавную кривую
        control_x = (x1 + x2) // 2

        line = self.create_line(
            x1, y1,
            control_x, y1,
            control_x, y2,
            x2, y2,
            smooth=False,
            fill=color,
            width=3 if source.value is not None else 2,
            arrow=tk.LAST,
            tags=('connection', conn.id)
        )

    def on_mouse_down(self, event):
        """Обработка нажатия кнопки мыши"""
        print(f"\n{'=' * 60}")
        print(f"MOUSE DOWN at ({event.x}, {event.y})")

        self.focus_set()

        items = self.find_withtag(tk.CURRENT)

        if not items:
            print("No items")
            self.selected_block = None
            self.dragging = False
            self.redraw()
            return

        all_tags = self.gettags(items[0])
        print(f"Tags: {all_tags}")

        # Ищем block_id
        block_id = None
        for tag in all_tags:
            if tag in ['current', 'block', 'output_port', 'input_port']:
                continue
            if tag.startswith('port_'):
                continue
            if len(tag) == 8 and all(c in '0123456789abcdef' for c in tag):
                block_id = tag
                break

        if not block_id:
            for tag in all_tags:
                if tag not in ['current', 'block', 'output_port', 'input_port']:
                    block_id = tag
                    break

        print(f"Block ID: {block_id}")

        # Определяем тип элемента
        is_output_port = 'output_port' in all_tags
        is_input_port = 'input_port' in all_tags
        is_block = 'block' in all_tags

        print(f"Type: output={is_output_port}, input={is_input_port}, block={is_block}")
        print(f"State: connecting={self.creating_connection}, source={self.connection_source}")

        # КРИТИЧЕСКИЙ ЛОГИЧЕСКИЙ БЛОК
        # Если уже создаем соединение И это input_port
        if self.creating_connection and is_input_port:
            print(">>> CASE A: Finishing connection (already connecting + clicked input_port)")

            if not block_id:
                print("ERROR: No block_id found!")
                self.cancel_connection()
                return

            # Находим порт
            port_idx = 0
            for tag in all_tags:
                if tag.startswith('port_'):
                    try:
                        port_idx = int(tag.split('_')[1])
                        break
                    except:
                        pass

            print(f"Trying to connect {self.connection_source} -> {block_id}:{port_idx}")

            # Создаем соединение
            conn_id = self.circuit.add_connection(
                self.connection_source,
                block_id,
                port_idx
            )

            if conn_id:
                print(f"SUCCESS: Connection created: {conn_id}")
                self.redraw()
                self.parent.event_generate('<<CircuitChanged>>')
            else:
                print(f"FAILED: Could not create connection")

            self.cancel_connection()
            return

        # Если кликнули на output_port и НЕ в режиме соединения
        elif is_output_port and not self.creating_connection:
            print(">>> CASE B: Starting new connection")
            self.creating_connection = True
            self.connection_source = block_id

            block = self.circuit.blocks.get(block_id)
            if block:
                x, y = block.get_output_port_position()
                self.temp_line = self.create_line(
                    x, y, event.x, event.y,
                    dash=(4, 2), fill='gray', width=2,
                    tags='temp_connection'
                )
            return

        # Если кликнули на блок
        elif is_block:
            print(">>> CASE C: Selecting block")
            block = self.circuit.blocks.get(block_id)
            if block:
                self.selected_block = block
                self.dragging = True
                self.drag_start = (event.x - block.x, event.y - block.y)
                self.redraw()
                self.parent.event_generate('<<SelectionChanged>>')
            return

        print(">>> CASE D: Unknown - doing nothing")

    def on_mouse_drag(self, event):
        """Обработка перемещения мыши с нажатой кнопкой"""
        if self.dragging and self.selected_block:
            # Перемещаем блок
            new_x = event.x - self.drag_start[0]
            new_y = event.y - self.drag_start[1]

            # Привязка к сетке
            grid_size = 10
            new_x = round(new_x / grid_size) * grid_size
            new_y = round(new_y / grid_size) * grid_size

            self.selected_block.x = new_x
            self.selected_block.y = new_y
            self.redraw()

        elif self.creating_connection and self.temp_line and self.connection_source:
            # Обновляем временную линию
            block = self.circuit.blocks.get(self.connection_source)
            if block:
                x1, y1 = block.get_output_port_position()
                self.coords(self.temp_line, x1, y1, event.x, event.y)

    def on_mouse_up(self, event):
        """Обработка отпускания кнопки мыши"""
        print(f"\n=== MOUSE UP at ({event.x}, {event.y}) ===")
        print(f"State: dragging={self.dragging}, creating={self.creating_connection}")

        if self.dragging:
            print("Finishing drag")
            self.dragging = False
            self.redraw()
            self.parent.event_generate('<<CircuitChanged>>')


        elif self.creating_connection:

            print("Mouse released while creating connection")

            items = self.find_overlapping(event.x - 5, event.y - 5, event.x + 5, event.y + 5)

            for item in items:

                tags = self.gettags(item)

                if 'input_port' in tags:

                    target_block_id = self._extract_block_id_from_tags(tags)

                    port_idx = self._extract_port_index_from_tags(tags)

                    if target_block_id and self.connection_source:

                        print(f"Auto-connecting: {self.connection_source} -> {target_block_id}:{port_idx}")

                        conn_id = self.circuit.add_connection(

                            self.connection_source,

                            target_block_id,

                            port_idx

                        )

                        if conn_id:
                            print(f"SUCCESS: Connection created: {conn_id}")
                            self.redraw()
                            self.parent.event_generate('<<CircuitChanged>>')
                        else:
                            print(f"FAILED: Could not create connection")
                            # Показать сообщение пользователю

                            messagebox.showwarning("Ошибка соединения",
                                                   f"Нельзя подключить больше одного входа к блоку")

                        self.cancel_connection()

                        return

            # Если не нашли input_port

            print("Not over input_port - cancelling")

            self.cancel_connection()

    def cancel_connection(self):
        """Отменить создание соединения"""
        self.creating_connection = False
        self.connection_start = None
        if self.temp_line:
            self.delete(self.temp_line)
            self.temp_line = None

    def on_double_click(self, event):
        """Обработка двойного клика - переключение INPUT значения"""
        items = self.find_withtag(tk.CURRENT)
        if items:
            tags = self.gettags(items[0])
            if 'block' in tags:
                block_id = tags[1]
                block = self.circuit.blocks.get(block_id)
                if block and block.type == BlockType.INPUT:
                    # Переключаем значение
                    new_value = not block.value if block.value is not None else True
                    block.value = new_value

                    # Добавляем в активные блоки симулятора
                    self.simulator.active_frontier.add(block_id)

                    self.redraw()
                    self.parent.event_generate('<<BlockValueChanged>>')

    def on_delete(self, event):
        """Обработка удаления"""
        if self.selected_block:
            self.circuit.remove_block(self.selected_block.id)
            self.selected_block = None
            self.redraw()
            self.parent.event_generate('<<CircuitChanged>>')

    def on_resize(self, event):
        """Обработка изменения размера"""
        self.redraw()

    def animate_signal(self, block_id: str, duration: int = 300):
        """Анимировать распространение сигнала от блока"""
        # Находим все соединения от этого блока
        connections_to_animate = []

        def collect_connections(current_id: str, depth: int = 0):
            block = self.circuit.blocks.get(current_id)
            if not block:
                return

            for conn_id in block.output_connections:
                connections_to_animate.append((conn_id, depth))
                conn = self.circuit.connections.get(conn_id)
                if conn:
                    collect_connections(conn.target_id, depth + 1)

        collect_connections(block_id)

        # Анимируем каждое соединение с задержкой
        for i, (conn_id, depth) in enumerate(connections_to_animate):
            self.after(duration * depth, self.highlight_connection, conn_id, duration)

    def highlight_connection(self, conn_id: str, duration: int):
        """Подсветить соединение"""
        items = self.find_withtag(conn_id)
        if items:
            original_color = self.itemcget(items[0], 'fill')
            original_width = self.itemcget(items[0], 'width')

            # Подсветка
            self.itemconfig(items[0], fill='yellow', width=4)

            # Возврат к исходному состоянию
            self.after(duration, lambda: self.itemconfig(items[0],
                                                         fill=original_color,
                                                         width=original_width))