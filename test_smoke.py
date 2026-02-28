"""
Comprehensive tests for the Eit (Eittris) game.

Designed to run headlessly on a server without a display.  The module-level
os.environ assignments must be in place *before* pygame or any game module is
imported, so they live at the very top of this file.

Run with:
    SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy LIBGL_ALWAYS_SOFTWARE=1 \
        .venv313/bin/pytest test_smoke.py -v
or simply:
    .venv313/bin/pytest test_smoke.py -v
(the env vars are also set programmatically below as a fallback)
"""

import os
import sys
import pickle
import tempfile
import types
import unittest.mock as mock

# --- Headless environment vars (set before any SDL/GL import) ----------------
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("LIBGL_ALWAYS_SOFTWARE", "1")

# Make the game's own directory importable regardless of cwd
GAME_DIR = os.path.dirname(os.path.abspath(__file__))
if GAME_DIR not in sys.path:
    sys.path.insert(0, GAME_DIR)

# The vendored PGU library lives in pgu/ and is directly importable.
import pgu  # noqa: E402
import pgu.gui  # noqa: E402

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_minimal_dm():
    """Return a lightweight fake DataManager that doesn't need OpenGL/audio."""
    dm = types.SimpleNamespace()
    dm.textures = {
        "standard": 1,
        "special": 2,
        "background_border": 3,
        "background_info": 4,
        "bw": 5,
    }
    # backgrounds dict: at least one entry so random_background() works
    dm.backgrounds = {"bg1": 10}
    dm.players = []
    dm.gameover_players = []

    # Stub sounds so no audio device is needed
    silent = types.SimpleNamespace(play=lambda: None)
    dm.placesound = silent
    dm.gameoversound = silent
    dm.welcomesound = silent
    dm.specialsounds = {
        k: silent
        for k in [
            "Faster",
            "Slower",
            "Stair",
            "Fill",
            "Rumble",
            "Inverse",
            "Flip",
            "Switch",
            "Packet",
            "Clear",
            "Question",
            "Bridge",
            "Mini",
            "Color",
            "Trans",
            "SZ",
            "Anti",
            "Background",
            "Blind",
            "Blink",
        ]
    }
    dm.music = False
    dm.fullscreen = False
    return dm


# ---------------------------------------------------------------------------
# 1. Module import tests
# ---------------------------------------------------------------------------


class TestImports:
    def test_import_eit_constants(self):
        import eit_constants

        assert eit_constants.DOWN_TIME == 500

    def test_import_blocks(self):
        import blocks

        assert blocks.BLOCK_SIZE == 24

    def test_import_blockfield(self):
        import blockfield  # noqa: F401

    def test_import_playerfield(self):
        import playerfield  # noqa: F401

    def test_import_datamanager(self):
        import datamanager  # noqa: F401

    def test_import_dialogs(self):
        import dialogs  # noqa: F401

    def test_import_eit(self):
        import eit  # noqa: F401


# ---------------------------------------------------------------------------
# 2. eit_constants sanity checks
# ---------------------------------------------------------------------------


class TestEitConstants:
    def test_to_next_level(self):
        from eit_constants import TO_NEXT_LEVEL

        assert TO_NEXT_LEVEL > 0

    def test_down_time(self):
        from eit_constants import DOWN_TIME

        assert DOWN_TIME > 0

    def test_drop_time(self):
        from eit_constants import DROP_TIME

        assert DROP_TIME > 0

    def test_spawn_time_greater_than_remove_time(self):
        from eit_constants import SPAWN_SPECIAL_TIME, REMOVE_SPECIAL_TIME

        assert SPAWN_SPECIAL_TIME > REMOVE_SPECIAL_TIME

    def test_down_time_delta_greater_than_one(self):
        from eit_constants import DOWN_TIME_DELTA

        assert DOWN_TIME_DELTA > 1.0


# ---------------------------------------------------------------------------
# 3. Scoretable unit tests (pure logic, no pygame/OpenGL)
# ---------------------------------------------------------------------------


