"""
Панель анализа MC/DC покрытия входов
"""
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Dict, List
from logic_trainer.core.coverage import CoverageAnalyzer
from logic_trainer.core.test_cases import TestSuite


class MCDCPanel(ttk.Frame):
    """Панель анализа MC/DC покрытия входов (упрощенная версия)"""

    def __init__(self, parent, coverage_analyzer: CoverageAnalyzer,
                 test_suite: TestSuite, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.analyzer = coverage_analyzer
        self.test_suite = test_suite

        self.setup_ui()
        self.refresh_data()

    def setup_ui(self):
        """Настроить интерфейс панели MC/DC"""
        # Заголовок
        title = ttk.Label(
            self,
            text="Анализ MC/DC покрытия входов",
            font=('Arial', 11, 'bold')
        )
        title.pack(pady=10)

        # Описание
        desc = ttk.Label(
            self,
            text="MC/DC проверяет что каждый вход независимо влияет на выход.\n"
                 "Требует пары тестов, отличающиеся только одним входом.",
            font=('Arial', 9),
            justify=tk.LEFT,
            foreground='gray'
        )
        desc.pack(pady=(0, 15), padx=10)

        # Основная статистика
        self.stats_frame = ttk.Frame(self)
        self.stats_frame.pack(fill=tk.X, padx=10, pady=5)

        # Используем отдельные переменные для упрощения доступа
        self.total_var = tk.StringVar(value="0")
        self.covered_var = tk.StringVar(value="0")
        self.percentage_var = tk.StringVar(value="0%")

        self._create_stat_label(self.stats_frame, "Всего входов:", self.total_var, 0, 0)
        self._create_stat_label(self.stats_frame, "Покрыто MC/DC:", self.covered_var, 0, 1)
        self._create_stat_label(self.stats_frame, "Процент MC/DC:", self.percentage_var, 1, 0)

        # Прогресс-бар
        self.progress = ttk.Progressbar(
            self,
            length=200,
            mode='determinate'
        )
        self.progress.pack(fill=tk.X, padx=10, pady=10)

        # Кнопки управления
        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill=tk.X, padx=10, pady=10)

        ttk.Button(
            btn_frame,
            text="Анализировать MC/DC",
            command=self.analyze_mcdc,
            width=18
        ).pack(side=tk.LEFT, padx=2)

        ttk.Button(
            btn_frame,
            text="Показать отчет",
            command=self.show_report,
            width=15
        ).pack(side=tk.LEFT, padx=2)

        ttk.Button(
            btn_frame,
            text="Предложить тесты",
            command=self.suggest_tests,
            width=18
        ).pack(side=tk.RIGHT, padx=2)

        # Разделитель
        ttk.Separator(self, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=10, pady=10)

        # Детальная таблица
        ttk.Label(
            self,
            text="Детали по входам:",
            font=('Arial', 10, 'bold')
        ).pack(anchor=tk.W, padx=10, pady=(0, 5))

        # Контейнер для таблицы с прокруткой
        table_container = ttk.Frame(self)
        table_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

        # Таблица
        columns = ("Вход", "MC/DC", "Пар тестов", "Влияет на выходы")
        self.tree = ttk.Treeview(table_container, columns=columns,
                                 show="headings", height=8)

        # Настройка колонок
        self.tree.column("Вход", width=120)
        self.tree.column("MC/DC", width=80, anchor=tk.CENTER)
        self.tree.column("Пар тестов", width=80, anchor=tk.CENTER)
        self.tree.column("Влияет на выходы", width=150)

        for col in columns:
            self.tree.heading(col, text=col)

        # Полоса прокрутки
        scrollbar = ttk.Scrollbar(table_container, orient=tk.VERTICAL,
                                  command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Привязка событий
        self.tree.bind("<Double-1>", self.on_row_double_click)

    def _create_stat_label(self, parent, text, var, row, col, padx=5):
        """Создать метку статистики с переменной"""
        frame = ttk.Frame(parent)
        frame.grid(row=row, column=col, sticky=tk.W, padx=padx, pady=2)

        ttk.Label(frame, text=text, font=('Arial', 9)).pack(side=tk.LEFT)
        label = ttk.Label(frame, textvariable=var, font=('Arial', 9, 'bold'))
        label.pack(side=tk.LEFT, padx=(5, 0))
        return label

    def analyze_mcdc(self):
        """Выполнить анализ MC/DC входов"""

        if not self.test_suite.test_cases:
            messagebox.showwarning("Внимание", "Нет тестовых случаев для анализа")
            return

        try:
            # Запускаем полный анализ (включая MC/DC входов)
            results = self.analyzer.analyze_all(self.test_suite, None)

            # Обновляем UI
            self.refresh_data()

            mcdc_stats = results['mcdc']['statistics']
            messagebox.showinfo(
                "Анализ MC/DC завершен",
                f"MC/DC анализ входов выполнен.\n\n"
                f"• Покрыто входов: {mcdc_stats['covered_inputs']}/{mcdc_stats['total_inputs']}\n"
                f"• Процент MC/DC: {mcdc_stats['coverage_percentage']:.1f}%"
            )
        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка анализа MC/DC: {str(e)}")
            import traceback
            traceback.print_exc()

    def refresh_data(self):
        """Обновить данные на панели"""
        # Очищаем таблицу
        for item in self.tree.get_children():
            self.tree.delete(item)

        # Если есть результаты MC/DC анализа входов
        if hasattr(self.analyzer, 'mcdc_results') and self.analyzer.mcdc_results:
            results = self.analyzer.mcdc_results
            stats = results['statistics']

            # Обновляем статистику через переменные
            self.total_var.set(str(stats['total_inputs']))
            self.covered_var.set(str(stats['covered_inputs']))
            self.percentage_var.set(f"{stats['coverage_percentage']:.1f}%")

            # Обновляем прогресс-бар
            self.progress['value'] = stats['coverage_percentage']

            # Заполняем таблицу
            for detail in stats['input_details']:
                status = "✓" if detail['covered'] else "✗"
                status_color = "green" if detail['covered'] else "red"

                # Используем человеческие имена выходов
                outputs_str = ", ".join(detail['influences_outputs']) if detail['influences_outputs'] else "—"

                item_id = self.tree.insert("", tk.END, values=(
                    detail['name'],
                    status,
                    detail['pair_count'],
                    outputs_str
                ))

                # Цвет строки
                if detail['covered']:
                    self.tree.item(item_id, tags=("covered",))
                else:
                    self.tree.item(item_id, tags=("uncovered",))

            # Настройка цветов
            self.tree.tag_configure("covered", foreground="green")
            self.tree.tag_configure("uncovered", foreground="red")
        else:
            # Нет данных
            self.total_var.set("0")
            self.covered_var.set("0")
            self.percentage_var.set("0%")
            self.progress['value'] = 0

    def show_report(self):
        """Показать полный отчет по MC/DC входам"""
        if hasattr(self.analyzer, 'mcdc_results') and self.analyzer.mcdc_results:
            # Используем метод анализатора для генерации отчета
            if hasattr(self.analyzer.mcdc_analyzer, 'get_mcdc_report'):
                report = self.analyzer.mcdc_analyzer.get_mcdc_report()
            else:
                report = self.generate_simple_report()

            # Создаем окно с отчетом
            report_window = tk.Toplevel(self)
            report_window.title("Отчет MC/DC входов")
            report_window.geometry("600x500")

            # Текстовое поле с прокруткой
            text_frame = ttk.Frame(report_window)
            text_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

            text_widget = tk.Text(text_frame, wrap=tk.WORD, font=('Courier', 9))
            scrollbar = ttk.Scrollbar(text_frame, command=text_widget.yview)
            text_widget.configure(yscrollcommand=scrollbar.set)

            text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

            text_widget.insert(tk.END, report)
            text_widget.config(state=tk.DISABLED)

            # Кнопка закрытия
            ttk.Button(report_window, text="Закрыть",
                       command=report_window.destroy).pack(pady=10)
        else:
            messagebox.showinfo("Отчет", "Сначала выполните анализ MC/DC")

    def generate_simple_report(self) -> str:
        """Сгенерировать простой отчет"""
        if not hasattr(self.analyzer, 'mcdc_results'):
            return "MC/DC анализ не выполнен"

        results = self.analyzer.mcdc_results
        stats = results['statistics']

        report = [
            "=" * 50,
            "ОТЧЕТ ПО MC/DC ПОКРЫТИЮ ВХОДОВ",
            "=" * 50,
            f"Всего входов: {stats['total_inputs']}",
            f"Покрыто MC/DC: {stats['covered_inputs']}",
            f"Процент MC/DC: {stats['coverage_percentage']:.1f}%",
            "",
            "ДЕТАЛИ ПО ВХОДАМ:",
            ""
        ]

        for detail in stats['input_details']:
            status = "✓" if detail['covered'] else "✗"
            report.append(f"{status} {detail['name']}:")
            report.append(f"  Пары тестов: {detail['pair_count']}")
            report.append(f"  Влияет на выходы: {', '.join(detail['influences_outputs']) if detail['influences_outputs'] else 'нет данных'}")
            report.append("")

        return "\n".join(report)

    def suggest_tests(self):
        """Предложить недостающие тесты для MC/DC входов"""
        if not hasattr(self.analyzer, 'mcdc_results') or not self.analyzer.mcdc_results:
            messagebox.showwarning("Внимание", "Сначала выполните анализ MC/DC")
            return

        try:
            # Используем анализатор MC/DC для генерации предложений
            if hasattr(self.analyzer.mcdc_analyzer, 'suggest_missing_tests'):
                suggestions = self.analyzer.mcdc_analyzer.suggest_missing_tests(self.test_suite)

                if not suggestions:
                    messagebox.showinfo("Рекомендации", "Все входы покрыты MC/DC!")
                    return

                # Показываем рекомендации
                self.show_suggestions(suggestions)
            else:
                messagebox.showinfo("Рекомендации", "Генератор рекомендаций не доступен")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка при генерации рекомендаций: {str(e)}")
            import traceback
            traceback.print_exc()

    def show_suggestions(self, suggestions: List[Dict]):
        """Показать рекомендации по тестам"""
        suggestions_window = tk.Toplevel(self)
        suggestions_window.title("Рекомендации по тестам для MC/DC")
        suggestions_window.geometry("500x400")

        # Заголовок
        ttk.Label(
            suggestions_window,
            text="Рекомендуемые тесты для улучшения MC/DC покрытия:",
            font=('Arial', 10, 'bold')
        ).pack(pady=10)

        # Текстовое поле с прокруткой
        text_frame = ttk.Frame(suggestions_window)
        text_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        text = tk.Text(text_frame, wrap=tk.WORD, font=('Arial', 9))
        scrollbar = ttk.Scrollbar(text_frame, command=text.yview)
        text.configure(yscrollcommand=scrollbar.set)

        text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Заполняем текст
        for i, suggestion in enumerate(suggestions, 1):
            text.insert(tk.END, f"{i}. Для входа '{suggestion['input_name']}':\n")
            text.insert(tk.END, f"   На основе теста: '{suggestion['base_test']}'\n")
            text.insert(tk.END, f"   Изменить: {suggestion['change_type']}\n")
            text.insert(tk.END, f"   Причина: {suggestion['reason']}\n\n")

        text.config(state=tk.DISABLED)

        # Кнопки
        btn_frame = ttk.Frame(suggestions_window)
        btn_frame.pack(fill=tk.X, padx=10, pady=10)

        ttk.Button(
            btn_frame,
            text="Закрыть",
            command=suggestions_window.destroy
        ).pack()

    def on_row_double_click(self, event):
        """Обработка двойного клика по строке"""
        selection = self.tree.selection()
        if selection:
            item = self.tree.item(selection[0])
            input_name = item['values'][0]

            # Находим детали по этому входу
            if hasattr(self.analyzer, 'mcdc_results'):
                for detail in self.analyzer.mcdc_results['statistics']['input_details']:
                    if detail['name'] == input_name:
                        self.show_input_details(input_name, detail)
                        break

    def show_input_details(self, input_name: str, data: Dict):
        """Показать детали по конкретному входу"""
        details_window = tk.Toplevel(self)
        details_window.title(f"Детали MC/DC: {input_name}")
        details_window.geometry("500x400")

        # Заголовок
        status = "✓ ПОКРЫТ" if data['covered'] else "✗ НЕ ПОКРЫТ"
        color = "green" if data['covered'] else "red"

        ttk.Label(details_window, text=f"Вход: {input_name}",
                  font=('Arial', 12, 'bold')).pack(pady=10)

        status_label = ttk.Label(details_window, text=status,
                                 font=('Arial', 11, 'bold'),
                                 foreground=color)
        status_label.pack(pady=5)

        # Детали
        frame = ttk.Frame(details_window)
        frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

        if data['covered']:
            ttk.Label(frame, text=f"Найдено пар тестов: {data['pair_count']}",
                      font=('Arial', 9)).pack(anchor=tk.W, pady=2)

            # Выходы
            outputs_str = ", ".join(data['influences_outputs']) if data['influences_outputs'] else "—"
            ttk.Label(frame, text=f"Влияет на выходы: {outputs_str}",
                      font=('Arial', 9)).pack(anchor=tk.W, pady=2)

            # Пары тестов (если есть детали)
            if data.get('test_pair_details'):
                ttk.Label(frame, text="Примеры пар тестов:",
                          font=('Arial', 9, 'bold')).pack(anchor=tk.W, pady=(10, 5))

                for pair_detail in data['test_pair_details'][:3]:  # Первые 3 пары
                    ttk.Label(frame, text=f"• {pair_detail.get('pair', 'N/A')}",
                              font=('Arial', 8)).pack(anchor=tk.W, padx=10)
        else:
            ttk.Label(frame, text="Не найдено пар тестов, отличающихся только этим входом.",
                      font=('Arial', 9), foreground='red').pack(anchor=tk.W, pady=10)

            ttk.Label(frame, text="Для MC/DC покрытия нужны два теста:",
                      font=('Arial', 9)).pack(anchor=tk.W, pady=5)

            ttk.Label(frame, text="1. Отличающиеся ТОЛЬКО этим входом",
                      font=('Arial', 8)).pack(anchor=tk.W, padx=20)
            ttk.Label(frame, text="2. С разными значениями выхода",
                      font=('Arial', 8)).pack(anchor=tk.W, padx=20)

        # Кнопка закрытия
        ttk.Button(details_window, text="Закрыть",
                   command=details_window.destroy).pack(pady=20)