import unittest

from server import (
    DOWNLOAD_DIR,
    USER_DOWNLOAD_DIR,
    extract_episode_id,
    filter_xiaoyuzhou_urls,
    parse_episode_ids,
    resolve_audio_file,
    move_qianwen_export,
)


class EpisodeParsingTests(unittest.TestCase):
    def test_extracts_id_from_url_with_query(self):
        value = (
            "https://www.xiaoyuzhoufm.com/episode/"
            "645c7f50306513184ca9efc9?s=example"
        )
        self.assertEqual(extract_episode_id(value), "645c7f50306513184ca9efc9")

    def test_accepts_multiple_separators_and_removes_duplicates(self):
        raw = (
            "https://www.xiaoyuzhoufm.com/episode/645c7f50306513184ca9efc9,"
            "https://www.xiaoyuzhoufm.com/episode/68371aa438dcc57c6473b586，"
            "645c7f50306513184ca9efc9"
        )
        self.assertEqual(
            parse_episode_ids(raw),
            ["645c7f50306513184ca9efc9", "68371aa438dcc57c6473b586"],
        )

    def test_rejects_non_episode_url(self):
        with self.assertRaises(ValueError):
            extract_episode_id("https://www.xiaoyuzhoufm.com/podcast/not-an-episode")

    def test_filters_chrome_tabs_to_episode_urls(self):
        tabs = [
            {
                "url": "https://www.xiaoyuzhoufm.com/episode/"
                "645c7f50306513184ca9efc9?s=example"
            },
            {"url": "https://www.xiaoyuzhoufm.com/podcast/123"},
            {"url": "https://example.com/episode/645c7f50306513184ca9efc9"},
        ]
        self.assertEqual(
            filter_xiaoyuzhou_urls(tabs),
            [
                "https://www.xiaoyuzhoufm.com/episode/"
                "645c7f50306513184ca9efc9?s=example"
            ],
        )

    def test_deduplicates_same_episode_with_different_query(self):
        tabs = [
            {
                "url": "https://www.xiaoyuzhoufm.com/episode/"
                "645c7f50306513184ca9efc9?s=one"
            },
            {
                "url": "https://www.xiaoyuzhoufm.com/episode/"
                "645c7f50306513184ca9efc9?s=two"
            },
        ]
        self.assertEqual(len(filter_xiaoyuzhou_urls(tabs)), 1)

    def test_audio_path_cannot_escape_download_directory(self):
        with self.assertRaises(ValueError):
            resolve_audio_file("../server.py")

    def test_audio_directory_is_in_current_project(self):
        self.assertEqual(DOWNLOAD_DIR.name, "download")

    def test_qianwen_export_rejects_path_outside_downloads(self):
        with self.assertRaises(ValueError):
            move_qianwen_export(str(DOWNLOAD_DIR / "file.txt"))

    def test_user_download_directory_is_named_downloads(self):
        self.assertEqual(USER_DOWNLOAD_DIR.name, "Downloads")


if __name__ == "__main__":
    unittest.main()