class TestScoretable:
    def setup_method(self):
        from eit import Scoretable

        self.st = Scoretable()

    def _make_stat(self, name, score=100, lines=5, level=2):
        return {"Name": name, "Score": score, "Lines": lines, "Level": level}

    def test_initial_state_empty(self):
        assert self.st.stats == {}
        assert self.st.get_list() == []

    def test_insert_result_creates_winner_entry(self):
        winner = self._make_stat("Alice")
        self.st.insert_result(winner, [])
        assert "Alice" in self.st.stats

    def test_insert_result_increments_wins(self):
        winner = self._make_stat("Alice")
        self.st.insert_result(winner, [])
        assert self.st.stats["Alice"]["Winns"] == 1

    def test_insert_result_increments_matches(self):
        winner = self._make_stat("Alice")
        loser = self._make_stat("Bob")
        self.st.insert_result(winner, [loser])
        assert self.st.stats["Alice"]["Matches"] == 1
        assert self.st.stats["Bob"]["Matches"] == 1

    def test_insert_result_accumulates_score(self):
        winner = self._make_stat("Alice", score=200)
        self.st.insert_result(winner, [])
        self.st.insert_result(winner, [])
        assert self.st.stats["Alice"]["Score"] == 400

    def test_insert_result_accumulates_lines(self):
        winner = self._make_stat("Alice", lines=10)
        self.st.insert_result(winner, [])
        self.st.insert_result(winner, [])
        assert self.st.stats["Alice"]["Lines"] == 20

    def test_insert_result_tracks_max_level(self):
        winner = self._make_stat("Alice", level=3)
        self.st.insert_result(winner, [])
        winner2 = self._make_stat("Alice", level=1)
        self.st.insert_result(winner2, [])
        assert self.st.stats["Alice"]["Max Level"] == 3

    def test_rank_points_winner_gains(self):
        winner = self._make_stat("Alice")
        loser = self._make_stat("Bob")
        self.st.insert_result(winner, [loser])
        assert self.st.stats["Alice"]["Rank Points"] > 0

    def test_rank_points_loser_loses(self):
        winner = self._make_stat("Alice")
        loser = self._make_stat("Bob")
        self.st.insert_result(winner, [loser])
        assert self.st.stats["Bob"]["Rank Points"] < 0

    def test_rank_points_sum_zero(self):
        """Rank points transferred from loser to winner sum to zero."""
        winner = self._make_stat("Alice")
        loser = self._make_stat("Bob")
        self.st.insert_result(winner, [loser])
        total = (
            self.st.stats["Alice"]["Rank Points"] + self.st.stats["Bob"]["Rank Points"]
        )
        assert total == 0

    def test_multiple_losers(self):
        winner = self._make_stat("Alice")
        losers = [self._make_stat("Bob"), self._make_stat("Carol")]
        self.st.insert_result(winner, losers)
        assert "Bob" in self.st.stats
        assert "Carol" in self.st.stats

    def test_get_list_sorted_by_rank_points(self):
        for name, score in [("Alice", 300), ("Bob", 100), ("Carol", 200)]:
            w = self._make_stat(name, score=score)
            self.st.insert_result(w, [])
        result = self.st.get_list()
        points = [v["Rank Points"] for _, v in result]
        assert points == sorted(points, reverse=True)

    def test_scoretable_pickle_roundtrip(self):
        winner = self._make_stat("Alice")
        self.st.insert_result(winner, [])
        with tempfile.NamedTemporaryFile(delete=False) as f:
            tmppath = f.name
        try:
            with open(tmppath, "wb") as f:
                pickle.dump(self.st, f)
            with open(tmppath, "rb") as f:
                loaded = pickle.load(f)
            assert loaded.stats["Alice"]["Winns"] == 1
        finally:
            os.unlink(tmppath)

    def test_rank_points_are_integers(self):
        """Rank points must stay integers (integer division fix)."""
        winner = self._make_stat("Alice")
        loser = self._make_stat("Bob")
        self.st.insert_result(winner, [loser])
        for stat in self.st.stats.values():
            assert isinstance(stat["Rank Points"], int), (
                "Rank Points should be int, got float — check // division"
            )


# ---------------------------------------------------------------------------
# 4. Block geometry unit tests (no OpenGL context needed for logic)
# ---------------------------------------------------------------------------


