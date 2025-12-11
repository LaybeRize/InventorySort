from __future__ import annotations


class SortInventory:
    def __init__(self, obj_name: str, obj_width: int, obj_pos: int, input_arr: ArrayWrapper):
        """
        The SortInventory class is an abstraction that bases its operation in taking in an array in the form of
        ArrayWrapper of arbitrary length. It then allows the call to sort_inventory() to get an array back
        which contains the given obj sorted with the least cost at the desired position.

        :param obj_name: The object name to insert into the input_arr
        :param obj_width: the width of the object
        :param obj_pos: the desired position of the object in the input_arr
        :param input_arr: the base array without the obj in it
        """
        self.obj_name = obj_name
        self.obj_width = obj_width
        if obj_pos < 0:
            obj_pos = input_arr.index(None)
        self.obj_pos = obj_pos
        self.input_arr = input_arr
        self.__MAX_COST = 2 ** 63
        self.COST_ABANDON = 2 * len(input_arr)

    def sort_inventory(self) -> ArrayWrapper:
        """
        Sorts the given obj into the array.

        :return: a newly generated version of the array with the obj inserted
        """
        arr, _ = self._sort_inventory(self.obj_pos, self.input_arr.copy())
        return arr

    def _sort_inventory(self, obj_pos: int, input_arr: ArrayWrapper, cost: int = 0) -> tuple[ArrayWrapper, int]:
        """
        The underlying recursive function to allow for cost-effective sorting. It actually implements the
        sorting algorithm.

        :param obj_pos: the current desired obj position
        :param input_arr: the input_arr to modify
        :param cost: the already incurred costs from former operations on the array
        :return: the newly modified input_arr and the newly calculated costs
        """
        # If the costs are bigger than twice the length of the array or the input_arr has the same configuration as
        # the base array, there is no sense in pursing this version of the input_arr further, return the object with
        # extreme cost, so it will not be chosen.
        if cost > self.COST_ABANDON or (cost > 0 and input_arr.equal(self.input_arr)):
            return input_arr, self.__MAX_COST

        all_free = False
        while not all_free:
            # If the obj_pos would move out of bounds the result is obviously invalid, so the algorithm should
            # abound this approach too.
            if obj_pos >= len(input_arr) or obj_pos < 0:
                return input_arr, self.__MAX_COST

            # Try to make free space under the object itself
            obj_pos, input_arr, cost = self._try_reordering(obj_pos, input_arr, cost)

            all_free = input_arr.all_free(self.obj_name, self.obj_width, obj_pos)

            # If after resorting the objects the desired space is not free, try to move the to be inserted item instead
            if not all_free:
                cost += 2
                free_left, free_right = input_arr.calc_free(self.obj_width, obj_pos)

                if free_left > 0 >= free_right:
                    obj_pos -= 1
                elif free_right > 0 >= free_left:
                    obj_pos += 1
                else:
                    # If the possibility exists that the item can move in both directions try which is cheaper
                    in_right, cost_right = self._sort_inventory(obj_pos + 1, input_arr.copy(), cost)
                    in_left, cost_left = self._sort_inventory(obj_pos - 1, input_arr.copy(), cost)
                    if cost_left > cost_right:
                        input_arr = in_right
                        cost = cost_right
                    else:
                        input_arr = in_left
                        cost = cost_left

            all_free = input_arr.all_free(self.obj_name, self.obj_width, obj_pos)

        # After successfully making space, the obj can be safely inserted
        input_arr.add_item(self.obj_name, self.obj_width, obj_pos)

        return input_arr, cost

    def _try_reordering(self, obj_pos: int, input_arr: ArrayWrapper, cost: int) \
            -> tuple[int, ArrayWrapper, int]:
        """
        Takes in the array and tries to move all underlying objects that would get in the way to one or the other side,
        if all underlying positions have either failed to be moved or freed the function returns its result.

        :param obj_pos: the current desired obj position
        :param input_arr: the input_arr to modify
        :param cost: the already incurred costs from former operations on the array
        :return: the newly modified input_arr and the newly calculated costs
        """
        free_left, free_right = input_arr.calc_free(self.obj_width, obj_pos)

        target = obj_pos
        while target < obj_pos + self.obj_width:
            if input_arr.is_free(target, self.obj_name):
                target += 1
                continue

            match input_arr.check_allowed_move_directions(obj_pos, self.obj_width, target):
                # Both
                case 0:
                    input_arr, cost, target = self._recursively_resolve_order(obj_pos, input_arr, cost, target)
                    free_left, free_right = input_arr.calc_free(self.obj_width, obj_pos)
                # Right
                case 1:
                    if free_right > 0:
                        cost += input_arr.move_right(target)
                        free_right -= 1
                    else:
                        target += 1
                # Left
                case -1:
                    if free_left > 0:
                        cost += input_arr.move_left(target)
                        free_left -= 1

                        if target != obj_pos:
                            target -= 1
                    else:
                        target += 1

        return obj_pos, input_arr, cost

    def _recursively_resolve_order(self, obj_pos: int, input_arr: ArrayWrapper, cost: int, target: int) \
            -> tuple[ArrayWrapper, int, int]:
        """
        The function tries to clean the targeted field specifically. The result of that attempt is returned.

        :param obj_pos: the current desired obj position
        :param input_arr: the input_arr to modify
        :param cost: the already incurred costs from former operations on the array
        :param target: the target space in the array to free from occupation
        :return: the newly modified input_arr and the newly calculated costs as well as the new target position from
                 which to continue
        """
        free_left, free_right = input_arr.calc_free(self.obj_width, obj_pos)

        if free_left > 0 >= free_right:
            cost += input_arr.move_left(target)
            if target != obj_pos:
                target -= 1
        elif free_right > 0 >= free_left:
            cost += input_arr.move_right(target)
        else:
            temp_arr_right, temp_cost = input_arr.move_right_copy(target)
            in_right, cost_right = self._sort_inventory(obj_pos, temp_arr_right, cost + temp_cost)
            temp_arr_left, temp_cost = input_arr.move_left_copy(target)
            in_left, cost_left = self._sort_inventory(obj_pos, temp_arr_left, cost + temp_cost)
            if cost_left > cost_right:
                return in_right, cost_right, target
            else:
                return in_left, cost_left, target

        return input_arr, cost, target


