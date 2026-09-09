import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from logic_trainer.core.mcdc_analyzer import MCDCAnalyzer
from logic_trainer.core.test_cases import TestSuite
from logic_trainer.core.block import Circuit, BlockType, LogicBlock
from logic_trainer.core.simulator import Simulator
from logic_trainer.core.coverage import CoverageAnalyzer
from logic_trainer.ui.canvas import LogicCanvas
from logic_trainer.ui.toolbar import Toolbar
from logic_trainer.ui.coverage_panel import CoveragePanel
from logic_trainer.ui.test_table import TestTable
from logic_trainer.ui.mcdc_panel import MCDCPanel
from logic_trainer.utils.serialization import CircuitSerializer
from typing import List, Optional, Dict, Tuple

class LogicTrainerApp:
    """Главное приложение"""

    def __init__(self, root):
        self.root = root
        self.root.title("Logic Trainer - Boolean Coverage Analyzer")
        self.root.geometry("1200x700")

        # Создаем схему
        self.circuit = Circuit()

        # Создаем анализатор покрытия
        self.analyzer = CoverageAnalyzer(self.circuit)

        # Создаем симулятор с передачей схемы
        self.simulator = Simulator(self.circuit)

        # Создаем тестовый набор
        self.test_suite = TestSuite(self.circuit)
        self.simulator.set_test_suite(self.test_suite)

        # Текущий файл
        self.current_file = None

        # Настраиваем интерфейс
        self.setup_ui()

        # Обновляем статистику
        self.update_stats()

    def setup_ui(self):
        """Настроить пользовательский интерфейс"""
        # Панель инструментов (слева)
        self.left_panel = ttk.Frame(self.root, width=200)
        self.left_panel.pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=5)

        # Центральная панель
        self.center_panel = ttk.Frame(self.root)
        self.center_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Правая панель с Notebook (вкладками)
        self.right_panel = ttk.Frame(self.root, width=350)
        self.right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, padx=5, pady=5)

        # Создаем холст с передачей всех параметров
        self.canvas = LogicCanvas(
            self.center_panel,
            self.circuit,
            self.simulator
        )
        self.canvas.pack(fill=tk.BOTH, expand=True)

        # Создаем панель инструментов
        self.toolbar = Toolbar(self.left_panel, self.canvas)
        self.toolbar.pack(fill=tk.Y, expand=True)

        # Создаем Notebook для правой панели
        self.right_notebook = ttk.Notebook(self.right_panel)
        self.right_notebook.pack(fill=tk.BOTH, expand=True)

        # Вкладка 1: Покрытие
        self.coverage_tab = ttk.Frame(self.right_notebook)
        self.right_notebook.add(self.coverage_tab, text="Покрытие")

        # Вкладка 2: Тесты
        self.tests_tab = ttk.Frame(self.right_notebook)
        self.right_notebook.add(self.tests_tab, text="Тесты")

        # Вкладка 3: MC/DC
        self.mcdc_tab = ttk.Frame(self.right_notebook)
        self.right_notebook.add(self.mcdc_tab, text="MC/DC")

        # Создаем таблицу тестов на своей вкладке
        self.test_table = TestTable(
            self.tests_tab,
            self.test_suite,
            on_case_selected=self.on_test_case_selected,
            app_reference=self  # ← Передаем ссылку на себя
        )
        self.test_table.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Создаем панель покрытия на своей вкладке
        self.coverage_panel = CoveragePanel(
            self.coverage_tab,
            self.analyzer,
            self.test_suite,
            self.simulator
        )
        self.coverage_panel.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)




        # Создаем панель управления под холстом
        self.setup_control_panel()

        # Привязка событий
        self.setup_bindings()

    # В класс LogicTrainerApp добавить:
    def show_analysis_results(self, results: Dict):
        """Показать результаты анализа"""
        from tkinter.scrolledtext import ScrolledText

        # Создаем окно с результатами
        results_window = tk.Toplevel(self.root)
        results_window.title("Результаты полного анализа")
        results_window.geometry("800x600")

        # Заголовок
        title_label = ttk.Label(
            results_window,
            text="📊 РЕЗУЛЬТАТЫ ПОЛНОГО АНАЛИЗА",
            font=('Arial', 12, 'bold')
        )
        title_label.pack(pady=10)

        # Основной текст с прокруткой
        text_area = ScrolledText(
            results_window,
            wrap=tk.WORD,
            font=('Courier', 10),
            width=80,
            height=30
        )
        text_area.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # Получаем отчет из анализатора
        report = self.analyzer.get_combined_report()
        text_area.insert(tk.END, report)
        text_area.config(state=tk.DISABLED)

        # Кнопка закрытия
        ttk.Button(
            results_window,
            text="Закрыть",
            command=results_window.destroy,
            width=15
        ).pack(pady=10)

    def add_test_from_current_state(self):
        """Добавить тестовый случай из текущего состояния"""
        inputs = {}
        expected = {}

        for block_id, block in self.circuit.blocks.items():
            if block.type == BlockType.INPUT and block.value is not None:
                inputs[block_id] = block.value
            elif block.type == BlockType.OUTPUT and block.value is not None:
                expected[block_id] = block.value

        if inputs:
            # Переключаемся на вкладку тестов
            self.right_notebook.select(1)  # Вкладка тестов

            # Добавляем тест
            name = f"Тест {len(self.test_suite.test_cases) + 1}"
            self.test_suite.add_test_case(name, inputs, expected)
            self.test_table.refresh_table()

            messagebox.showinfo("Успех", "Тестовый случай добавлен")
        else:
            messagebox.showwarning("Внимание",
                                   "Нет входных блоков со значениями")

    def on_test_case_selected(self, index: int, run_test: bool = False):
        """Обработка выбора тестового случая"""
        print(f"\n=== Test case selected: index={index}, run_test={run_test}")
        self.test_suite.set_current_case(index)

        # Применяем тестовый случай к схеме
        self.test_suite.apply_current_case()

        # Сбрасываем симулятор
        self.simulator.reset()

        # Если нужно запустить тест
        if run_test:
            print(f"Running test case {index}")
            results = self.simulator.run_current_test()
            print(f"Test results: {results}")
            self.canvas.redraw()
            self.update_coverage()
            self.test_table.refresh_table()
        else:
            # Просто показываем схему
            print(f"Showing test case {index}")
            self.canvas.redraw()

    def setup_control_panel(self):
        """Настроить панель управления"""
        control_frame = ttk.Frame(self.center_panel)
        control_frame.pack(fill=tk.X, pady=(5, 0))

        # # Кнопки управления симуляцией
        # self.start_btn = ttk.Button(
        #     control_frame,
        #     text="▶ Старт",
        #     command=self.start_simulation,
        #     width=10
        # )
        # self.start_btn.pack(side=tk.LEFT, padx=2)

        self.step_btn = ttk.Button(
            control_frame,
            text="⎚ Шаг",
            command=self.step_simulation,
            width=10
        )
        self.step_btn.pack(side=tk.LEFT, padx=2)

        self.reset_btn = ttk.Button(
            control_frame,
            text="↺ Сброс",
            command=self.reset_simulation,
            width=10
        )
        self.reset_btn.pack(side=tk.LEFT, padx=2)

        # Разделитель
        ttk.Separator(control_frame, orient=tk.VERTICAL).pack(side=tk.LEFT, padx=10, fill=tk.Y)

        # Кнопки файлов
        self.new_btn = ttk.Button(
            control_frame,
            text="Новый",
            command=self.new_circuit,
            width=10
        )
        self.new_btn.pack(side=tk.LEFT, padx=2)

        self.save_btn = ttk.Button(
            control_frame,
            text="Сохранить",
            command=self.save_circuit,
            width=10
        )
        self.save_btn.pack(side=tk.LEFT, padx=2)

        self.load_btn = ttk.Button(
            control_frame,
            text="Загрузить",
            command=self.open_circuit,
            width=10
        )
        self.load_btn.pack(side=tk.LEFT, padx=2)

        # Разделитель
        ttk.Separator(control_frame, orient=tk.VERTICAL).pack(side=tk.LEFT, padx=10, fill=tk.Y)

        # Анимация
        self.animation_var = tk.BooleanVar(value=True)

        self.animation_check = ttk.Checkbutton(
            control_frame,
            text="Анимация",
            variable=self.animation_var
        )
        self.animation_check.pack(side=tk.LEFT, padx=2)

        # Скорость
        ttk.Label(control_frame, text="Скорость:").pack(side=tk.LEFT, padx=(10, 5))
        self.speed_var = tk.IntVar(value=500)

        self.speed_scale = ttk.Scale(
            control_frame,
            from_=100,
            to=1000,
            variable=self.speed_var,
            orient=tk.HORIZONTAL,
            length=100
        )
        self.speed_scale.pack(side=tk.LEFT, padx=2)
        ttk.Separator(control_frame, orient=tk.VERTICAL).pack(side=tk.LEFT, padx=10, fill=tk.Y)


    def analyze_level_a(self):
        """Выполнить анализ DO-178C Level A"""
        try:
            print(f"\n{'=' * 60}")
            print("ЗАПУСК АНАЛИЗА DO-178C Level A")
            print(f"{'=' * 60}")

            # Запускаем полный анализ
            results = self.analyzer.analyze_all(self.test_suite, self.simulator)

            # Получаем статус Level A
            level_a_status = self.analyzer.get_level_a_status()

            # Показываем результаты
            self.show_level_a_results(results['decision_mcdc'])

            # Обновляем UI
            self.update_coverage()
            self.update_stats()

        except Exception as e:
            messagebox.showerror("Ошибка анализа", f"Ошибка при анализе DO-178C: {str(e)}")
            import traceback
            traceback.print_exc()

    def show_level_a_results(self, results: Dict):
        """Показать результаты анализа DO-178C Level A"""
        from tkinter.scrolledtext import ScrolledText

        # Создаем окно с результатами
        results_window = tk.Toplevel(self.root)
        results_window.title("Результаты анализа DO-178C Level A")
        results_window.geometry("900x700")

        # Заголовок
        title_label = ttk.Label(
            results_window,
            text="📊 DO-178C Level A АНАЛИЗ MC/DC ПОКРЫТИЯ ВЕТОК",
            font=('Arial', 14, 'bold')
        )
        title_label.pack(pady=10)

        # Статус
        stats = results['statistics']
        status_text = "✅ СООТВЕТСТВУЕТ" if stats['level_a_percentage'] == 100 else "❌ НЕ СООТВЕТСТВУЕТ"
        status_color = "green" if stats['level_a_percentage'] == 100 else "red"

        status_label = ttk.Label(
            results_window,
            text=f"Статус: {status_text}",
            font=('Arial', 12, 'bold'),
            foreground=status_color
        )
        status_label.pack(pady=5)

        # Статистика
        stats_frame = ttk.Frame(results_window)
        stats_frame.pack(fill=tk.X, padx=20, pady=10)

        stats_text = (
            f"Всего анализируемых блоков: {stats['total_blocks']}\n"
            f"Соответствует Level A: {stats['level_a_blocks']} ({stats['level_a_percentage']:.1f}%)\n"
            f"Branch coverage (True/False): {stats['branch_coverage_percentage']:.1f}%\n"
            f"Частичное MC/DC: {stats['partial_mcdc_percentage']:.1f}%"
        )

        stats_label = ttk.Label(
            stats_frame,
            text=stats_text,
            font=('Courier', 10),
            justify=tk.LEFT
        )
        stats_label.pack()

        # Разделитель
        ttk.Separator(results_window, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=20, pady=10)

        # Детальный отчет
        report_label = ttk.Label(
            results_window,
            text="Детальный отчет:",
            font=('Arial', 11, 'bold')
        )
        report_label.pack(pady=5)

        # Основной текст с прокруткой
        text_area = ScrolledText(
            results_window,
            wrap=tk.WORD,
            font=('Courier', 9),
            width=100,
            height=25
        )
        text_area.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # Вставляем отчет
        report = results.get('report', 'Отчет не доступен')
        text_area.insert(tk.END, report)
        text_area.config(state=tk.DISABLED)

        # Кнопки
        button_frame = ttk.Frame(results_window)
        button_frame.pack(pady=10)

        ttk.Button(
            button_frame,
            text="Экспорт отчета",
            command=lambda: self.export_report(report),
            width=15
        ).pack(side=tk.LEFT, padx=5)

        ttk.Button(
            button_frame,
            text="Закрыть",
            command=results_window.destroy,
            width=15
        ).pack(side=tk.LEFT, padx=5)

    def export_report(self, report: str):
        """Экспортировать отчет в файл"""
        from tkinter import filedialog
        import os

        filename = filedialog.asksaveasfilename(
            title="Экспорт отчета DO-178C",
            defaultextension=".txt",
            filetypes=[("Текстовые файлы", "*.txt"), ("Все файлы", "*.*")]
        )

        if filename:
            try:
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(report)
                messagebox.showinfo("Успех", f"Отчет сохранен в {os.path.basename(filename)}")
            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось сохранить отчет: {str(e)}")

    def setup_bindings(self):
        """Настроить привязки событий"""
        # Подписываемся на события холста
        self.canvas.bind('<<CircuitChanged>>', self.on_circuit_changed)
        self.canvas.bind('<<BlockValueChanged>>', self.on_block_value_changed)
        self.canvas.bind('<<MouseMove>>', self.on_mouse_move)
        self.canvas.bind('<<SelectionChanged>>', self.on_selection_changed)

        # Обновляем статистику при старте
        self.on_circuit_changed()

    def on_circuit_changed(self, event=None):
        """Обработка изменения схемы"""
        self.update_stats()

    def on_block_value_changed(self, event=None):
        """Обработка изменения значения блока"""
        self.update_coverage()

    def on_mouse_move(self, event):
        """Обработка движения мыши"""
        # Метод оставлен для совместимости, но теперь ничего не делает
        # так как StatusBar удален
        pass

    def on_selection_changed(self, event=None):
        """Обработка изменения выделения"""
        # Метод оставлен для совместимости, но теперь ничего не делает
        # так как StatusBar удален
        pass

    def update_stats(self):
        """Обновить статистику"""
        if hasattr(self, 'toolbar'):
            self.toolbar.update_stats()
        self.update_coverage()

    def update_coverage(self):
        """Обновить информацию о покрытии"""
        if not hasattr(self, 'analyzer'):
            print("No analyzer!")
            return

        try:
            # Собираем текущие состояния блоков
            block_states = {}
            for block_id, block in self.circuit.blocks.items():
                block_states[block_id] = block.value

            print(f"\n=== Main: Updating coverage ===")
            print(f"Circuit has {len(self.circuit.blocks)} blocks")
            for block_id, value in block_states.items():
                if value is not None:
                    block = self.circuit.blocks.get(block_id)
                    if block:
                        print(f"  - {block.name} ({block.type.value}) = {value}")

            # Обновляем UI покрытия
            if hasattr(self, 'coverage_panel') and self.coverage_panel is not None:
                self.coverage_panel.update_coverage(block_states)

        except Exception as e:
            print(f"Error in update_coverage: {e}")
            import traceback
            traceback.print_exc()

    def start_simulation(self):
        """Запустить непрерывную симуляцию"""
        try:
            changed_blocks = self.simulator.simulate_continuous()

            if changed_blocks and self.animation_var.get():
                for block_id in changed_blocks:
                    self.canvas.animate_signal(block_id, self.speed_var.get())

            self.canvas.redraw()
            self.update_coverage()

        except Exception as e:
            messagebox.showerror("Ошибка симуляции", str(e))

    def step_simulation(self):
        """Выполнить один шаг симуляции"""
        try:
            changed_blocks = self.simulator.simulate_step()

            if changed_blocks and self.animation_var.get():
                for block_id in changed_blocks:
                    self.canvas.animate_signal(block_id, self.speed_var.get())

            self.canvas.redraw()
            self.update_coverage()

        except Exception as e:
            messagebox.showerror("Ошибка симуляции", str(e))

    def reset_simulation(self):
        """Сбросить симуляцию"""
        self.simulator.reset()
        self.canvas.redraw()
        self.update_coverage()

    def new_circuit(self):
        """Создать новую схему"""
        if self.circuit.blocks:
            if not messagebox.askyesno("Подтверждение",
                                       "Создать новую схему? Несохраненные изменения будут потеряны."):
                return

        # ВАЖНО: Сбрасываем счетчики имен блоков
        if hasattr(LogicBlock, '_counters'):
            LogicBlock._counters.clear()

        new_circuit = Circuit()

        self.analyzer.update_circuit(new_circuit)

        # Очищаем схему
        self.circuit = new_circuit

        self.simulator = Simulator(self.circuit)
        self.analyzer = CoverageAnalyzer(self.circuit)
        self.test_suite = TestSuite(self.circuit)
        self.simulator.set_test_suite(self.test_suite)

        # Обновляем ссылки
        self.canvas.circuit = self.circuit
        self.canvas.simulator = self.simulator

        if hasattr(self, 'toolbar'):
            self.toolbar.circuit = self.circuit
            self.toolbar.canvas = self.canvas

        if hasattr(self, 'coverage_panel'):
            self.coverage_panel.analyzer = self.analyzer

        if hasattr(self, 'test_table'):
            self.test_table.test_suite = self.test_suite
            self.test_table.refresh_table()

        if hasattr(self, 'mcdc_panel'):
            self.mcdc_panel.test_suite = self.test_suite
            self.mcdc_panel.refresh_data()

        self.canvas.redraw()
        self.current_file = None

        self.update_stats()

        messagebox.showinfo("Новая схема", "Создана новая пустая схема")

    def open_circuit(self):
        """Открыть схему из файла"""
        from logic_trainer.utils.serialization import CircuitSerializer

        filename = filedialog.askopenfilename(
            title="Открыть схему",
            filetypes=[
                ("Файлы схем", "*.logic"),
                ("JSON файлы", "*.json"),
                ("Все файлы", "*.*")
            ]
        )

        if not filename:
            return

        try:
            print(f"\n{'=' * 60}")
            print(f"ЗАГРУЗКА СХЕМЫ: {filename}")
            print(f"{'=' * 60}")

            # Загружаем схему И тестовые случаи
            circuit, test_cases_data = CircuitSerializer.load_from_file(filename)

            # ВАЖНО: Полностью сбрасываем все состояния перед загрузкой
            self._reset_all_states()

            # Обновляем схему
            self.circuit = circuit

            # Создаем новые анализаторы
            self.analyzer = CoverageAnalyzer(circuit)
            self.analyzer.mcdc_analyzer = MCDCAnalyzer(circuit)

            # Создаем новый симулятор
            self.simulator = Simulator(circuit)

            # Создаем новый набор тестов
            self.test_suite = TestSuite(circuit)
            self.simulator.set_test_suite(self.test_suite)

            # ВОССТАНАВЛИВАЕМ ТЕСТОВЫЕ СЛУЧАИ с обновленными ID
            for test_data in test_cases_data:
                self.test_suite.add_test_case(
                    test_data['name'],
                    test_data['inputs'],
                    test_data['expected_outputs']
                )

                # Восстанавливаем статус выполнения если есть
                if test_data.get('passed') is not None:
                    for test_case in self.test_suite.test_cases:
                        if test_case.name == test_data['name']:
                            test_case.passed = test_data['passed']
                            break

            # Обновляем ссылки в UI компонентах
            self._update_ui_references(circuit)

            self.canvas.redraw()
            self.current_file = filename

            # Обновляем статистику
            self.update_stats()

            messagebox.showinfo("Успех",
                                f"Схема загружена\n"
                                f"Блоков: {len(circuit.blocks)}\n"
                                f"Тестовых случаев: {len(test_cases_data)}")

        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось загрузить схему: {str(e)}")
            import traceback
            traceback.print_exc()

    def _reset_all_states(self):
        """Полный сброс всех состояний"""
        print("Сброс всех состояний...")

        # Сбрасываем счетчики имен блоков
        if hasattr(LogicBlock, '_counters'):
            LogicBlock._counters.clear()
            print("Счетчики имен сброшены")

        # Сбрасываем все ссылки
        self.circuit = Circuit()
        self.analyzer = CoverageAnalyzer(self.circuit)
        self.simulator = Simulator(self.circuit)
        self.test_suite = TestSuite(self.circuit)
        self.simulator.set_test_suite(self.test_suite)

    def _update_ui_references(self, circuit):
        """Обновить ссылки в UI компонентах"""
        print("Обновление ссылок в UI...")

        # Холст
        self.canvas.circuit = circuit
        self.canvas.simulator = self.simulator

        # Панель инструментов
        if hasattr(self, 'toolbar'):
            self.toolbar.circuit = circuit
            self.toolbar.canvas = self.canvas
            self.toolbar.update_stats()

        # Панель покрытия
        if hasattr(self, 'coverage_panel'):
            self.coverage_panel.analyzer = self.analyzer
            self.coverage_panel.test_suite = self.test_suite
            self.coverage_panel.simulator = self.simulator

        # Таблица тестов
        if hasattr(self, 'test_table'):
            self.test_table.test_suite = self.test_suite
            self.test_table.refresh_table()

        # Панель MC/DC
        if hasattr(self, 'mcdc_panel'):
            self.mcdc_panel.analyzer = self.analyzer
            self.mcdc_panel.test_suite = self.test_suite

        print("Ссылки обновлены")

    def save_circuit(self):
        """Сохранить схему"""
        if not self.current_file:
            self.save_circuit_as()
        else:
            self._save_to_file(self.current_file)

    def save_circuit_as(self):
        """Сохранить схему как..."""
        from logic_trainer.utils.serialization import CircuitSerializer

        filename = filedialog.asksaveasfilename(
            title="Сохранить схему как",
            defaultextension=".logic",
            filetypes=[
                ("Файлы схем", "*.logic"),
                ("JSON файлы", "*.json"),
                ("Все файлы", "*.*")
            ]
        )

        if filename:
            self._save_to_file(filename)
            self.current_file = filename

    def _save_to_file(self, filename: str):
        """Сохранить схему в файл"""
        try:
            # Сохраняем схему И тестовые случаи
            CircuitSerializer.save_to_file(self.circuit, filename, self.test_suite)
            messagebox.showinfo("Успех", f"Схема сохранена\n"
                                      f"Тестовых случаев: {len(self.test_suite.test_cases)}")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось сохранить схему: {str(e)}")


def main():
    root = tk.Tk()
    app = LogicTrainerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()