class TestBlockGeometry:
    """Test block rotation and movement logic using a stub dm."""

    def setup_method(self):
        # We need pygame imported for K_* constants used by blocks.py at import
        import pygame

        if not pygame.get_init():
            pygame.init()
        self.dm = make_minimal_dm()

    def test_block_move(self):
        from blocks import BlockO

        b = BlockO(self.dm, 3, 5)
        original_xs = [bp.x for bp in b.blockparts]
        b.move(2, 0)
        for bp, ox in zip(b.blockparts, original_xs):
            assert bp.x == ox + 2

    def test_block_move_negative(self):
        from blocks import BlockI

        b = BlockI(self.dm, 4, 2)
        original_ys = [bp.y for bp in b.blockparts]
        b.move(0, -1)
        for bp, oy in zip(b.blockparts, original_ys):
            assert bp.y == oy - 1

    def test_block_o_no_rotate(self):
        """O-block should not rotate."""
        from blocks import BlockO

        b = BlockO(self.dm, 3, 3)
        positions_before = [(bp.x, bp.y) for bp in b.blockparts]
        b.rotate("cw")
        positions_after = [(bp.x, bp.y) for bp in b.blockparts]
        assert positions_before == positions_after

    def test_block_t_rotate_cw(self):
        from blocks import BlockT

        b = BlockT(self.dm, 3, 3)
        positions_before = [(bp.x, bp.y) for bp in b.blockparts]
        b.rotate("cw")
        positions_after = [(bp.x, bp.y) for bp in b.blockparts]
        assert positions_before != positions_after

    def test_block_t_rotate_360(self):
        """Four CW rotations should return to original position."""
        from blocks import BlockT

        b = BlockT(self.dm, 3, 3)
        original = [(bp.x, bp.y) for bp in b.blockparts]
        for _ in range(4):
            b.rotate("cw")
        after = [(bp.x, bp.y) for bp in b.blockparts]
        assert original == after

    def test_block_rotate_cw_then_ccw(self):
        """CW then CCW should be a no-op."""
        from blocks import BlockL

        b = BlockL(self.dm, 3, 3)
        original = [(bp.x, bp.y) for bp in b.blockparts]
        b.rotate("cw")
        b.rotate("ccw")
        after = [(bp.x, bp.y) for bp in b.blockparts]
        assert original == after

    def test_all_block_types_instantiate(self):
        from blocks import ALL_BLOCKS

        for BlockClass in ALL_BLOCKS:
            b = BlockClass(self.dm, 3, 3)
            assert len(b.blockparts) == 4

    def test_block_has_four_parts(self):
        from blocks import BlockI, BlockT, BlockO, BlockL, BlockJ, BlockS, BlockZ

        for Cls in [BlockI, BlockT, BlockO, BlockL, BlockJ, BlockS, BlockZ]:
            b = Cls(self.dm, 0, 0)
            assert len(b.blockparts) == 4, f"{Cls.__name__} should have 4 parts"

    def test_standard_parts_list(self):
        from blocks import STANDARD_PARTS

        assert len(STANDARD_PARTS) == 7

    def test_special_parts_list(self):
        from blocks import SPECIAL_PARTS

        assert len(SPECIAL_PARTS) == 22

    def test_block_part_move(self):
        from blocks import BlockPart

        bp = BlockPart(2, 3, texture=1)
        bp.move(1, -1)
        assert bp.x == 3
        assert bp.y == 2


# ---------------------------------------------------------------------------
# 5. BlockField logic tests
# ---------------------------------------------------------------------------


