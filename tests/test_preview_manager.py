import unittest
import urllib.request
from unittest.mock import patch, MagicMock
from pathlib import Path
import shutil
from service import PreviewServerManager

class TestPreviewServerManager(unittest.TestCase):
    def setUp(self):
        self.test_dir = Path("output/test_preview_workspace")
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)
        self.test_dir.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)

    def test_ensure_dependencies_already_installed(self):
        nm = self.test_dir / "node_modules"
        nm.mkdir(parents=True, exist_ok=True)
        (nm / ".dummy").touch()
        pm = PreviewServerManager(self.test_dir, port=5173)
        self.assertTrue(pm.ensure_dependencies())

    @patch("subprocess.run")
    def test_ensure_dependencies_calls_npm_install(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0)
        pm = PreviewServerManager(self.test_dir, port=5173)
        res = pm.ensure_dependencies()
        self.assertTrue(res)
        mock_run.assert_called_once()

    @patch("urllib.request.urlopen")
    def test_is_server_ready_success(self, mock_urlopen):
        mock_resp = MagicMock(status=200)
        mock_urlopen.return_value.__enter__.return_value = mock_resp
        pm = PreviewServerManager(self.test_dir, port=5173)
        self.assertTrue(pm.is_server_ready("http://localhost:5173"))

    @patch.object(urllib.request.OpenerDirector, "open")
    def test_is_server_ready_passes_timeout_as_keyword_not_post_data(self, mock_open):
        mock_resp = MagicMock(status=200)
        mock_resp.__enter__.return_value = mock_resp
        mock_open.return_value = mock_resp
        pm = PreviewServerManager(self.test_dir, port=5173)
        self.assertTrue(pm.is_server_ready("http://localhost:5173", timeout_seconds=0.5))
        called_req, called_data, called_timeout = mock_open.call_args.args
        self.assertIsNone(called_req.data)
        self.assertIsNone(called_data)
        self.assertEqual(called_timeout, 0.5)

    @patch("urllib.request.urlopen", side_effect=Exception("Connection refused"))
    def test_is_server_ready_failure(self, mock_urlopen):
        pm = PreviewServerManager(self.test_dir, port=5173)
        self.assertFalse(pm.is_server_ready("http://localhost:5173"))

    @patch.object(PreviewServerManager, "is_server_ready", return_value=True)
    def test_start_server_already_running(self, mock_ready):
        pm = PreviewServerManager(self.test_dir, port=5173)
        url = pm.start_server()
        self.assertEqual(url, "http://localhost:5173")
        self.assertIsNone(pm.process)

    @patch("subprocess.Popen")
    @patch.object(PreviewServerManager, "ensure_dependencies", return_value=True)
    @patch.object(PreviewServerManager, "is_server_ready", side_effect=[False, True])
    def test_start_server_spawns_process(self, mock_ready, mock_deps, mock_popen):
        mock_proc = MagicMock()
        mock_popen.return_value = mock_proc
        pm = PreviewServerManager(self.test_dir, port=5173)
        url = pm.start_server()
        self.assertEqual(url, "http://localhost:5173")
        mock_popen.assert_called_once()
        self.assertEqual(pm.process, mock_proc)

    def test_stop_server(self):
        pm = PreviewServerManager(self.test_dir, port=5173)
        mock_proc = MagicMock()
        pm.process = mock_proc
        pm.stop_server()
        mock_proc.terminate.assert_called_once()
        self.assertIsNone(pm.process)

if __name__ == "__main__":
    unittest.main()
