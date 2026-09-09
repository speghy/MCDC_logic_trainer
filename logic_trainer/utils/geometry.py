"""
Геометрические утилиты для работы с координатами
"""


def distance(x1: int, y1: int, x2: int, y2: int) -> float:
    """Расстояние между двумя точками"""
    return ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5


def point_in_rect(x: int, y: int, rect_x: int, rect_y: int, width: int, height: int) -> bool:
    """Проверить, находится ли точка внутри прямоугольника"""
    return (rect_x <= x <= rect_x + width and
            rect_y <= y <= rect_y + height)


def line_intersection(line1, line2):
    """Найти точку пересечения двух линий"""
    (x1, y1), (x2, y2) = line1
    (x3, y3), (x4, y4) = line2

    denom = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
    if denom == 0:
        return None  # Линии параллельны

    px = ((x1 * y2 - y1 * x2) * (x3 - x4) - (x1 - x2) * (x3 * y4 - y3 * x4)) / denom
    py = ((x1 * y2 - y1 * x2) * (y3 - y4) - (y1 - y2) * (x3 * y4 - y3 * x4)) / denom

    return (px, py)


def bezier_curve(p0, p1, p2, p3, t):
    """Вычислить точку на кривой Безье"""
    x = (1 - t) ** 3 * p0[0] + 3 * (1 - t) ** 2 * t * p1[0] + 3 * (1 - t) * t ** 2 * p2[0] + t ** 3 * p3[0]
    y = (1 - t) ** 3 * p0[1] + 3 * (1 - t) ** 2 * t * p1[1] + 3 * (1 - t) * t ** 2 * p2[1] + t ** 3 * p3[1]
    return (x, y)


def create_smooth_connection(start, end, offset=50):
    """Создать контрольные точки для плавного соединения"""
    x1, y1 = start
    x2, y2 = end

    # Контрольные точки для кривой Безье
    dx = abs(x2 - x1)
    offset = min(offset, dx // 2)

    cp1 = (x1 + offset, y1)
    cp2 = (x2 - offset, y2)

    return cp1, cp2