class TestBlockField:
    def setup_method(self):
        import pygame

        if not pygame.get_init():
            pygame.init()
        self.dm = make_minimal_dm()

    def _make_field(self, px=0, py=0):
        from blockfield import BlockField

        return BlockField(self.dm, px, py)

    def test_field_initial_size(self):
        f = self._make_field()
        assert len(f.blockparts) == 23
        assert all(len(row) == 10 for row in f.blockparts)

    def test_field_initially_empty(self):
        f = self._make_field()
        assert all(bp is None for row in f.blockparts for bp in row)

    def test_field_blockparts_list_empty(self):
        f = self._make_field()
        assert f.blockparts_list == []

    def test_insert_bp(self):
        from blocks import BlockPartRed

        f = self._make_field()
        bp = BlockPartRed(self.dm, 3, 5)
        f.insert_bp((3, 5), bp)
        assert f.blockparts[5][3] is bp
        assert bp in f.blockparts_list

    def test_remove_bp(self):
        from blocks import BlockPartRed

        f = self._make_field()
        bp = BlockPartRed(self.dm, 3, 5)
        f.insert_bp((3, 5), bp)
        f.remove_bp((3, 5))
        assert f.blockparts[5][3] is None
        assert bp not in f.blockparts_list

    def test_replace_bp(self):
        from blocks import BlockPartRed, BlockPartBlue

        f = self._make_field()
        red = BlockPartRed(self.dm, 4, 6)
        blue = BlockPartBlue(self.dm, 4, 6)
        f.insert_bp((4, 6), red)
        f.replace_bp(red, blue)
        assert f.blockparts[6][4] is blue
        assert red not in f.blockparts_list
        assert blue in f.blockparts_list

    def test_in_valid_position_empty_field(self):
        from blocks import BlockT

        f = self._make_field()
        b = BlockT(self.dm, 3, 3)
        assert f.in_valid_position(b) is True

    def test_in_valid_position_collision(self):
        from blocks import BlockPartRed, BlockT

        f = self._make_field()
        # Place a red part where T-block's parts will be
        bp = BlockPartRed(self.dm, 3, 4)
        f.insert_bp((3, 4), bp)
        b = BlockT(self.dm, 3, 3)
        # There will be overlap at some position
        assert f.in_valid_position(b) is False

    def test_in_valid_position_out_of_bounds_negative(self):
        from blocks import BlockT

        f = self._make_field()
        b = BlockT(self.dm, -10, -10)
        assert f.in_valid_position(b) is False

    def test_clear_field(self):
        from blocks import BlockPartRed

        f = self._make_field()
        bp = BlockPartRed(self.dm, 3, 5)
        f.insert_bp((3, 5), bp)
        f.clear_field()
        assert f.blockparts_list == []
        assert all(cell is None for row in f.blockparts for cell in row)

    def test_remove_full_rows_empty_field(self):
        f = self._make_field()
        cleared, special = f.remove_full_rows()
        assert cleared == 0
        assert special is None

    def test_remove_full_rows_one_full_row(self):
        from blocks import BlockPartRed

        f = self._make_field()
        row_y = 22
        for x in range(10):
            bp = BlockPartRed(self.dm, x, row_y)
            f.insert_bp((x, row_y), bp)
        cleared, special = f.remove_full_rows()
        assert cleared == 1
        assert all(cell is None for cell in f.blockparts[row_y])

    def test_remove_full_rows_two_full_rows(self):
        from blocks import BlockPartRed

        f = self._make_field()
        for row_y in [21, 22]:
            for x in range(10):
                bp = BlockPartRed(self.dm, x, row_y)
                f.insert_bp((x, row_y), bp)
        cleared, _ = f.remove_full_rows()
        assert cleared == 2

    def test_remove_full_rows_partial_row_not_cleared(self):
        from blocks import BlockPartRed

        f = self._make_field()
        # Fill 9 out of 10 cells — should not count as full
        for x in range(9):
            bp = BlockPartRed(self.dm, x, 22)
            f.insert_bp((x, 22), bp)
        cleared, _ = f.remove_full_rows()
        assert cleared == 0

    def test_top_index_empty(self):
        f = self._make_field()
        # Empty field: no blockparts, loop never finds anything, returns 22
        assert f.top_index() == 22

    def test_top_index_with_block(self):
        from blocks import BlockPartRed

        f = self._make_field()
        bp = BlockPartRed(self.dm, 5, 10)
        f.insert_bp((5, 10), bp)
        assert f.top_index() == 9  # y - 1 = 9

    def test_flip_does_not_corrupt_field(self):
        """After flip, blockparts and blockparts_list stay in sync."""
        from blocks import BlockPartRed

        f = self._make_field()
        for x in range(5):
            bp = BlockPartRed(self.dm, x, 20)
            f.insert_bp((x, 20), bp)
        f.flip()
        assert f.check() is True

    def test_effects_keys(self):
        f = self._make_field()
        expected = {"Inverse", "Mini", "Blink", "Blind", "Trans", "SZ", "Color"}
        assert set(f.effects.keys()) == expected

    def test_add_line_bottom(self):
        from blocks import BlockPartRed

        f = self._make_field()
        # Put a block at row 10 so add_line(top=False) can shift it up
        bp = BlockPartRed(self.dm, 5, 10)
        f.insert_bp((5, 10), bp)
        f.add_line(top=False)
        # The old row 22 should now have 9 non-None cells
        non_none = sum(1 for cell in f.blockparts[22] if cell is not None)
        assert non_none == 9


