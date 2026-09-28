from PyQt5.QtWidgets import QLayout
from PyQt5.QtCore import Qt, QRect, QSize, QPoint


class FlowLayout(QLayout):
    """
    流式布局：子控件从左到右排列，自动换行
    支持设置水平和垂直间距
    """

    def __init__(self, parent=None, margin=0, spacing=4):
        super().__init__(parent)
        if parent is not None:
            self.setContentsMargins(margin, margin, margin, margin)
        self._spacing = spacing
        self._items = []

    def __del__(self):
        while self.count():
            self.takeAt(0)

    def addItem(self, item):
        self._items.append(item)

    def count(self):
        return len(self._items)

    def itemAt(self, index):
        if 0 <= index < len(self._items):
            return self._items[index]
        return None

    def takeAt(self, index):
        if 0 <= index < len(self._items):
            return self._items.pop(index)
        return None

    def expandingDirections(self):
        return Qt.Orientations(Qt.Orientation(0))

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, width):
        return self._do_layout(QRect(0, 0, width, 0), True)

    def setGeometry(self, rect):
        super().setGeometry(rect)
        self._do_layout(rect, False)

    def sizeHint(self):
        return self.minimumSize()

    def minimumSize(self):
        size = QSize()
        for item in self._items:
            size = size.expandedTo(item.minimumSize())
        margins = self.contentsMargins()
        size += QSize(margins.left() + margins.right(),
                      margins.top() + margins.bottom())
        return size

    def _do_layout(self, rect, test_only):
        """
        实际布局计算
        test_only=True 时只计算高度，不实际移动控件
        返回所需高度
        """
        margins = self.contentsMargins()
        effective_rect = rect.adjusted(
            margins.left(), margins.top(),
            -margins.right(), -margins.bottom()
        )

        x = effective_rect.x()
        y = effective_rect.y()
        line_height = 0

        for item in self._items:
            widget = item.widget()
            if not widget:
                continue

            space_x = self._spacing
            space_y = self._spacing

            item_w = item.sizeHint().width()
            # 如果子项高度随宽度变化，使用 heightForWidth 计算真实高度
            if item.hasHeightForWidth():
                item_h = item.heightForWidth(item_w)
            else:
                item_h = item.sizeHint().height()

            next_x = x + item_w + space_x
            if next_x - space_x > effective_rect.right() and line_height > 0:
                # 换行
                x = effective_rect.x()
                y = y + line_height + space_y
                next_x = x + item_w + space_x
                line_height = 0

            if not test_only:
                item.setGeometry(QRect(QPoint(x, y), QSize(item_w, item_h)))

            x = next_x
            line_height = max(line_height, item_h)

        total_height = y + line_height - rect.y() + margins.bottom()
        return total_height

    def setSpacing(self, spacing):
        self._spacing = spacing
        self.update()

    def spacing(self):
        return self._spacing