class ArrayWrapper:
    def __init__(self, arr: list[str | None]):
        """
        The ArrayWrapper is a wrapper around a list of strings or None values.

        :param arr: the underlying array to wrap
        """
        self.arr = arr

    def __len__(self) -> int:
        """
        Calls the len function on the underlying array.

        :return: the length of the array
        """
        return len(self.arr)

    def copy(self) -> ArrayWrapper:
        """
        Creates a copy of itself.

        :return: a copy of the underlying array wrapped in a new ArrayWrapper
        """
        return ArrayWrapper(self.arr.copy())

    def index(self, value) -> int:
        """
        Calls the index function on the underlying array.

        :param value: the value for which to get the index
        :return: the index of the value
        """
        return self.arr.index(value)

    def equal(self, other: ArrayWrapper) -> bool:
        """
        Compares its underlying array with another ArrayWrapper's underlying array.

        :param other: the other ArrayWrapper
        :return: If the arrays are the same
        """
        return self.arr == other.arr

    def is_free(self, target, name: str) -> bool:
        """
        Checks if the targeted space is None or the given name.

        :param target: the position to check
        :param name: the name that is also allowed as an option at the target position
        :return: If the space is occupied by the None value or the name
        """
        return self.arr[target] in [None, name]

    def add_item(self, name: str, obj_width: int, obj_pos: int) -> None:
        """
        Adds the name value on all the necessary spaces if it is not already present in the array.

        :param name: the value to add
        :param obj_width: the width of the object to add
        :param obj_pos: the starting position of the object to add
        """
        if name not in self.arr:
            for offset in range(obj_width):
                self.arr[obj_pos + offset] = name

    def free_spaces(self) -> int:
        """
        Calculates the amount of free spaces.

        :return: The amount of free spaces in the underlying array
        """
        return sum([1 if var is None else 0 for var in self.arr])

    def all_free(self, name: str, obj_width: int, obj_pos: int) -> bool:
        """
        Checks if the spaces below the object are all free (or already occupied by the object itself).

        :param name: the name of the object
        :param obj_width: the width of the object
        :param obj_pos: the starting position of the object
        :return: If the spaces that are to be taken by the object are free or occupied by the object
        """
        return sum([1 if var in [None, name] else 0 for var in self.arr[obj_pos:obj_pos + obj_width]]) == obj_width

    def calc_free(self, obj_width: int, obj_pos: int) -> tuple[int, int]:
        """
        Calculates the free spaces on both sides of the object.

        :param obj_width: the width of the object
        :param obj_pos: the starting position of the object
        :return: the amount of spaces that are free on the left side of the object and the amount of spaces
                 that are free on the right side of the object
        """
        return sum([1 if val is None else 0 for val in self.arr[:obj_pos]]), \
            sum([1 if val is None else 0 for val in self.arr[obj_pos + obj_width:]])

    def check_allowed_move_directions(self, obj_pos: int, obj_width: int, target: int) -> int:
        """
        Checks the targeted positions object and what directions it is allowed to move to.

        :param obj_pos: the starting position of the object
        :param obj_width: the width of the object
        :param target: the target space where the object that needs to move is positioned
        :return: 0 if the targeted object can move both directions, 1 if the target is only allowed to move right,
                 -1 if the target is only allowed to move left.
        """
        # If the item wants to occupy the most left spot the item there must move right
        if target == 0:
            return 1
        # If the item wants to occupy the most right spot the item there must move left
        if target == len(self.arr) - 1:
            return -1

        left_val = self.arr[obj_pos - 1] if obj_pos != 0 else None
        right_val = self.arr[obj_pos + obj_width] if obj_pos + obj_width != len(self.arr) else None

        # If the underlying item is wider then the overlay item it can move in both directions
        if self.arr[target] == left_val == right_val:
            return 0
        if self.arr[target] == left_val:
            return -1
        if self.arr[target] == right_val:
            return 1
        return 0

    def move_left(self, pos: int) -> int:
        """
        Finds the combined item pointed to, splits the part of and moves it over to the left.

        :param pos: the position from which the check for continuity should start
        :return: The incurred cost of the move
        """
        name = self.arr[pos]
        while self.arr[pos] == name:
            pos += 1
            if pos >= len(self.arr):
                pos = len(self.arr)
                break

        sub_part = list(reversed(self.arr[:pos]))
        sub_part.remove(None)
        sub_part = list(reversed(sub_part)) + [None]
        return self.calc_cost(sub_part + self.arr[pos:])

    def move_left_copy(self, pos: int) -> tuple[ArrayWrapper, int]:
        """
        Makes a copy of itself and calls move_left() on it with the given position.

        :param pos: the position that is passed to the move_left() function
        :return: the copy of itself after the move_left call and the costs the move have incurred
        """
        new_arr = self.copy()
        cost = new_arr.move_left(pos)
        return new_arr, cost

    def move_right(self, pos: int) -> int:
        """
        Finds the combined item pointed to, splits the part of and moves it over to the right.

        :param pos: the position from which the check for continuity should start
        :return: The incurred cost of the move
        """
        name = self.arr[pos]
        while self.arr[pos] == name:
            pos -= 1
            if pos < 0:
                pos = -1
                break

        sub_part = self.arr[pos + 1:]
        sub_part.remove(None)
        sub_part = [None] + sub_part
        return self.calc_cost(self.arr[:pos + 1] + sub_part)

    def move_right_copy(self, pos: int) -> tuple[ArrayWrapper, int]:
        """
        Makes a copy of itself and calls move_right() on it with the given position.

        :param pos: the position that is passed to the move_right() function
        :return: the copy of itself after the move_left call and the costs the move have incurred
        """
        new_arr = self.copy()
        cost = new_arr.move_right(pos)
        return new_arr, cost

    def calc_cost(self, new_array: list[str | None]) -> int:
        """
        Compares itself to the new array to calculate the costs then overwrites itself with the new array.

        :param new_array: the new array to check against and overwrite itself with
        :return: the move cost calculated
        """
        cost = 0
        for pos in range(len(new_array)):
            if new_array[pos] is not None and self.arr[pos] != new_array[pos]:
                cost += 1
        self.arr = new_array
        return cost

    def change_objects(self, new_array: ArrayWrapper) -> dict[str, int]:
        """
        Takes in the new ArrayWrapper, compares it to itself and notes all the items that have moved then overwrites
        its internal array with that of the passed ArrayWrapper.

        :param new_array: the new ArrayWrapper to which it compares itself
        :return: a dictionary of items that have moved and what starting position the item has now
        """
        result: dict[str | None, int] = {}
        for pos in range(len(self.arr)):
            if new_array.arr[pos] not in result and self.arr[pos] != new_array.arr[pos]:
                result[new_array.arr[pos]] = new_array.index(new_array.arr[pos])

        if None in result:
            result.pop(None)

        self.arr = new_array.arr
        return result

    def insert_and_return_changes(self, obj_name: str, obj_width: int, obj_pos: int) -> tuple[bool, dict[str, int]]:
        """
        Tries to insert the given object into itself. If it fails do nothing, otherwise insert the item.

        :param obj_name: the object's name
        :param obj_width: the width of the object
        :param obj_pos: the starting position of the object
        :return: If the insertion was successfully and if it was also a dictionary of changes generated by the
                 change_objects function.
        """
        if sum([1 if val is None else 0 for val in self.arr]) < obj_width:
            return False, {}
        return True, self.change_objects(SortInventory(obj_name, obj_width, obj_pos, self.copy()).sort_inventory())

    def remove_item(self, obj_name: str) -> int:
        """
        Removes the given object.

        :param obj_name: the object's name to removes
        :return: the amount of spaces the object occupied before removal
        """
        count = self.arr.count(obj_name)
        self.arr = [val if val != obj_name else None for val in self.arr]
        return count

    def fully_covered(self, name, obj_width: int, obj_pos: int) -> bool:
        """
        Checks if the given object covers the given name fully.

        :param name: the name for which to check for
        :param obj_width: the width of the object
        :param obj_pos: the starting position of the object
        :return: If the object covers the name fully
        """
        return self.arr.count(name) == self.arr[obj_pos:obj_pos + obj_width].count(name)

    def remove_items_under_new_item(self, obj_width: int, obj_pos: int) -> tuple[dict[str, int], int]:
        """
        First tries to remove all items fully covered and if that doesn't make enough space, removes all items that
        are blocking the object's position.

        :param obj_width: the width of the object
        :param obj_pos: the starting position of the object
        :return: The objects that were removed and their length, as well as their summed length
        """
        free_spaces = self.free_spaces()
        names = list(set(self.arr[obj_pos:obj_pos + obj_width]))
        if None in names:
            names.remove(None)

        sized_normed = sorted([(self.fully_covered(name, obj_width, obj_pos),
                                self.arr.count(name),
                                self.arr.index(name), name) for name in names], key=lambda x: (-x[0], x[1], x[2]))

        result: dict[str, int] = {}
        sum_width = 0
        covered = True
        for item_covered, size, start, name in sized_normed:
            if covered and free_spaces + sum_width >= obj_width:
                break
            result[name] = size
            sum_width += self.remove_item(name)
            covered = item_covered
        return result, sum_width
