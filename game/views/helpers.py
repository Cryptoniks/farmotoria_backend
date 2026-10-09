# Helper functions for views


def is_cell_locked(locks, r, c):
    """Check if cell is locked by any area lock."""
    for lock in locks:
        if (
            lock.row_start <= r < lock.row_start + lock.rows and
            lock.col_start <= c < lock.col_start + lock.cols
        ):
            return lock
    return None


def iter_rect(row, col, h, w):
    """Iterate over all cells in a rectangle."""
    for r in range(row, row + h):
        for c in range(col, col + w):
            yield r, c