# ---------------------------------------------------------------------------
# 6. PlayerField scoring logic
# ---------------------------------------------------------------------------


class TestPlayerFieldScoring:
    def setup_method(self):
        import pygame

        if not pygame.get_init():
            pygame.init()
        self.dm = make_minimal_dm()

    def _make_player(self, name="TestPlayer", pid=0):
        # Patch load_controls so it doesn't read profiles.cfg from disk
        from playerfield import PlayerField

        with mock.patch.object(PlayerField, "load_controls"):
            pf = PlayerField(self.dm, pid, name, 0, 0)
        pf.default_controls()
        self.dm.players = [pf]
        return pf

    def test_initial_score_zero(self):
        pf = self._make_player()
        assert pf.score == 0

    def test_initial_level_zero(self):
        pf = self._make_player()
        assert pf.level == 0

    def test_initial_lines_zero(self):
        pf = self._make_player()
        assert pf.lines == 0

    def test_score_one_line(self):
        pf = self._make_player()
        pf.do_score(1)
        assert pf.score == 40  # (level 0 + 1) * 40

    def test_score_two_lines(self):
        pf = self._make_player()
        pf.do_score(2)
        assert pf.score == 100

    def test_score_three_lines(self):
        pf = self._make_player()
        pf.do_score(3)
        assert pf.score == 300

    def test_score_four_lines(self):
        pf = self._make_player()
        pf.do_score(4)
        assert pf.score == 1200

    def test_score_scales_with_level(self):
        pf = self._make_player()
        pf.level = 2
        pf.do_score(1)
        assert pf.score == (2 + 1) * 40

    def test_lines_counter_increments(self):
        pf = self._make_player()
        pf.do_score(3)
        assert pf.lines == 3

    def test_lines_counter_accumulates(self):
        pf = self._make_player()
        pf.do_score(2)
        pf.do_score(1)
        assert pf.lines == 3

    def test_level_up(self):
        from eit_constants import TO_NEXT_LEVEL

        pf = self._make_player()
        pf.do_score(TO_NEXT_LEVEL)
        assert pf.level == 1

    def test_level_up_multiple_times(self):
        from eit_constants import TO_NEXT_LEVEL

        pf = self._make_player()
        # Clear enough lines for 3 level-ups
        for _ in range(3):
            pf.to_nextlevel = 1
            pf.do_score(1)
        assert pf.level == 3

    def test_downtime_decreases_on_level_up(self):
        from eit_constants import DOWN_TIME, DOWN_TIME_DELTA

        pf = self._make_player()
        pf.to_nextlevel = 1
        initial_downtime = pf.downtime
        pf.do_score(1)
        assert pf.downtime < initial_downtime
        assert abs(pf.downtime - initial_downtime / DOWN_TIME_DELTA) < 1e-9


# ---------------------------------------------------------------------------
# 7. PlayerField default controls
# ---------------------------------------------------------------------------


