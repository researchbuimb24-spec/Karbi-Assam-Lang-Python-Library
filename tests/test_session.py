import unittest
import sqlite3
from pathlib import Path

import karbi
from karbi.core.session import KarbiSession, session
from karbi.dictionary import DictionaryEntry
from karbi.translator import TranslationMatch
from karbi.api import SearchResult


class TestKarbiSession(unittest.TestCase):
    """Test suite for KarbiSession and karbi.session() connection-reuse API."""

    def test_session_normal_lifecycle(self):
        """Session opens cleanly and closes when exiting normal context."""
        with karbi.session() as s:
            self.assertTrue(s.is_active)
            self.assertFalse(s.is_closed)
            self.assertIsInstance(s.connection(), sqlite3.Connection)

            entry = s.lookup("arlèng")
            self.assertIsNotNone(entry)
            self.assertEqual(entry.lemma, "arlèng")

        self.assertTrue(s.is_closed)
        self.assertFalse(s.is_active)
        # Attempting operation after exit raises RuntimeError
        with self.assertRaises(RuntimeError):
            s.lookup("arlèng")

    def test_session_exception_lifecycle(self):
        """Session closes reliably even when an unhandled exception is raised."""
        sess_ref = None
        with self.assertRaises(ValueError):
            with karbi.session() as s:
                sess_ref = s
                self.assertTrue(s.is_active)
                raise ValueError("Intentional error inside session context")

        self.assertIsNotNone(sess_ref)
        self.assertTrue(sess_ref.is_closed)
        self.assertFalse(sess_ref.is_active)

    def test_session_nested_contexts(self):
        """Nested context managers with the same session reuse connection until outermost exit."""
        with karbi.session() as s:
            conn1 = s.connection()
            with s:
                conn2 = s.connection()
                self.assertIs(conn1, conn2)
                res = s.lookup("làng")
                self.assertIsNotNone(res)
            # Inner exit must not close connection
            self.assertTrue(s.is_active)
            self.assertFalse(s.is_closed)
            res2 = s.lookup("hèm")
            self.assertIsNotNone(res2)

        # Outermost exit closes connection
        self.assertTrue(s.is_closed)

    def test_session_all_operations(self):
        """Session supports lookup, lookup_all, translate, and search."""
        with karbi.session() as s:
            # 1. lookup
            e = s.lookup("cho")
            self.assertIsNotNone(e)

            # 2. lookup_all
            homonyms = s.lookup_all("cho")
            self.assertGreaterEqual(len(homonyms), 1)

            # 3. translate
            matches = s.translate("water", from_lang="en")
            self.assertGreaterEqual(len(matches), 1)
            self.assertEqual(matches[0].karbi_lemma, "làng")

            # 4. search
            results = s.search("house")
            self.assertGreaterEqual(len(results), 1)

    def test_session_refresh(self):
        """Calling refresh closes previous connection and re-establishes a fresh one."""
        with karbi.session() as s:
            old_conn = s.connection()
            s.refresh()
            new_conn = s.connection()
            self.assertIsNot(old_conn, new_conn)
            entry = s.lookup("arlèng")
            self.assertIsNotNone(entry)

    def test_batch_lookup_reusable_connection(self):
        """karbi.batch_lookup and karbi.batch_translate reuse connections cleanly."""
        words = ["arlèng", "làng", "hèm", "cho", "nonexistent_word_xyz"]
        res_map = karbi.batch_lookup(words)
        self.assertEqual(len(res_map), 5)
        self.assertIsNotNone(res_map["arlèng"])
        self.assertIsNone(res_map["nonexistent_word_xyz"])

        trans_map = karbi.batch_translate(["water", "house"])
        self.assertIn("water", trans_map)
        self.assertIn("house", trans_map)
        self.assertGreaterEqual(len(trans_map["water"]), 1)


if __name__ == "__main__":
    unittest.main()
