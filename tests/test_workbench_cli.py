import http.server
import socketserver
from pathlib import Path
from unittest.mock import MagicMock, patch

from novel2script.cli import main


def test_serve_workbench_cli_success():
    # 模拟 socketserver.TCPServer 及其上下文管理器，以及 webbrowser.open
    with patch("socketserver.TCPServer") as mock_tcpserver, \
         patch("webbrowser.open") as mock_webbrowser:
        
        # 实例化模拟
        mock_server_instance = MagicMock()
        mock_tcpserver.return_value.__enter__.return_value = mock_server_instance
        
        # 运行 CLI 命令
        exit_code = main(["serve-workbench", "--port", "8888", "--host", "127.0.0.1"])
        
        assert exit_code == 0
        
        # 校验 TCPServer 被正确配置并调用
        mock_tcpserver.assert_called_once()
        args, kwargs = mock_tcpserver.call_args
        assert args[0] == ("127.0.0.1", 8888)
        
        # 校验 serve_forever 是否被调用
        mock_server_instance.serve_forever.assert_called_once()


def test_serve_workbench_cli_missing_workbench(tmp_path):
    # 模拟当前工作目录没有 workbench 的情况
    # 且模拟 Path.cwd() 返回一个没有 workbench/index.html 的路径
    fake_cwd = tmp_path / "fake_project"
    fake_cwd.mkdir()

    with patch("pathlib.Path.cwd", return_value=fake_cwd), \
         patch("socketserver.TCPServer") as mock_tcpserver:
        
        # 运行命令，它应该找不到任何 workbench 文件夹（因为它是临时的 fake_cwd 且 sys.argv __file__ 指向的上一级也没有）
        # 这里为了彻底排除 __file__ 关联的 path，我们要测试其错误返回码
        # 同时为了防止真的找到，我们在 cli.py 中有三层 fallback，
        # 在这种临时目录下三层 fallback 应该都会失败，输出错误并返回 1
        exit_code = main(["serve-workbench", "--no-browser"])
        
        assert exit_code == 1
        assert not mock_tcpserver.called
