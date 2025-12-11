from sort import ArrayWrapper
import tkinter as tk


class DragAndDrop:
    def __init__(self, grid: int, width: int, height: int, left_corner: tuple[int, int]):
        """
        The DragAndDrop class creates an interactive Inventory of Items. These items can be dynamically added and
        can be rearranged by the user via Drag and Drop on the Screen.

        :param grid: The grids unit in pixel
        :param width: a multiple of grid in pixel (the multiple is the amount of columns in the inventory)
        :param height: a multiple of grid in pixel (the multiple is the amount of rows in the inventory)
        :param left_corner: the left corner given as (x, y) coordinates in pixel
        """
        self.occupied_positions: dict[str, list[int]] = {}
        self.widgets: dict[str, tk.Widget] = {}
        self.grid: int = grid
        self.min_x, self.min_y = left_corner
        self.max_x = self.min_x + width
        self.max_y = self.min_y + height
        self.columns = width // grid
        self.rows = height // grid
        self.grid_occupancy: list[ArrayWrapper] = [ArrayWrapper([None for _ in range(self.columns)])
                                                   for _ in range(self.rows)]

    def add_occupation(self, item: tk.Widget, grid_x: int, grid_y: int, width: int, name: str) -> bool:
        """
        The function allows the placement of a new tk.Widget into the Inventory.

        :param item: The tk.Widget that should be placed in the inventory
        :param grid_x: the desired x position in the inventory grid (-1 implies first free space)
        :param grid_y: the desired y position in the inventory grid (-1 implies frist row that has enough space)
        :param width: the amount of columns taken by the item
        :param name: the text string that is internally associated with the tk.Widget
        :return: If the item could be placed in the inventory
        """
        item.internal_name = name
        x = self.min_x + (self.grid * grid_x)
        y = self.min_y + (self.grid * grid_y)

        changes: dict[str, int] = {}
        if grid_y < 0:
            grid_x = -1
            success = False
            for temp_y in range(len(self.grid_occupancy)):
                success, changes = self.grid_occupancy[temp_y].insert_and_return_changes(name, width, grid_x)
                if success:
                    y = self.min_y + (self.grid * temp_y)
                    break
            if not success:
                return False
        else:
            success, changes = self.grid_occupancy[grid_y].insert_and_return_changes(name, width, grid_x)
            if not success:
                return False

        self.occupied_positions[name] = [x, y, self.grid * width]
        self.widgets[name] = item
        item.bind("<ButtonPress-1>", DND.on_drag_start)
        item.bind("<B1-Motion>", DND.on_drag_motion)
        item.bind("<ButtonRelease-1>", DND.on_drag_stop)

        for changed_item_name, position in changes.items():
            _, y, width = self.occupied_positions[changed_item_name]
            x = (position * self.grid) + self.min_x
            self.widgets[changed_item_name].place(x=x, y=y, width=width, height=self.grid)
            self.occupied_positions[changed_item_name] = [x, y, width]

        return True

    @staticmethod
    def on_drag_start(event) -> None:
        """
        Stores the widgets initial relative position of the cursor when dragging starts as well as raises the object
        to the front.
        """
        event.widget.startX = event.x
        event.widget.startY = event.y
        event.widget.tkraise()

    @staticmethod
    def on_drag_motion(event) -> None:
        """
        Moves the widget to the new position while dragging.
        """
        x = event.widget.winfo_x() + (event.x - event.widget.startX)
        y = event.widget.winfo_y() + (event.y - event.widget.startY)
        event.widget.place(x=x, y=y)

    def on_drag_stop(self, event) -> None:
        """
        Positions the item to the new grid. The placement tries to insert the object at the desired position, and uses
        the insertion algorithm for that, if that fails the object is returned to the original position.
        If the item is dragged out of bounds it is always returned to its original position.
        """
        name = event.widget.internal_name
        old_x, old_y, width = self.occupied_positions[name]
        x = self.calc_bound_x(event.widget.winfo_x(), width)
        y = self.calc_bound_y(event.widget.winfo_y())

        if x == -1 or y == -1 or (not self.reorder_other_widgets_around(name, x, y, width)):
            event.widget.place(x=old_x, y=old_y)

    def reorder_other_widgets_around(self, name: str, x: int, y: int, width: int) -> bool:
        """
        Tries to reorder the item in the inventory, by trying multiple things in order.

        :param name: the name of the item to move
        :param x: the desired x position in pixels
        :param y: the desired y position in pixels
        :param width: the items width in pixels
        :return: If the item could be successfully placed
        """
        width //= self.grid
        pos_x = ((x - self.min_x) // self.grid)
        pos_y = ((y - self.min_y) // self.grid)

        result_occupation: list[ArrayWrapper] = [self.grid_occupancy[i].copy() for i in range(self.rows)]
        [obj.remove_item(name) for obj in result_occupation]
        # First tries to insert without removing any items from the targeted row
        success, changes = result_occupation[pos_y].insert_and_return_changes(name, width, pos_x)
        if success:
            self.occupied_positions[name][1] = y
            self.update_item_position(changes)
            self.grid_occupancy = result_occupation
            return True

        # If that fails tries to see if removing underlying items would be possible
        items, total_width = result_occupation[pos_y].remove_items_under_new_item(width, pos_x)
        if total_width > result_occupation[pos_y ^ 1].free_spaces():
            return False

        # If so, removes them and puts them in the other row before inserting the item in the desired row
        freed_items_y = ((pos_y ^ 1) * self.grid) + self.min_y
        for changed_item_name in items.keys():
            self.occupied_positions[changed_item_name][1] = freed_items_y
        self.occupied_positions[name][1] = y

        for removed_item_name, changed_item_width in items.items():
            _, changes = result_occupation[pos_y ^ 1].insert_and_return_changes(removed_item_name,
                                                                                changed_item_width, -1)
            self.update_item_position(changes)

        _, changes = result_occupation[pos_y].insert_and_return_changes(name, width, pos_x)
        self.update_item_position(changes)

        self.grid_occupancy = result_occupation
        return True

    def update_item_position(self, changes: dict[str, int]) -> None:
        """
        Updates the given items with their new positions.

        :param changes: the items that have changed position
        """
        for changed_item_name, position in changes.items():
            _, pos_y, width = self.occupied_positions[changed_item_name]
            pos_x = (position * self.grid) + self.min_x
            self.widgets[changed_item_name].place(x=pos_x, y=pos_y)
            self.occupied_positions[changed_item_name] = [pos_x, pos_y, width]

    def calc_bound_x(self, pos: int, width: int) -> int:
        """
        Takes in the imprecise target x position of the Drag and Drop operation and tries to find the correct precise
        place to put the item.

        :param pos: the imprecise x position of the item in pixel
        :param width: the width of the item in pixel
        :return: Returns the precise x position, or if the item was out of bounds -1
        """
        temp_val = ((pos + int(self.grid / 2)) // self.grid) * self.grid
        if temp_val < self.min_x:
            return -1
        if temp_val + width > self.max_x:
            return -1
        return temp_val

    def calc_bound_y(self, pos: int) -> int:
        """
        Takes in the imprecise target y position of the Drag and Drop operation and tries to find the correct precise
        place to put the item.

        :param pos: the imprecise y position of the item in pixel
        :return: Returns the precise y position, or if the item was out of bounds -1
        """
        temp_val = ((pos + int(self.grid / 2)) // self.grid) * self.grid
        if temp_val < self.min_y:
            return -1
        if temp_val + self.grid > self.max_y:
            return -1
        return temp_val


WIDTH = 1000
HEIGHT = 200
LEFT = 100
TOP = 100
DND = DragAndDrop(100, WIDTH, HEIGHT, (LEFT, TOP))


def create_label(root: tk.Tk, width: int, counter: int) -> int:
    """
    A small abstracted function to make inserting a few items into the inventory easy and quick.

    :param root: tk.Tk object to which the label should be tied
    :param width: the width of the object in grid units (not pixel)
    :param counter: a unique number to properly identify the label
    :return: returns the counter incremented by 1
    """
    colors = ["antiquewhite", "aqua", "aquamarine1", "beige", "bisque1", "burlywood1", "cadetblue1",
              "chartreuse", "crimson", "chocolate1", "darksalmon", "deepskyblue"]
    color = colors[counter % len(colors)]
    label = tk.Label(root, text=f"Drag Me!\nItem {counter}", bg=color, font=("Arial", 10))
    DND.add_occupation(label, -1, -1, width, f"ITEM-{counter}-{width}")
    return counter + 1


def main():
    # Create main window
    root = tk.Tk()
    root.geometry("1200x600")
    root.title("Drag and Drop Example")

    # Create draggable label
    label_bg = tk.Label(root, text="", bg="white", font=("Arial", 10))
    label_bg.place(x=LEFT, y=TOP, width=WIDTH, height=HEIGHT)

    counter = 1
    counter = create_label(root, 2, counter)
    counter = create_label(root, 3, counter)
    counter = create_label(root, 3, counter)
    counter = create_label(root, 4, counter)
    counter = create_label(root, 2, counter)
    counter = create_label(root, 1, counter)
    counter = create_label(root, 1, counter)
    counter = create_label(root, 2, counter)
    create_label(root, 1, counter)

    root.mainloop()


if __name__ == '__main__':
    main()