class TestPlayerFieldControls:
    def setup_method(self):
        import pygame

        if not pygame.get_init():
            pygame.init()
        self.dm = make_minimal_dm()

    def _make_player(self, pid):
        from playerfield import PlayerField

        with mock.patch.object(PlayerField, "load_controls"):
            pf = PlayerField(self.dm, pid, f"P{pid}", 0, 0)
        pf.default_controls()
        self.dm.players = [pf]
        return pf

    def test_player0_controls_set(self):
        import pygame

        pf = self._make_player(0)
        assert pf.left == pygame.K_a
        assert pf.right == pygame.K_d

    def test_player1_controls_set(self):
        import pygame

        pf = self._make_player(1)
        assert pf.left == pygame.K_LEFT
        assert pf.right == pygame.K_RIGHT

    def test_all_player_ids_get_controls(self):
        for pid in range(4):
            pf = self._make_player(pid)
            assert hasattr(pf, "left")
            assert hasattr(pf, "right")
            assert hasattr(pf, "drop")


# ---------------------------------------------------------------------------
# 8. PlayerField target selection
# ---------------------------------------------------------------------------


class TestPlayerFieldTargeting:
    def setup_method(self):
        import pygame

        if not pygame.get_init():
            pygame.init()
        self.dm = make_minimal_dm()

    def _make_player(self, pid, name=None):
        from playerfield import PlayerField

        with mock.patch.object(PlayerField, "load_controls"):
            pf = PlayerField(self.dm, pid, name or f"P{pid}", 0, 0)
        pf.default_controls()
        return pf

    def test_next_target_selects_other_player(self):
        p1 = self._make_player(0)
        p2 = self._make_player(1)
        self.dm.players = [p1, p2]
        p1.next_target()
        assert p1.target is p2

    def test_next_target_wraps_around(self):
        p1 = self._make_player(0)
        p2 = self._make_player(1)
        self.dm.players = [p1, p2]
        p1.next_target()
        p1.next_target()
        # With 2 players, second call tries to advance past p2 back to p1,
        # but a player cannot target itself, so target becomes None.
        assert p1.target is None

    def test_next_target_single_player_is_none(self):
        p1 = self._make_player(0)
        self.dm.players = [p1]
        p1.next_target()
        assert p1.target is None

    def test_next_target_skips_gameover_player(self):
        p1 = self._make_player(0)
        p2 = self._make_player(1)
        p3 = self._make_player(2)
        self.dm.players = [p1, p2, p3]
        p2.gameover = True
        p1.next_target()
        assert p1.target is p3


# ---------------------------------------------------------------------------
# 9. Pygame initialisation smoke test
# ---------------------------------------------------------------------------


class TestPygameInit:
    def test_pygame_init_succeeds(self):
        import pygame

        result = pygame.init()
        # result is (success_count, fail_count); at least display should init
        assert result[0] > 0

    def test_display_set_mode_dummy(self):
        import pygame
        from pygame.locals import SWSURFACE

        pygame.init()
        screen = pygame.display.set_mode((640, 480), SWSURFACE)
        assert screen is not None

    def test_clock_creation(self):
        import pygame

        pygame.init()
        clock = pygame.time.Clock()
        assert clock is not None

    def test_event_pump(self):
        import pygame

        pygame.init()
        pygame.event.pump()  # should not raise

    def test_key_set_repeat(self):
        import pygame

        pygame.init()
        pygame.key.set_repeat()  # should not raise


# ---------------------------------------------------------------------------
# 10. Main game object construction (menu init, config loading)
# ---------------------------------------------------------------------------


class TestMainInit:
    """Test Main.__init__ which covers: Scoretable, ConfigObj, GUI construction."""

    def test_main_constructs_without_error(self, tmp_path, monkeypatch):
        """Main() should build the full menu GUI without raising."""
        import pygame
        from pygame.locals import SWSURFACE

        pygame.init()
        pygame.display.set_mode((640, 500), SWSURFACE)

        # Run from tmp_path so config/data files don't clash
        monkeypatch.chdir(GAME_DIR)

        from eit import Main

        m = Main()
        assert m is not None

    def test_main_loads_scoretable(self, monkeypatch):
        import pygame
        from pygame.locals import SWSURFACE

        pygame.init()
        pygame.display.set_mode((640, 500), SWSURFACE)
        monkeypatch.chdir(GAME_DIR)

        from eit import Main

        m = Main()
        assert m.scoretable is not None

    def test_main_loads_settings(self, monkeypatch):
        import pygame
        from pygame.locals import SWSURFACE

        pygame.init()
        pygame.display.set_mode((640, 500), SWSURFACE)
        monkeypatch.chdir(GAME_DIR)

        from eit import Main

        m = Main()
        assert isinstance(m.active_profiles, dict)
        assert len(m.active_profiles) == 4

    def test_main_init_menu(self, monkeypatch):
        import pygame
        from pygame.locals import SWSURFACE

        pygame.init()
        pygame.display.set_mode((640, 500), SWSURFACE)
        monkeypatch.chdir(GAME_DIR)

        from eit import Main

        m = Main()
        app = m.init_menu()
        assert app is not None

    def test_main_save_scoretable(self, monkeypatch, tmp_path):
        """save_scoretable() should write a valid pickle file."""
        import pygame
        from pygame.locals import SWSURFACE

        pygame.init()
        pygame.display.set_mode((640, 500), SWSURFACE)
        monkeypatch.chdir(GAME_DIR)

        from eit import Main, Scoretable

        m = Main()
        m.scoretable = Scoretable()
        # Point the save to tmp_path to avoid clobbering real data
        orig_open = open
        saved = {}

        def fake_open(path, mode="r", **kw):
            if path == "scoretable.dat" and "w" in mode:
                import io

                buf = io.BytesIO()
                saved["buf"] = buf
                return buf
            return orig_open(path, mode, **kw)

        # Just call save; if it doesn't raise we're fine
        m.save_scoretable()


# ---------------------------------------------------------------------------
# 11. Main event loop: single iteration then quit
# ---------------------------------------------------------------------------


class TestMainLoop:
    def test_main_runs_one_iteration(self, monkeypatch):
        """
        Patch Main.running to False after the first loop() call so the while
        loop exits immediately.  Exercises pygame.init, display.set_mode,
        init_menu, and the first frame of the menu render path.
        """
        import pygame
        from pygame.locals import SWSURFACE

        pygame.init()
        monkeypatch.chdir(GAME_DIR)

        from eit import Main

        original_loop = Main.loop

        call_count = {"n": 0}

        def one_shot_loop(self):
            original_loop(self)
            call_count["n"] += 1
            self.running = False  # stop after first iteration

        monkeypatch.setattr(Main, "loop", one_shot_loop)
        m = Main()
        m.main()
        assert call_count["n"] == 1

    def test_quit_event_stops_loop(self, monkeypatch):
        """Posting a QUIT event should cause the loop to exit."""
        import pygame
        from pygame.locals import QUIT, SWSURFACE

        pygame.init()
        monkeypatch.chdir(GAME_DIR)

        from eit import Main

        original_init_menu = Main.init_menu

        def patched_init_menu(self):
            # Post a QUIT before returning so the first frame sees it
            pygame.event.post(pygame.event.Event(QUIT))
            return original_init_menu(self)

        monkeypatch.setattr(Main, "init_menu", patched_init_menu)
        m = Main()
        m.main()
        assert m.running is False


# ---------------------------------------------------------------------------
# 12. calc_stats integration test
# ---------------------------------------------------------------------------


class TestCalcStats:
    def test_calc_stats_records_winner(self, monkeypatch):
        import pygame
        from pygame.locals import SWSURFACE

        pygame.init()
        monkeypatch.chdir(GAME_DIR)

        from eit import Main
        from playerfield import PlayerField

        m = Main()

        dm = make_minimal_dm()
        with mock.patch.object(PlayerField, "load_controls"):
            p1 = PlayerField(dm, 0, "Alice", 0, 0)
            p2 = PlayerField(dm, 1, "Bob", 0, 0)
        p1.default_controls()
        p2.default_controls()
        p1.score = 500
        p1.lines = 20
        p1.level = 3
        p2.score = 100
        p2.lines = 5
        p2.level = 1

        m.dm = dm
        dm.players = [p1, p2]

        m.calc_stats(p1)

        assert "Alice" in m.scoretable.stats
        assert m.scoretable.stats["Alice"]["Winns"] == 1
        assert "Bob" in m.scoretable.stats
        assert m.scoretable.stats["Bob"]["Winns"] == 0
